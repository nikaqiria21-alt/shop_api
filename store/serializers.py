from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Order, OrderItem, Product, SelectedProduct


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "stock", "created_at"]
        read_only_fields = ["id", "created_at"]


class SelectedProductSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source="product", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = SelectedProduct
        fields = ["id", "product", "product_detail", "quantity", "subtotal", "selected_at"]
        read_only_fields = ["id", "product_detail", "subtotal", "selected_at"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("რაოდენობა უნდა იყოს მინიმუმ 1.")
        return value


class CheckoutSerializer(serializers.Serializer):
#უფასო სატესტო გადახდის პარამეტრები
    test_card_or_method = serializers.CharField(
        default="FREE_TEST_CARD_4242",
        help_text="Test method or test card (no real charge is made)."
    )


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product_name", "unit_price", "quantity"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "total_amount", "payment_method", "status", "created_at", "items"]
        read_only_fields = fields