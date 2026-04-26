import pytest

from apps.orders.constants import OrderStatus
from apps.orders.models import Order


pytestmark = pytest.mark.django_db


def test_user_login_returns_jwt(api_client, manager_user):
    response = api_client.post(
        "/api/auth/token/",
        {"email": "manager@example.com", "password": "Manager123!"},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


def test_api_without_jwt_returns_401(api_client):
    response = api_client.get("/api/products/")

    assert response.status_code == 401


def test_user_without_required_role_gets_403(api_client, worker_user, category):
    api_client.force_authenticate(user=worker_user)
    response = api_client.post(
        "/api/products/",
        {
            "name": "Laptop",
            "sku": "LAP-403",
            "description": "Blocked",
            "price": "1000.00",
            "category": category.id,
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 403


def test_manager_can_create_product(api_client, manager_user, category):
    api_client.force_authenticate(user=manager_user)
    response = api_client.post(
        "/api/products/",
        {
            "name": "Laptop",
            "sku": "LAP-100",
            "description": "Workstation",
            "price": "1500.00",
            "category": category.id,
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["sku"] == "LAP-100"


def test_worker_cannot_create_product(api_client, worker_user, category):
    api_client.force_authenticate(user=worker_user)
    response = api_client.post(
        "/api/products/",
        {
            "name": "Laptop",
            "sku": "LAP-101",
            "description": "Workstation",
            "price": "1500.00",
            "category": category.id,
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 403


def test_cannot_create_stock_item_with_negative_quantity(api_client, manager_user, product, warehouse):
    api_client.force_authenticate(user=manager_user)
    response = api_client.post(
        "/api/stock/",
        {
            "product": product.id,
            "warehouse": warehouse.id,
            "quantity": -1,
            "reserved_quantity": 0,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "quantity" in response.data


def test_cannot_create_order_over_available_stock(api_client, manager_user, stock_item, customer, product):
    api_client.force_authenticate(user=manager_user)
    response = api_client.post(
        "/api/orders/",
        {
            "customer": customer.id,
            "items": [{"product": product.id, "quantity": stock_item.quantity + 1, "price": "99.90"}],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "items" in response.data


def test_order_status_changes_update_reserved_and_quantity(api_client, manager_user, stock_item, customer, product):
    api_client.force_authenticate(user=manager_user)
    create_response = api_client.post(
        "/api/orders/",
        {
            "customer": customer.id,
            "items": [{"product": product.id, "quantity": 3, "price": "99.90"}],
        },
        format="json",
    )
    order_id = create_response.data["id"]

    reserve_response = api_client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.RESERVED},
        format="json",
    )
    stock_item.refresh_from_db()

    assert reserve_response.status_code == 200
    assert stock_item.quantity == 10
    assert stock_item.reserved_quantity == 3

    ship_response = api_client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.SHIPPED},
        format="json",
    )
    stock_item.refresh_from_db()

    assert ship_response.status_code == 200
    assert stock_item.quantity == 7
    assert stock_item.reserved_quantity == 0


def test_completed_order_cannot_be_modified_or_changed_again(api_client, manager_user, stock_item, customer, product):
    api_client.force_authenticate(user=manager_user)
    create_response = api_client.post(
        "/api/orders/",
        {
            "customer": customer.id,
            "items": [{"product": product.id, "quantity": 2, "price": "99.90"}],
        },
        format="json",
    )
    order_id = create_response.data["id"]
    api_client.post(f"/api/orders/{order_id}/change-status/", {"status": OrderStatus.RESERVED}, format="json")
    api_client.post(f"/api/orders/{order_id}/change-status/", {"status": OrderStatus.SHIPPED}, format="json")
    complete_response = api_client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.COMPLETED},
        format="json",
    )

    assert complete_response.status_code == 200
    assert Order.objects.get(pk=order_id).status == OrderStatus.COMPLETED

    patch_response = api_client.patch(
        f"/api/orders/{order_id}/",
        {"customer": customer.id},
        format="json",
    )
    second_status_response = api_client.post(
        f"/api/orders/{order_id}/change-status/",
        {"status": OrderStatus.CANCELLED},
        format="json",
    )

    assert patch_response.status_code == 400
    assert second_status_response.status_code == 400
