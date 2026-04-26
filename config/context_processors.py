from typing import Any

from apps.users.constants import UserRole


def role_flags(request: Any) -> dict[str, bool]:
    user = getattr(request, "user", None)
    is_authenticated = bool(user and user.is_authenticated)
    role = getattr(user, "role", None) if is_authenticated else None
    is_admin = bool(is_authenticated and role == UserRole.ADMIN)
    is_manager = bool(is_authenticated and role == UserRole.MANAGER)
    is_worker = bool(is_authenticated and role == UserRole.WAREHOUSE_WORKER)
    return {
        "is_admin_role": is_admin,
        "is_manager_role": is_manager,
        "is_worker_role": is_worker,
        "can_create_products": is_admin or is_manager,
        "can_create_orders": is_admin or is_manager,
    }
