from rest_framework.exceptions import PermissionDenied
from rest_framework.viewsets import ModelViewSet

from apps.audit.constants import AuditAction
from apps.audit.services import log_action
from apps.common.viewsets import ProtectedDestroyMixin
from apps.users.constants import UserRole
from apps.users.permissions import IsAdminManagerOrWorkerReadOnly, IsStockRolePermission
from apps.warehouse.models import StockItem, Warehouse
from apps.warehouse.serializers import StockItemSerializer, WarehouseSerializer
from apps.warehouse.services import update_stock_item


class WarehouseViewSet(ProtectedDestroyMixin, ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAdminManagerOrWorkerReadOnly]
    protected_error_message = "Cannot delete this warehouse because it is linked to existing stock records."

    def perform_create(self, serializer):
        warehouse = serializer.save()
        log_action(self.request.user, AuditAction.CREATE, warehouse)

    def perform_update(self, serializer):
        warehouse = serializer.save()
        log_action(self.request.user, AuditAction.UPDATE, warehouse)

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditAction.DELETE, instance)
        instance.delete()


class StockItemViewSet(ModelViewSet):
    queryset = StockItem.objects.select_related("product", "warehouse").all()
    serializer_class = StockItemSerializer
    permission_classes = [IsStockRolePermission]

    def perform_create(self, serializer):
        stock_item = serializer.save()
        log_action(self.request.user, AuditAction.CREATE, stock_item)

    def perform_update(self, serializer):
        if (
            self.request.user.role == UserRole.WAREHOUSE_WORKER
            and {"product", "warehouse"} & set(serializer.validated_data)
        ):
            raise PermissionDenied("Warehouse workers can only change stock quantities.")
        updated = update_stock_item(serializer.instance, serializer.validated_data, self.request.user)
        serializer.instance = updated

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditAction.DELETE, instance)
        instance.delete()
