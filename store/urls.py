from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    OrderListView,
    ProductViewSet,
    RegisterView,
    SelectedProductViewSet,
    TestCheckoutView,
)

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"selected-products", SelectedProductViewSet, basename="selected-product")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("checkout/test/", TestCheckoutView.as_view(), name="test-checkout"),
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("", include(router.urls)),
]