import pytest
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditLog
from apps.catalog.models import Category, Product
from apps.catalog.serializers import ProductSerializer
from apps.users.constants import UserRole


pytestmark = pytest.mark.django_db


def test_category_crud_permissions_and_audit(authenticated_client, manager_user, worker_user):
    manager_client = authenticated_client(manager_user)

    create_response = manager_client.post(
        "/api/categories/",
        {"name": "Office", "description": "Office supplies"},
        format="json",
    )
    category_id = create_response.data["id"]
    update_response = manager_client.patch(
        f"/api/categories/{category_id}/",
        {"description": "Updated"},
        format="json",
    )
    list_response = manager_client.get("/api/categories/")
    delete_response = manager_client.delete(f"/api/categories/{category_id}/")

    worker_client = authenticated_client(worker_user)
    worker_create_response = worker_client.post(
        "/api/categories/",
        {"name": "Blocked", "description": "No access"},
        format="json",
    )

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert list_response.status_code == 200
    assert delete_response.status_code == 204
    assert worker_create_response.status_code == 403
    assert AuditLog.objects.filter(entity="Category", action="DELETE").exists()


def test_product_crud_permissions_validation_and_str(authenticated_client, manager_user, worker_user, category):
    manager_client = authenticated_client(manager_user)

    create_response = manager_client.post(
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
    product_id = create_response.data["id"]
    product = Product.objects.get(pk=product_id)

    update_response = manager_client.patch(
        f"/api/products/{product_id}/",
        {"price": "1400.00"},
        format="json",
    )
    list_response = manager_client.get("/api/products/")
    delete_response = manager_client.delete(f"/api/products/{product_id}/")

    worker_client = authenticated_client(worker_user)
    worker_list_response = worker_client.get("/api/products/")
    worker_create_response = worker_client.post(
        "/api/products/",
        {
            "name": "Blocked",
            "sku": "WRK-100",
            "description": "No access",
            "price": "1.00",
            "category": category.id,
            "is_active": True,
        },
        format="json",
    )
    invalid_price_response = manager_client.post(
        "/api/products/",
        {
            "name": "Invalid",
            "sku": "BAD-PRICE",
            "description": "",
            "price": "-1.00",
            "category": category.id,
            "is_active": True,
        },
        format="json",
    )

    assert create_response.status_code == 201
    assert str(category) == "Electronics"
    assert str(product) == "Laptop (LAP-100)"
    assert update_response.status_code == 200
    assert list_response.status_code == 200
    assert worker_list_response.status_code == 200
    assert worker_create_response.status_code == 403
    assert invalid_price_response.status_code == 400
    assert "price" in invalid_price_response.data
    assert delete_response.status_code == 204
    assert AuditLog.objects.filter(entity="Product", action="DELETE").exists()


def test_product_create_requires_required_fields(authenticated_client, manager_user):
    client = authenticated_client(manager_user)

    response = client.post("/api/products/", {"name": ""}, format="json")

    assert response.status_code == 400
    assert "sku" in response.data
    assert "category" in response.data


def test_product_serializer_custom_price_validation():
    serializer = ProductSerializer()

    with pytest.raises(ValidationError, match="Price must be greater than or equal to 0"):
        serializer.validate_price(-1)


def test_manager_can_create_product_from_existing_fixture(authenticated_client, manager_user, category):
    client = authenticated_client(manager_user)

    response = client.post(
        "/api/products/",
        {
            "name": "Scanner",
            "sku": "SCN-NEW",
            "description": "Scanner",
            "price": "99.90",
            "category": category.id,
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["sku"] == "SCN-NEW"
    assert Category.objects.filter(products__sku="SCN-NEW").exists()
