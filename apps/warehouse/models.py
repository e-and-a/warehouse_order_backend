from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.catalog.models import Product


class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class StockItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_items")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="stock_items")
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    reserved_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["warehouse__name", "product__name"]
        constraints = [
            models.UniqueConstraint(fields=["product", "warehouse"], name="unique_stock_product_warehouse"),
            models.CheckConstraint(condition=Q(quantity__gte=0), name="stock_quantity_non_negative"),
            models.CheckConstraint(condition=Q(reserved_quantity__gte=0), name="stock_reserved_non_negative"),
            models.CheckConstraint(condition=Q(reserved_quantity__lte=F("quantity")), name="stock_reserved_lte_quantity"),
        ]

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity

    def __str__(self) -> str:
        return f"{self.product} at {self.warehouse}: {self.quantity}"
