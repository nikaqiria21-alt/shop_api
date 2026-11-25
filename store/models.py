from decimal import Decimal
from django.conf import settings
from django.db import models


class Product(models.Model):
    #პროდუქტი — ამატებს, აახლებს და შლის მხოლოდ ადმინისტრატორი
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.price} GEL)"


class SelectedProduct(models.Model):
    #მომხმარებლის მიერ არჩეული სასურველი პროდუქტები
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="selected_products",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="selected_by_users",
    )
    quantity = models.PositiveIntegerField(default=1)
    selected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-selected_at"]

    @property
    def subtotal(self) -> Decimal:
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.user.username} -> {self.product.name} x{self.quantity}"


class Order(models.Model):
    #გადახდილი სატესტოდ დადასტურებული შეკვეთა
    class Status(models.TextChoices):
        PAID = "PAID", "Paid (Test)"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, default="FREE_TEST_SANDBOX")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PAID)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.total_amount} ({self.status})"


class OrderItem(models.Model):
    #შეკვეთაში შესული პროდუქტების სნეპშოტი
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"