from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Category, Product
from apps.orders.constants import OrderStatus
from apps.orders.models import Customer, Order
from apps.orders.services import change_order_status, create_order
from apps.users.constants import UserRole
from apps.warehouse.models import StockItem, Warehouse


class Command(BaseCommand):
    help = "Create demo users, catalog, stock, customers and orders."

    def handle(self, *args, **options):
        with transaction.atomic():
            User = get_user_model()
            admin = self._upsert_user(
                User,
                email="admin@example.com",
                password="Admin123!",
                role=UserRole.ADMIN,
                is_staff=True,
                is_superuser=True,
            )
            manager = self._upsert_user(
                User,
                email="manager@example.com",
                password="Manager123!",
                role=UserRole.MANAGER,
                is_staff=False,
                is_superuser=False,
            )
            self._upsert_user(
                User,
                email="worker@example.com",
                password="Worker123!",
                role=UserRole.WAREHOUSE_WORKER,
                is_staff=False,
                is_superuser=False,
            )

            electronics, _ = Category.objects.get_or_create(
                name="Electronics",
                defaults={"description": "Devices and accessories."},
            )
            office, _ = Category.objects.get_or_create(
                name="Office",
                defaults={"description": "Office supplies."},
            )

            laptop, _ = Product.objects.get_or_create(
                sku="LAP-100",
                defaults={
                    "name": "Laptop Pro 14",
                    "description": "Portable workstation.",
                    "price": Decimal("1500.00"),
                    "category": electronics,
                },
            )
            scanner, _ = Product.objects.get_or_create(
                sku="SCN-200",
                defaults={
                    "name": "Barcode Scanner",
                    "description": "USB barcode scanner.",
                    "price": Decimal("120.00"),
                    "category": electronics,
                },
            )
            paper, _ = Product.objects.get_or_create(
                sku="PPR-500",
                defaults={
                    "name": "Printer Paper",
                    "description": "A4 paper pack.",
                    "price": Decimal("6.50"),
                    "category": office,
                },
            )

            north, _ = Warehouse.objects.get_or_create(
                name="North Warehouse",
                defaults={"address": "North industrial area"},
            )
            south, _ = Warehouse.objects.get_or_create(
                name="South Warehouse",
                defaults={"address": "South logistics park"},
            )

            self._upsert_stock(laptop, north, 20, 0)
            self._upsert_stock(scanner, north, 50, 0)
            self._upsert_stock(paper, south, 300, 0)
            self._upsert_stock(laptop, south, 10, 0)

            customer_a, _ = Customer.objects.get_or_create(
                email="client-a@example.com",
                defaults={
                    "name": "Client A",
                    "phone": "+10000000001",
                    "address": "1 Market Street",
                },
            )
            customer_b, _ = Customer.objects.get_or_create(
                email="client-b@example.com",
                defaults={
                    "name": "Client B",
                    "phone": "+10000000002",
                    "address": "2 Commerce Avenue",
                },
            )

            if not Order.objects.exists():
                create_order(
                    customer=customer_a,
                    items=[{"product": laptop, "quantity": 2, "price": laptop.price}],
                    created_by=manager,
                )
                reserved = create_order(
                    customer=customer_b,
                    items=[{"product": scanner, "quantity": 5, "price": scanner.price}],
                    created_by=manager,
                )
                change_order_status(reserved, OrderStatus.RESERVED, manager)

        self.stdout.write(self.style.SUCCESS("Seed data created."))

    def _upsert_user(self, User, email: str, password: str, role: str, **extra):
        user, _created = User.objects.get_or_create(email=email, defaults={"role": role, **extra})
        user.set_password(password)
        user.role = role
        for field, value in extra.items():
            setattr(user, field, value)
        user.is_active = True
        user.save()
        return user

    def _upsert_stock(self, product: Product, warehouse: Warehouse, quantity: int, reserved_quantity: int) -> None:
        StockItem.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            defaults={"quantity": quantity, "reserved_quantity": reserved_quantity},
        )
