from django.contrib import admin

from apps.warehouse.models import StockItem, Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "address", "created_at"]
    search_fields = ["name", "address"]
    list_filter = ["created_at"]


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "warehouse", "quantity", "reserved_quantity", "available_quantity", "updated_at"]
    list_filter = ["warehouse", "updated_at"]
    search_fields = ["product__name", "product__sku", "warehouse__name"]
