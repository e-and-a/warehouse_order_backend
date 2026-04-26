from django.db import models


class OrderStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    RESERVED = "RESERVED", "Reserved"
    SHIPPED = "SHIPPED", "Shipped"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
