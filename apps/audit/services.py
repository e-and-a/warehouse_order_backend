from typing import Any

from django.db.models import Model

from apps.audit.constants import AuditAction
from apps.audit.models import AuditLog


def log_action(user: Any, action: AuditAction | str, instance: Model | None = None, entity: str | None = None, entity_id: Any = None) -> AuditLog:
    if instance is not None:
        entity = instance.__class__.__name__
        entity_id = instance.pk
    if entity is None or entity_id is None:
        raise ValueError("Either instance or entity/entity_id must be provided.")
    actor = user if getattr(user, "is_authenticated", False) else None
    return AuditLog.objects.create(
        user=actor,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
    )
