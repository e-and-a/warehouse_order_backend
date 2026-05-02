from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product
from apps.orders.models import Customer
from apps.users.constants import UserRole
from apps.warehouse.models import StockItem, Warehouse


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def testserver_allowed_host(settings):
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]


@pytest.fixture
def authenticated_client():
    def _authenticate(user):
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        return api_client

    return _authenticate


@pytest.fixture
def admin_user(db):
    User = get_user_model()
    return User.objects.create_user(
        email="admin@example.com",
        password="Admin123!",
        role=UserRole.ADMIN,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def manager_user(db):
    User = get_user_model()
    return User.objects.create_user(
        email="manager@example.com",
        password="Manager123!",
        role=UserRole.MANAGER,
    )


@pytest.fixture
def worker_user(db):
    User = get_user_model()
    return User.objects.create_user(
        email="worker@example.com",
        password="Worker123!",
        role=UserRole.WAREHOUSE_WORKER,
    )


@pytest.fixture
def unknown_role_user(db):
    User = get_user_model()
    return User.objects.create_user(
        email="unknown@example.com",
        password="Unknown123!",
        role="UNKNOWN",
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Electronics", description="Devices")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Barcode Scanner",
        sku="SCN-100",
        description="USB scanner",
        price=Decimal("99.90"),
        category=category,
    )


@pytest.fixture
def product_factory(category):
    counter = {"value": 0}

    def _create(**overrides):
        counter["value"] += 1
        data = {
            "name": f"Product {counter['value']}",
            "sku": f"SKU-{counter['value']:03d}",
            "description": "Factory product",
            "price": Decimal("10.00"),
            "category": category,
            "is_active": True,
        }
        data.update(overrides)
        return Product.objects.create(**data)

    return _create


@pytest.fixture
def warehouse(db):
    return Warehouse.objects.create(name="Main Warehouse", address="Main street")


@pytest.fixture
def warehouse_factory(db):
    counter = {"value": 0}

    def _create(**overrides):
        counter["value"] += 1
        data = {
            "name": f"Warehouse {counter['value']}",
            "address": f"{counter['value']} Storage Avenue",
        }
        data.update(overrides)
        return Warehouse.objects.create(**data)

    return _create


@pytest.fixture
def stock_item(product, warehouse):
    return StockItem.objects.create(product=product, warehouse=warehouse, quantity=10, reserved_quantity=0)


@pytest.fixture
def stock_factory(warehouse):
    def _create(product, quantity=10, reserved_quantity=0, warehouse_override=None):
        return StockItem.objects.create(
            product=product,
            warehouse=warehouse_override or warehouse,
            quantity=quantity,
            reserved_quantity=reserved_quantity,
        )

    return _create


@pytest.fixture
def customer(db):
    return Customer.objects.create(
        name="Client A",
        email="client@example.com",
        phone="+100000000",
        address="1 Market Street",
    )


@pytest.fixture
def customer_factory(db):
    counter = {"value": 0}

    def _create(**overrides):
        counter["value"] += 1
        data = {
            "name": f"Client {counter['value']}",
            "email": f"client-{counter['value']}@example.com",
            "phone": f"+1000000000{counter['value']}",
            "address": f"{counter['value']} Market Street",
        }
        data.update(overrides)
        return Customer.objects.create(**data)

    return _create
