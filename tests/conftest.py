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
def warehouse(db):
    return Warehouse.objects.create(name="Main Warehouse", address="Main street")


@pytest.fixture
def stock_item(product, warehouse):
    return StockItem.objects.create(product=product, warehouse=warehouse, quantity=10, reserved_quantity=0)


@pytest.fixture
def customer(db):
    return Customer.objects.create(
        name="Client A",
        email="client@example.com",
        phone="+100000000",
        address="1 Market Street",
    )
