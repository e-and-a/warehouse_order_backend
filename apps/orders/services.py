from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.audit.constants import AuditAction
from apps.audit.services import log_action
from apps.catalog.models import Product
from apps.orders.constants import OrderStatus
from apps.orders.models import Customer, Order, OrderItem
from apps.warehouse.services import (
    get_available_quantity,
    release_reserved_product,
    reserve_product,
    ship_reserved_product,
)


ALLOWED_TRANSITIONS = {
    OrderStatus.CREATED: {OrderStatus.RESERVED, OrderStatus.CANCELLED},
    OrderStatus.RESERVED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.COMPLETED},
}


def _quantity_by_product(items: list[dict]) -> dict[Product, int]:
    quantities: dict[Product, int] = defaultdict(int)
    for item in items:
        quantities[item["product"]] += item["quantity"]
    return dict(quantities)


def _validate_available_stock(items: list[dict]) -> None:
    for product, quantity in _quantity_by_product(items).items():
        available = get_available_quantity(product)
        if quantity > available:
            raise ValidationError(
                {
                    "items": (
                        f"Not enough stock for product {product.sku}. "
                        f"Requested {quantity}, available {available}."
                    )
                }
            )


def _create_order_items(order: Order, items: list[dict]) -> None:
    order_items = []
    for item in items:
        product = item["product"]
        price = item.get("price", product.price)
        if price is None:
            price = Decimal("0.00")
        order_items.append(
            OrderItem(
                order=order,
                product=product,
                quantity=item["quantity"],
                price=price,
            )
        )
    OrderItem.objects.bulk_create(order_items)


def create_order(customer: Customer, items: list[dict], created_by) -> Order:
    with transaction.atomic():
        _validate_available_stock(items)
        order = Order.objects.create(customer=customer, created_by=created_by)
        _create_order_items(order, items)
        log_action(created_by, AuditAction.CREATE, order)
        return Order.objects.select_related("customer", "created_by").prefetch_related("items__product").get(pk=order.pk)


def update_order(order: Order, validated_data: dict, user) -> Order:
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if locked_order.status == OrderStatus.COMPLETED:
            raise ValidationError({"status": "Completed orders cannot be modified."})
        if locked_order.status == OrderStatus.CANCELLED:
            raise ValidationError({"status": "Cancelled orders cannot be modified."})

        items = validated_data.pop("items", None)
        if items is not None and locked_order.status != OrderStatus.CREATED:
            raise ValidationError({"items": "Items can only be changed while order status is CREATED."})

        if "customer" in validated_data:
            locked_order.customer = validated_data["customer"]
        locked_order.save(update_fields=["customer", "updated_at"])

        if items is not None:
            _validate_available_stock(items)
            locked_order.items.all().delete()
            _create_order_items(locked_order, items)

        log_action(user, AuditAction.UPDATE, locked_order)
        return Order.objects.select_related("customer", "created_by").prefetch_related("items__product").get(pk=locked_order.pk)


def delete_order(order: Order, user) -> None:
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().prefetch_related("items__product").get(pk=order.pk)
        if locked_order.status == OrderStatus.COMPLETED:
            raise ValidationError({"status": "Completed orders cannot be deleted."})
        if locked_order.status == OrderStatus.RESERVED:
            for item in locked_order.items.all():
                release_reserved_product(item.product, item.quantity)
        log_action(user, AuditAction.DELETE, locked_order)
        locked_order.delete()


def change_order_status(order: Order, new_status: str, user) -> Order:
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().prefetch_related("items__product").get(pk=order.pk)
        current_status = locked_order.status

        if current_status == OrderStatus.COMPLETED:
            raise ValidationError({"status": "Completed orders cannot change status."})
        if current_status == OrderStatus.CANCELLED:
            raise ValidationError({"status": "Cancelled orders cannot change status."})
        if new_status == current_status:
            raise ValidationError({"status": "Order already has this status."})
        if new_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise ValidationError(
                {"status": f"Invalid status transition from {current_status} to {new_status}."}
            )

        if new_status == OrderStatus.RESERVED:
            for item in locked_order.items.all():
                reserve_product(item.product, item.quantity)
        elif new_status == OrderStatus.SHIPPED:
            for item in locked_order.items.all():
                ship_reserved_product(item.product, item.quantity)
        elif new_status == OrderStatus.CANCELLED and current_status == OrderStatus.RESERVED:
            for item in locked_order.items.all():
                release_reserved_product(item.product, item.quantity)

        locked_order.status = new_status
        locked_order.save(update_fields=["status", "updated_at"])
        log_action(user, AuditAction.STATUS_CHANGE, locked_order)
        return Order.objects.select_related("customer", "created_by").prefetch_related("items__product").get(pk=locked_order.pk)
