import pytest
from django.contrib.auth import get_user_model

from apps.audit.models import AuditLog
from apps.catalog.models import Product
from apps.orders.models import Order
from apps.users.constants import UserRole


pytestmark = pytest.mark.django_db


def _login(client, user, password):
    return client.post("/login/", {"username": user.email, "password": password})


@pytest.mark.parametrize(
    ("fixture_name", "password"),
    [
        ("admin_user", "Admin123!"),
        ("manager_user", "Manager123!"),
        ("worker_user", "Worker123!"),
    ],
)
def test_template_pages_access_by_allowed_roles(request, client, fixture_name, password, product, stock_item, customer):
    user = request.getfixturevalue(fixture_name)

    login_response = _login(client, user, password)

    assert login_response.status_code == 302
    for path in ["/dashboard/", "/products/", "/stock/", "/orders/"]:
        response = client.get(path)
        assert response.status_code == 200


def test_template_pages_redirect_anonymous_users(client):
    response = client.get("/dashboard/")

    assert response.status_code == 302
    assert response["Location"].startswith("/login/")


def test_template_pages_forbid_unknown_role(client, unknown_role_user):
    client.force_login(unknown_role_user)

    response = client.get("/dashboard/")

    assert response.status_code == 403


def test_products_template_create_allowed_for_manager(client, manager_user, category):
    client.force_login(manager_user)

    response = client.post(
        "/products/",
        {
            "name": "Template Product",
            "sku": "TPL-100",
            "description": "Created from page",
            "price": "12.50",
            "category": category.id,
            "is_active": "on",
        },
    )

    assert response.status_code == 302
    assert Product.objects.filter(sku="TPL-100").exists()
    assert AuditLog.objects.filter(entity="Product", action="CREATE").exists()


def test_products_template_create_forbidden_for_worker(client, worker_user, category):
    client.force_login(worker_user)

    response = client.post(
        "/products/",
        {
            "name": "Blocked Template Product",
            "sku": "TPL-403",
            "description": "No access",
            "price": "12.50",
            "category": category.id,
            "is_active": "on",
        },
    )

    assert response.status_code == 403
    assert not Product.objects.filter(sku="TPL-403").exists()


def test_products_template_invalid_form_does_not_create_product(client, manager_user, category):
    client.force_login(manager_user)

    response = client.post(
        "/products/",
        {
            "name": "",
            "sku": "",
            "description": "Invalid",
            "price": "-1.00",
            "category": category.id,
            "is_active": "on",
        },
    )

    assert response.status_code == 200
    assert not Product.objects.filter(description="Invalid").exists()


def test_orders_template_create_allowed_for_manager(client, manager_user, stock_item, customer, product):
    client.force_login(manager_user)

    response = client.post(
        "/orders/",
        {
            "customer": customer.id,
            "product": product.id,
            "quantity": 2,
        },
    )

    assert response.status_code == 302
    assert Order.objects.filter(customer=customer, created_by=manager_user).exists()


def test_orders_template_create_forbidden_for_worker(client, worker_user, stock_item, customer, product):
    client.force_login(worker_user)

    response = client.post(
        "/orders/",
        {
            "customer": customer.id,
            "product": product.id,
            "quantity": 1,
        },
    )

    assert response.status_code == 403


def test_orders_template_shows_validation_error(client, manager_user, stock_item, customer, product):
    client.force_login(manager_user)

    response = client.post(
        "/orders/",
        {
            "customer": customer.id,
            "product": product.id,
            "quantity": stock_item.quantity + 1,
        },
    )

    assert response.status_code == 200
    assert b"Not enough stock" in response.content


def test_worker_products_page_is_read_only(client, worker_user, product):
    client.force_login(worker_user)

    response = client.get("/products/")

    assert response.status_code == 200
    assert b"Create product" not in response.content


def test_orders_page_hides_create_form_for_worker(client, worker_user, stock_item, customer, product):
    client.force_login(worker_user)

    response = client.get("/orders/")

    assert response.status_code == 200
    assert b"Create order" not in response.content
