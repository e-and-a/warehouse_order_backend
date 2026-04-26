from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    MANAGER = "MANAGER", "Manager"
    WAREHOUSE_WORKER = "WAREHOUSE_WORKER", "Warehouse worker"
