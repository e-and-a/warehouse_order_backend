import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Warehouse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("address", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="StockItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                (
                    "reserved_quantity",
                    models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)]),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_items",
                        to="catalog.product",
                    ),
                ),
                (
                    "warehouse",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_items",
                        to="warehouse.warehouse",
                    ),
                ),
            ],
            options={
                "ordering": ["warehouse__name", "product__name"],
                "constraints": [
                    models.UniqueConstraint(fields=("product", "warehouse"), name="unique_stock_product_warehouse"),
                    models.CheckConstraint(condition=Q(("quantity__gte", 0)), name="stock_quantity_non_negative"),
                    models.CheckConstraint(condition=Q(("reserved_quantity__gte", 0)), name="stock_reserved_non_negative"),
                    models.CheckConstraint(condition=Q(("reserved_quantity__lte", F("quantity"))), name="stock_reserved_lte_quantity"),
                ],
            },
        ),
    ]
