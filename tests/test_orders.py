import pytest
from django.core.management import call_command
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditLog
from apps.orders.constants import OrderStatus
from apps.orders.models import Customer, Order, OrderItem
from apps.orders.serializers import OrderItemSerializer, OrderSerializer
from apps.orders.services import change_order_status, create_order, delete_order, update_order


pytestmark = pytest.mark.django_db


def _create_order_via_api(client, customer, product, quantity=2, price="99.90"):
    return client.post(
        "/api/orders/",
        {
            "customer": customer.id,
            "items": [{"product": product.id, "quantity": quantity, "price": price}],
        },
        format="json",
    )


def test_customer_crud_permissions_and_str(authenticated_client, manager_user, worker_user):
    manager_client = authenticated_client(manager_user)

    create_response = manager_client.post(
        "/api/customers/",
        {
            "name": "Client B",
            "email": "client-b@example.com",
            "phone": "+10000000002",
            "address": "2 Market Street",
        },
        format="json",
    )
    customer_id = create_response.data["id"]
    customer = Customer.objects.get(pk=customer_id)
    update_response = manager_client.patch(
        f"/api/customers/{customer_id}/",
        {"phone": "+19999999999"},
        format="json",
    )
    list_response = manager_client.get("/api/customers/")
    delete_response = manager_client.delete(f"/api/customers/{customer_id}/")

    worker_client = authenticated_client(worker_user)
    worker_response = worker_client.get("/api/customers/")

    assert create_response.status_code == 201
    assert str(customer) == "Client B"
    assert update_response.status_code == 200
    assert list_response.status_code == 200
    assert delete_response.status_code == 204
    assert worker_response.status_code == 403
    assert AuditLog.objects.filter(entity="Customer", action="DELETE").exists()


def test_delete_customer_linked_to_order_returns_400(authenticated_client, manager_user, customer):
    Order.objects.create(customer=customer, created_by=manager_user)
    client = authenticated_client(manager_user)

    response = client.delete(f"/api/customers/{customer.id}/")

    assert response.status_code == 400
    assert "linked to existing orders" in response.data["detail"]
    assert Customer.objects.filter(pk=customer.pk).exists()


def test_order_create_over_available_stock_returns_400(authenticated_client, manager_user, stock_item, customer, product):
    client = authenticated_client(manager_user)

    response = _create_order_via_api(client, customer, product, quantity=stock_item.quantity + 1)

    assert response.status_code == 400
    assert "items" in response.data


def test_order_create_does_not_reserve_stock_until_status_changes(authenticated_client, manager_user, stock_item, customer, product):
    client = authenticated_client(manager_user)

    response = _create_order_via_api(client, customer, product, quantity=3)
    stock_item.refresh_from_db()

    assert response.status_code == 201
    assert stock_item.quantity == 10
    assert stock_item.reserved_quantity == 0


def test_order_create_with_empty_items_returns_400(authenticated_client, manager_user, customer):
    client = authenticated_client(manager_user)

    response = client.post(
        "/api/orders/",
        {"customer": customer.id, "items": []},
        format="json",
    )

    assert response.status_code == 400
    assert "items" in response.data


def test_order_create_rejects_invalid_item_quantity_and_price(authenticated_client, manager_user, customer, product):
    client = authenticated_client(manager_user)

    response = client.post(
        "/api/orders/",
        {
            "customer": customer.id,
            "items": [{"product": product.id, "quantity": 0, "price": "-1.00"}],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "items" in response.data


def test_order_created_reserved_shipped_flow_updates_stock(authenticated_client, manager_user, stock_item, customer, product):
    client = authenticated_client(manager_user)
    create_response = _create_order_via_api(client, customer, product, quantity=3)
    order_id = create_response.data["id"]

    reserve_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.RESERVED},
        format="json",
    )
    stock_item.refresh_from_db()

    ship_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.SHIPPED},
        format="json",
    )
    stock_item.refresh_from_db()

    assert create_response.status_code == 201
    assert reserve_response.status_code == 200
    assert ship_response.status_code == 200
    assert stock_item.quantity == 7
    assert stock_item.reserved_quantity == 0


def test_cancelled_reserved_order_releases_reserve(authenticated_client, manager_user, stock_item, customer, product):
    client = authenticated_client(manager_user)
    create_response = _create_order_via_api(client, customer, product, quantity=4)
    order_id = create_response.data["id"]
    client.post(f"/api/orders/{order_id}/change-status/", {"status": OrderStatus.RESERVED}, format="json")
    stock_item.refresh_from_db()
    assert stock_item.reserved_quantity == 4

    cancel_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.CANCELLED},
        format="json",
    )
    stock_item.refresh_from_db()

    assert cancel_response.status_code == 200
    assert cancel_response.data["status"] == OrderStatus.CANCELLED
    assert stock_item.reserved_quantity == 0


def test_cancelled_created_order_does_not_change_stock(authenticated_client, manager_user, stock_item, customer, product):
    client = authenticated_client(manager_user)
    create_response = _create_order_via_api(client, customer, product, quantity=4)
    order_id = create_response.data["id"]

    cancel_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.CANCELLED},
        format="json",
    )
    stock_item.refresh_from_db()

    assert cancel_response.status_code == 200
    assert stock_item.quantity == 10
    assert stock_item.reserved_quantity == 0


def test_completed_order_cannot_be_modified_deleted_or_changed_again(
    authenticated_client,
    manager_user,
    stock_item,
    customer,
    product,
):
    client = authenticated_client(manager_user)
    create_response = _create_order_via_api(client, customer, product, quantity=2)
    order_id = create_response.data["id"]
    client.post(f"/api/orders/{order_id}/change-status/", {"status": OrderStatus.RESERVED}, format="json")
    client.post(f"/api/orders/{order_id}/change-status/", {"status": OrderStatus.SHIPPED}, format="json")
    complete_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.COMPLETED},
        format="json",
    )

    patch_response = client.patch(
        f"/api/orders/{order_id}/",
        {"customer": customer.id},
        format="json",
    )
    delete_response = client.delete(f"/api/orders/{order_id}/")
    second_status_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.CANCELLED},
        format="json",
    )

    assert complete_response.status_code == 200
    assert Order.objects.get(pk=order_id).status == OrderStatus.COMPLETED
    assert patch_response.status_code == 400
    assert delete_response.status_code == 400
    assert second_status_response.status_code == 400


def test_order_permissions_for_worker(authenticated_client, manager_user, worker_user, stock_item, customer, product):
    worker_client = authenticated_client(worker_user)
    manager_client = authenticated_client(manager_user)
    create_response = _create_order_via_api(manager_client, customer, product, quantity=1)
    order_id = create_response.data["id"]

    worker_list_response = worker_client.get("/api/orders/")
    worker_create_response = _create_order_via_api(worker_client, customer, product, quantity=1)
    worker_status_response = worker_client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.RESERVED},
        format="json",
    )

    assert worker_list_response.status_code == 200
    assert worker_create_response.status_code == 403
    assert worker_status_response.status_code == 403


def test_order_list_requires_authentication(api_client):
    response = api_client.get("/api/orders/")

    assert response.status_code == 401


def test_order_update_destroy_and_status_validation_paths(
    authenticated_client,
    manager_user,
    stock_item,
    customer,
    customer_factory,
    product,
):
    client = authenticated_client(manager_user)
    create_response = _create_order_via_api(client, customer, product, quantity=1)
    order_id = create_response.data["id"]
    other_customer = customer_factory(email="other@example.com")

    patch_response = client.patch(
        f"/api/orders/{order_id}/",
        {
            "customer": other_customer.id,
            "items": [{"product": product.id, "quantity": 2, "price": "88.00"}],
        },
        format="json",
    )
    same_status_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.CREATED},
        format="json",
    )
    invalid_transition_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.SHIPPED},
        format="json",
    )
    invalid_status_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": "UNKNOWN"},
        format="json",
    )
    reserve_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.RESERVED},
        format="json",
    )
    update_reserved_response = client.patch(
        f"/api/orders/{order_id}/",
        {"items": [{"product": product.id, "quantity": 1, "price": "88.00"}]},
        format="json",
    )
    delete_reserved_response = client.delete(f"/api/orders/{order_id}/")
    stock_item.refresh_from_db()

    assert patch_response.status_code == 200
    assert same_status_response.status_code == 400
    assert invalid_transition_response.status_code == 400
    assert invalid_status_response.status_code == 400
    assert reserve_response.status_code == 200
    assert update_reserved_response.status_code == 400
    assert delete_reserved_response.status_code == 204
    assert stock_item.reserved_quantity == 0


def test_cancelled_order_cannot_be_changed_or_updated(authenticated_client, manager_user, stock_item, customer, product):
    client = authenticated_client(manager_user)
    create_response = _create_order_via_api(client, customer, product, quantity=1)
    order_id = create_response.data["id"]
    client.post(f"/api/orders/{order_id}/change-status/", {"status": OrderStatus.CANCELLED}, format="json")

    update_response = client.patch(f"/api/orders/{order_id}/", {"customer": customer.id}, format="json")
    status_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.RESERVED},
        format="json",
    )

    assert update_response.status_code == 400
    assert status_response.status_code == 400


def test_order_reservation_spans_multiple_stock_items(
    authenticated_client,
    manager_user,
    stock_item,
    warehouse_factory,
    customer,
    product,
):
    second_warehouse = warehouse_factory(name="Overflow")
    second_stock = stock_item.__class__.objects.create(
        product=product,
        warehouse=second_warehouse,
        quantity=5,
        reserved_quantity=0,
    )
    stock_item.quantity = 2
    stock_item.save(update_fields=["quantity"])

    client = authenticated_client(manager_user)
    create_response = _create_order_via_api(client, customer, product, quantity=4)
    order_id = create_response.data["id"]
    reserve_response = client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.RESERVED},
        format="json",
    )
    stock_item.refresh_from_db()
    second_stock.refresh_from_db()

    assert reserve_response.status_code == 200
    assert stock_item.reserved_quantity == 2
    assert second_stock.reserved_quantity == 2


def test_order_serializers_validate_items_quantity_and_price(customer, product, manager_user):
    create_serializer = OrderSerializer(data={"customer": customer.id, "items": []})
    assert not create_serializer.is_valid()
    assert "items" in create_serializer.errors

    order = Order.objects.create(customer=customer, created_by=manager_user)
    update_serializer = OrderSerializer(order, data={"items": []}, partial=True)
    assert not update_serializer.is_valid()
    assert "items" in update_serializer.errors

    item_serializer = OrderItemSerializer(data={"product": product.id, "quantity": 0, "price": "-1.00"})
    assert not item_serializer.is_valid()
    assert "quantity" in item_serializer.errors
    assert "price" in item_serializer.errors

    serializer = OrderItemSerializer()
    with pytest.raises(ValidationError, match="Quantity must be greater than 0"):
        serializer.validate_quantity(0)
    with pytest.raises(ValidationError, match="Price must be greater than or equal to 0"):
        serializer.validate_price(-1)


def test_order_service_direct_error_and_default_price_paths(manager_user, stock_item, customer, product):
    order = create_order(
        customer=customer,
        items=[{"product": product, "quantity": 1, "price": None}],
        created_by=manager_user,
    )
    order_item = order.items.get()

    assert order_item.price == 0
    assert str(order) == f"Order #{order.pk} - {OrderStatus.CREATED}"
    assert str(order_item) == f"{product} x 1"

    with pytest.raises(ValidationError, match="Completed orders cannot be modified"):
        order.status = OrderStatus.COMPLETED
        order.save(update_fields=["status"])
        update_order(order, {"customer": customer}, manager_user)

    with pytest.raises(ValidationError, match="Completed orders cannot be deleted"):
        delete_order(order, manager_user)


def test_seed_data_command_creates_demo_data():
    call_command("seed_data")

    assert Order.objects.count() == 2
    assert Order.objects.filter(status=OrderStatus.RESERVED).exists()
    assert AuditLog.objects.filter(entity="Order", action="CREATE").count() == 2
