from decimal import Decimal
from django.db import transaction
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, OrderItem, Product, SelectedProduct
from .permissions import IsAdminOrReadOnly
from .serializers import (
    CheckoutSerializer,
    OrderSerializer,
    ProductSerializer,
    RegisterSerializer,
    SelectedProductSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]


class SelectedProductViewSet(viewsets.ModelViewSet):
    serializer_class = SelectedProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SelectedProduct.objects.filter(user=self.request.user).select_related("product")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data["product"]
        quantity = serializer.validated_data.get("quantity", 1)

        if product.stock < quantity:
            return Response(
                {"detail": f"Only {product.stock} units are available in stock."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item, created = SelectedProduct.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            new_qty = item.quantity + quantity
            if product.stock < new_qty:
                return Response(
                    {"detail": f"Total quantity ({new_qty}) exceeds available stock ({product.stock})."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            item.quantity = new_qty
            item.save()

        output_serializer = self.get_serializer(item)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class TestCheckoutView(APIView):
    # უფასო სატესტო გადახდა: ითვლის მომხმარებლის მიერ შერჩეული პროდუქტების ჯამურ ფასს,
    # ამოწმებს მარაგს, ქმნის გადახდილ შეკვეთას (Order) და ასუფთავებს არჩეულ სიას.
    permission_classes = [IsAuthenticated]
    serializer_class = CheckoutSerializer

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        selected_items = list(
            SelectedProduct.objects.select_for_update()
            .select_related("product")
            .filter(user=request.user)
        )

        if not selected_items:
            return Response(
                {"detail": "Please select at least one product before proceeding to checkout."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total = Decimal("0.00")
        for item in selected_items:
            if item.product.stock < item.quantity:
                return Response(
                    {"detail": f"Insufficient stock for product '{item.product.name}'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            total += item.product.price * item.quantity

        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            payment_method=f"FREE_TEST ({serializer.validated_data['test_card_or_method']})",
            status=Order.Status.PAID,
        )

        for item in selected_items:
            OrderItem.objects.create(
                order=order,
                product_name=item.product.name,
                unit_price=item.product.price,
                quantity=item.quantity,
            )
            item.product.stock -= item.quantity
            item.product.save()

        SelectedProduct.objects.filter(user=request.user).delete()

        return Response(
            {
                "message": "Test payment completed successfully (no real charge was made).",
                "order": OrderSerializer(order).data,
            },
            status=status.HTTP_201_CREATED,
        )


class OrderListView(generics.ListAPIView):
    # მომხმარებლის მიერ შესრულებული შეკვეთების ისტორია
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")