from decimal import Decimal
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Order, Product, SelectedProduct


class StoreAPITests(APITestCase):
    def setUp(self):
        # ადმინისტრატორი (staff)
        self.admin = User.objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="AdminPassword123!",
        )

        # ჩვეულებრივი მომხმარებელი
        self.buyer = User.objects.create_user(
            username="buyer_user",
            email="buyer@example.com",
            password="BuyerPassword123!",
        )

        # საწყისი პროდუქტი
        self.product = Product.objects.create(
            name="Gaming Mouse",
            description="Wireless ergonomic mouse",
            price=Decimal("120.00"),
            stock=10,
        )

        # URL-ები
        self.register_url = reverse("register")
        self.login_url = reverse("token_obtain_pair")
        self.products_list_url = reverse("product-list")
        self.selected_list_url = reverse("selected-product-list")
        self.checkout_url = reverse("test-checkout")
        self.orders_url = reverse("order-list")

    def get_jwt_access_token(self, username: str, password: str) -> str:
        response = self.client.post(
            self.login_url,
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        return response.data["access"]

    def authenticate_as(self, username: str, password: str):
        token = self.get_jwt_access_token(username, password)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_register_and_jwt_login(self):
        payload = {
            "username": "new_registered_user",
            "email": "new@example.com",
            "password": "NewUserPass123!",
        }
        reg_res = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(reg_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(reg_res.data["username"], "new_registered_user")

        token = self.get_jwt_access_token("new_registered_user", "NewUserPass123!")
        self.assertTrue(len(token) > 20)

    def test_only_admin_can_create_update_delete_products(self):
        # ჩვეულებრივ მომხმარებელს არ შეუძლია პროდუქტის შექმნა (403 Forbidden)
        self.authenticate_as("buyer_user", "BuyerPassword123!")
        create_res = self.client.post(
            self.products_list_url,
            {"name": "Keyboard", "description": "Mechanical", "price": "200.00", "stock": 5},
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_403_FORBIDDEN)

        # ადმინს შეუძლია შექმნა, განახლება და წაშლა
        self.authenticate_as("admin_user", "AdminPassword123!")
        admin_create_res = self.client.post(
            self.products_list_url,
            {"name": "Keyboard", "description": "Mechanical", "price": "200.00", "stock": 5},
            format="json",
        )
        self.assertEqual(admin_create_res.status_code, status.HTTP_201_CREATED)
        created_id = admin_create_res.data["id"]

        detail_url = reverse("product-detail", kwargs={"pk": created_id})
        patch_res = self.client.patch(detail_url, {"price": "180.00"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(patch_res.data["price"]), Decimal("180.00"))

        delete_res = self.client.delete(detail_url)
        self.assertEqual(delete_res.status_code, status.HTTP_204_NO_CONTENT)

    def test_user_select_product_and_free_test_checkout(self):
        self.authenticate_as("buyer_user", "BuyerPassword123!")

        # 1. მომხმარებელი ირჩევს პროდუქტს (quantity=3 -> ჯამი 360.00)
        select_res = self.client.post(
            self.selected_list_url,
            {"product": self.product.id, "quantity": 3},
            format="json",
        )
        self.assertEqual(select_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(select_res.data["subtotal"]), Decimal("360.00"))

        # 2. უფასო სატესტო გადახდა
        checkout_res = self.client.post(
            self.checkout_url,
            {"test_card_or_method": "FREE_TEST_CARD_4242"},
            format="json",
        )
        self.assertEqual(checkout_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(checkout_res.data["order"]["status"], Order.Status.PAID)
        self.assertEqual(Decimal(checkout_res.data["order"]["total_amount"]), Decimal("360.00"))

        # 3. მარაგი უნდა შემცირდეს 10-დან 7-მდე
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7)

        # 4. შერჩეული პროდუქტების სია უნდა გასუფთავდეს
        self.assertEqual(SelectedProduct.objects.filter(user=self.buyer).count(), 0)

        # 5. შეკვეთების ისტორიაში უნდა ჩანდეს შეკვეთა
        orders_res = self.client.get(self.orders_url)
        self.assertEqual(orders_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(orders_res.data), 1)
        self.assertEqual(orders_res.data[0]["items"][0]["product_name"], "Gaming Mouse")
        self.assertEqual(orders_res.data[0]["items"][0]["quantity"], 3)