from django.contrib import admin

from apps.orders.models import Customer, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ["product"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "email", "phone", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "email", "phone"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "status", "created_by", "created_at", "updated_at"]
    list_filter = ["status", "created_at", "updated_at"]
    search_fields = ["id", "customer__name", "customer__email", "created_by__email"]
    autocomplete_fields = ["customer", "created_by"]
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "product", "quantity", "price"]
    list_filter = ["product"]
    search_fields = ["order__id", "product__name", "product__sku"]
