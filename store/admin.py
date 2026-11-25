from django.contrib import admin
from .models import Order, OrderItem, Product, SelectedProduct

admin.site.register(Product)
admin.site.register(SelectedProduct)
admin.site.register(Order)
admin.site.register(OrderItem)