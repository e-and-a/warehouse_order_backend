from rest_framework.viewsets import ModelViewSet

from apps.audit.constants import AuditAction
from apps.audit.services import log_action
from apps.common.viewsets import ProtectedDestroyMixin
from apps.catalog.models import Category, Product
from apps.catalog.serializers import CategorySerializer, ProductSerializer
from apps.users.permissions import IsAdminManagerOrWorkerReadOnly


class CategoryViewSet(ProtectedDestroyMixin, ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminManagerOrWorkerReadOnly]
    protected_error_message = "Cannot delete this category because it is linked to existing products."

    def perform_create(self, serializer):
        category = serializer.save()
        log_action(self.request.user, AuditAction.CREATE, category)

    def perform_update(self, serializer):
        category = serializer.save()
        log_action(self.request.user, AuditAction.UPDATE, category)

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditAction.DELETE, instance)
        instance.delete()


class ProductViewSet(ProtectedDestroyMixin, ModelViewSet):
    queryset = Product.objects.select_related("category").all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminManagerOrWorkerReadOnly]
    protected_error_message = "Cannot delete this product because it is linked to stock records or order items."

    def perform_create(self, serializer):
        product = serializer.save()
        log_action(self.request.user, AuditAction.CREATE, product)

    def perform_update(self, serializer):
        product = serializer.save()
        log_action(self.request.user, AuditAction.UPDATE, product)

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditAction.DELETE, instance)
        instance.delete()
