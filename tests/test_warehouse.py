import pytest
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditLog
from apps.users.constants import UserRole
from apps.warehouse.models import StockItem, Warehouse
from apps.warehouse.serializers import StockItemSerializer
from apps.warehouse.services import (
    get_available_quantity,
    release_reserved_product,
    reserve_product,
    ship_reserved_product,
    update_stock_item,
)


pytestmark = pytest.mark.django_db


def test_warehouse_crud_permissions_and_str(authenticated_client, manager_user, worker_user):
    manager_client = authenticated_client(manager_user)

    create_response = manager_client.post(
        "/api/warehouses/",
        {"name": "Secondary", "address": "2 Storage Street"},
        format="json",
    )
    warehouse_id = create_response.data["id"]
    warehouse = Warehouse.objects.get(pk=warehouse_id)
    update_response = manager_client.patch(
        f"/api/warehouses/{warehouse_id}/",
        {"address": "Updated address"},
        format="json",
    )
    list_response = manager_client.get("/api/warehouses/")
    delete_response = manager_client.delete(f"/api/warehouses/{warehouse_id}/")

    worker_client = authenticated_client(worker_user)
    worker_create_response = worker_client.post(
        "/api/warehouses/",
        {"name": "Blocked", "address": "No access"},
        format="json",
    )

    assert create_response.status_code == 201
    assert str(warehouse) == "Secondary"
    assert update_response.status_code == 200
    assert list_response.status_code == 200
    assert delete_response.status_code == 204
    assert worker_create_response.status_code == 403
    assert AuditLog.objects.filter(entity="Warehouse", action="DELETE").exists()


def test_stock_crud_permissions_and_validations(
    authenticated_client,
    manager_user,
    worker_user,
    product,
    product_factory,
    warehouse,
    warehouse_factory,
):
    manager_client = authenticated_client(manager_user)
    stock_product = product_factory(sku="STK-100")
    create_response = manager_client.post(
        "/api/stock/",
        {
            "product": stock_product.id,
            "warehouse": warehouse.id,
            "quantity": 10,
            "reserved_quantity": 2,
        },
        format="json",
    )
    stock_id = create_response.data["id"]
    stock_item = StockItem.objects.get(pk=stock_id)

    update_response = manager_client.patch(
        f"/api/stock/{stock_id}/",
        {"reserved_quantity": 3},
        format="json",
    )
    list_response = manager_client.get("/api/stock/")

    worker_client = authenticated_client(worker_user)
    worker_update_response = worker_client.patch(
        f"/api/stock/{stock_id}/",
        {"quantity": 12},
        format="json",
    )
    worker_retarget_response = worker_client.patch(
        f"/api/stock/{stock_id}/",
        {"warehouse": warehouse_factory(name="Other warehouse").id},
        format="json",
    )
    worker_create_response = worker_client.post(
        "/api/stock/",
        {
            "product": product.id,
            "warehouse": warehouse.id,
            "quantity": 1,
            "reserved_quantity": 0,
        },
        format="json",
    )
    worker_delete_response = worker_client.delete(f"/api/stock/{stock_id}/")

    invalid_quantity_response = manager_client.post(
        "/api/stock/",
        {
            "product": product.id,
            "warehouse": warehouse.id,
            "quantity": -1,
            "reserved_quantity": 0,
        },
        format="json",
    )
    invalid_reserved_response = manager_client.post(
        "/api/stock/",
        {
            "product": product.id,
            "warehouse": warehouse.id,
            "quantity": 5,
            "reserved_quantity": -1,
        },
        format="json",
    )
    reserved_gt_quantity_response = manager_client.post(
        "/api/stock/",
        {
            "product": product.id,
            "warehouse": warehouse.id,
            "quantity": 5,
            "reserved_quantity": 6,
        },
        format="json",
    )
    duplicate_response = manager_client.post(
        "/api/stock/",
        {
            "product": stock_product.id,
            "warehouse": warehouse.id,
            "quantity": 1,
            "reserved_quantity": 0,
        },
        format="json",
    )

    delete_response = manager_client.delete(f"/api/stock/{stock_id}/")

    assert create_response.status_code == 201
    assert stock_item.available_quantity == 8
    assert str(stock_item) == f"{stock_item.product} at {stock_item.warehouse}: 10"
    assert update_response.status_code == 200
    assert list_response.status_code == 200
    assert worker_update_response.status_code == 200
    assert worker_retarget_response.status_code == 403
    assert worker_create_response.status_code == 403
    assert worker_delete_response.status_code == 403
    assert invalid_quantity_response.status_code == 400
    assert invalid_reserved_response.status_code == 400
    assert reserved_gt_quantity_response.status_code == 400
    assert duplicate_response.status_code == 400
    assert delete_response.status_code == 204
    assert AuditLog.objects.filter(entity="StockItem", action="DELETE").exists()


def test_stock_item_serializer_custom_validation_lines(product, warehouse, stock_item):
    duplicate_serializer = StockItemSerializer()
    with pytest.raises(ValidationError, match="already exists"):
        duplicate_serializer.validate({"product": product, "warehouse": warehouse, "quantity": 1, "reserved_quantity": 0})

    instance_serializer = StockItemSerializer(instance=stock_item)
    with pytest.raises(ValidationError, match="Quantity must be greater than or equal to 0"):
        instance_serializer.validate({"quantity": -1})
    with pytest.raises(ValidationError, match="Reserved quantity must be greater than or equal to 0"):
        instance_serializer.validate({"reserved_quantity": -1})


def test_stock_services_success_paths(product, warehouse, manager_user):
    first = StockItem.objects.create(product=product, warehouse=warehouse, quantity=5, reserved_quantity=5)
    second_warehouse = Warehouse.objects.create(name="Second", address="Second address")
    second = StockItem.objects.create(product=product, warehouse=second_warehouse, quantity=10, reserved_quantity=0)

    assert get_available_quantity(product) == 10

    reserve_product(product, 4)
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.reserved_quantity == 5
    assert second.reserved_quantity == 4

    release_reserved_product(product, 6)
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.reserved_quantity == 0
    assert second.reserved_quantity == 3

    ship_reserved_product(product, 3)
    second.refresh_from_db()
    assert second.quantity == 7
    assert second.reserved_quantity == 0

    updated = update_stock_item(second, {"quantity": 9, "reserved_quantity": 1}, manager_user)
    assert updated.quantity == 9
    assert updated.reserved_quantity == 1


def test_worker_can_update_existing_stock_quantities(authenticated_client, worker_user, stock_item):
    client = authenticated_client(worker_user)

    response = client.patch(
        f"/api/stock/{stock_item.id}/",
        {"quantity": 15, "reserved_quantity": 1},
        format="json",
    )
    stock_item.refresh_from_db()

    assert response.status_code == 200
    assert stock_item.quantity == 15
    assert stock_item.reserved_quantity == 1


def test_stock_update_rejects_reserved_greater_than_quantity(authenticated_client, manager_user, stock_item):
    client = authenticated_client(manager_user)

    response = client.patch(
        f"/api/stock/{stock_item.id}/",
        {"reserved_quantity": stock_item.quantity + 1},
        format="json",
    )

    assert response.status_code == 400
    assert "reserved_quantity" in response.data


def test_stock_services_validation_errors(product, product_factory, stock_item, manager_user):
    product_without_stock = product_factory(sku="NO-STOCK")

    with pytest.raises(ValidationError, match="Quantity must be greater than 0"):
        reserve_product(product, 0)
    with pytest.raises(ValidationError, match="Quantity must be greater than 0"):
        release_reserved_product(product, 0)
    with pytest.raises(ValidationError, match="Quantity must be greater than 0"):
        ship_reserved_product(product, 0)
    with pytest.raises(ValidationError, match="Not enough available stock"):
        reserve_product(product, 99)
    with pytest.raises(ValidationError, match="Reserved stock"):
        release_reserved_product(product_without_stock, 1)
    with pytest.raises(ValidationError, match="Reserved stock"):
        ship_reserved_product(product_without_stock, 1)
    with pytest.raises(ValidationError, match="Quantity must be greater than or equal to 0"):
        update_stock_item(stock_item, {"quantity": -1}, manager_user)
    with pytest.raises(ValidationError, match="Reserved quantity must be greater than or equal to 0"):
        update_stock_item(stock_item, {"reserved_quantity": -1}, manager_user)
    with pytest.raises(ValidationError, match="Reserved quantity cannot exceed quantity"):
        update_stock_item(stock_item, {"reserved_quantity": 11}, manager_user)
