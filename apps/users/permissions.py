from collections.abc import Iterable

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.users.constants import UserRole


def user_has_role(user, roles: Iterable[str]) -> bool:
    return bool(user and user.is_authenticated and (user.is_superuser or user.role in roles))


class IsAdminRole(BasePermission):
    def has_permission(self, request, view) -> bool:
        return user_has_role(request.user, [UserRole.ADMIN])


class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view) -> bool:
        return user_has_role(request.user, [UserRole.ADMIN, UserRole.MANAGER])


class IsAdminManagerOrWorkerReadOnly(BasePermission):
    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return user_has_role(
                request.user,
                [UserRole.ADMIN, UserRole.MANAGER, UserRole.WAREHOUSE_WORKER],
            )
        return user_has_role(request.user, [UserRole.ADMIN, UserRole.MANAGER])


class IsStockRolePermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        if not user_has_role(
            request.user,
            [UserRole.ADMIN, UserRole.MANAGER, UserRole.WAREHOUSE_WORKER],
        ):
            return False
        if request.method in SAFE_METHODS:
            return True
        if getattr(view, "action", None) in {"update", "partial_update"}:
            return user_has_role(
                request.user,
                [UserRole.ADMIN, UserRole.MANAGER, UserRole.WAREHOUSE_WORKER],
            )
        return user_has_role(request.user, [UserRole.ADMIN, UserRole.MANAGER])


class IsOrderRolePermission(BasePermission):
    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return user_has_role(
                request.user,
                [UserRole.ADMIN, UserRole.MANAGER, UserRole.WAREHOUSE_WORKER],
            )
        return user_has_role(request.user, [UserRole.ADMIN, UserRole.MANAGER])
