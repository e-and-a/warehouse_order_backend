from rest_framework import serializers

from apps.warehouse.models import StockItem, Warehouse


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "name", "address", "created_at"]
        read_only_fields = ["id", "created_at"]


class StockItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = StockItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "warehouse",
            "warehouse_name",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "product_name",
            "product_sku",
            "warehouse_name",
            "available_quantity",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        product = attrs.get("product", self.instance.product if self.instance else None)
        warehouse = attrs.get("warehouse", self.instance.warehouse if self.instance else None)
        quantity = attrs.get("quantity", self.instance.quantity if self.instance else None)
        reserved_quantity = attrs.get(
            "reserved_quantity",
            self.instance.reserved_quantity if self.instance else 0,
        )
        if product and warehouse:
            duplicate = StockItem.objects.filter(product=product, warehouse=warehouse)
            if self.instance:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": "Stock item for this product and warehouse already exists."}
                )
        if quantity is not None and quantity < 0:
            raise serializers.ValidationError({"quantity": "Quantity must be greater than or equal to 0."})
        if reserved_quantity < 0:
            raise serializers.ValidationError({"reserved_quantity": "Reserved quantity must be greater than or equal to 0."})
        if quantity is not None and reserved_quantity > quantity:
            raise serializers.ValidationError({"reserved_quantity": "Reserved quantity cannot exceed quantity."})
        return attrs
