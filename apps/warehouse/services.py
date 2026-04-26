from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from apps.audit.constants import AuditAction
from apps.audit.services import log_action
from apps.catalog.models import Product
from apps.warehouse.models import StockItem


def get_available_quantity(product: Product) -> int:
    totals = StockItem.objects.filter(product=product).aggregate(
        quantity=Sum("quantity"),
        reserved_quantity=Sum("reserved_quantity"),
    )
    quantity = totals["quantity"] or 0
    reserved_quantity = totals["reserved_quantity"] or 0
    return quantity - reserved_quantity


def update_stock_item(stock_item: StockItem, validated_data: dict, user) -> StockItem:
    with transaction.atomic():
        locked = StockItem.objects.select_for_update().get(pk=stock_item.pk)
        for field in ["product", "warehouse", "quantity", "reserved_quantity"]:
            if field in validated_data:
                setattr(locked, field, validated_data[field])
        if locked.quantity < 0:
            raise ValidationError({"quantity": "Quantity must be greater than or equal to 0."})
        if locked.reserved_quantity < 0:
            raise ValidationError({"reserved_quantity": "Reserved quantity must be greater than or equal to 0."})
        if locked.reserved_quantity > locked.quantity:
            raise ValidationError({"reserved_quantity": "Reserved quantity cannot exceed quantity."})
        locked.save()
        log_action(user, AuditAction.UPDATE, locked)
        return locked


def reserve_product(product: Product, quantity: int) -> None:
    if quantity <= 0:
        raise ValidationError({"quantity": "Quantity must be greater than 0."})

    remaining = quantity
    stock_items = (
        StockItem.objects.select_for_update()
        .filter(product=product, quantity__gt=0)
        .order_by("warehouse_id", "id")
    )

    for stock_item in stock_items:
        available = stock_item.available_quantity
        if available <= 0:
            continue
        reserved = min(available, remaining)
        stock_item.reserved_quantity += reserved
        stock_item.save(update_fields=["reserved_quantity", "updated_at"])
        remaining -= reserved
        if remaining == 0:
            return

    raise ValidationError({"items": f"Not enough available stock for product {product.sku}."})


def release_reserved_product(product: Product, quantity: int) -> None:
    if quantity <= 0:
        raise ValidationError({"quantity": "Quantity must be greater than 0."})

    remaining = quantity
    stock_items = (
        StockItem.objects.select_for_update()
        .filter(product=product, reserved_quantity__gt=0)
        .order_by("warehouse_id", "id")
    )

    for stock_item in stock_items:
        released = min(stock_item.reserved_quantity, remaining)
        stock_item.reserved_quantity -= released
        stock_item.save(update_fields=["reserved_quantity", "updated_at"])
        remaining -= released
        if remaining == 0:
            return

    raise ValidationError({"stock": f"Reserved stock for product {product.sku} is inconsistent."})


def ship_reserved_product(product: Product, quantity: int) -> None:
    if quantity <= 0:
        raise ValidationError({"quantity": "Quantity must be greater than 0."})

    remaining = quantity
    stock_items = (
        StockItem.objects.select_for_update()
        .filter(product=product, reserved_quantity__gt=0)
        .order_by("warehouse_id", "id")
    )

    for stock_item in stock_items:
        shipped = min(stock_item.reserved_quantity, remaining)
        stock_item.reserved_quantity -= shipped
        stock_item.quantity -= shipped
        stock_item.save(update_fields=["quantity", "reserved_quantity", "updated_at"])
        remaining -= shipped
        if remaining == 0:
            return

    raise ValidationError({"stock": f"Reserved stock for product {product.sku} is inconsistent."})
