from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.audit.constants import AuditAction
from apps.audit.services import log_action
from apps.common.viewsets import ProtectedDestroyMixin
from apps.orders.models import Customer, Order
from apps.orders.serializers import CustomerSerializer, OrderSerializer, OrderStatusSerializer
from apps.orders.services import change_order_status, create_order, delete_order, update_order
from apps.users.permissions import IsAdminOrManager, IsOrderRolePermission


class CustomerViewSet(ProtectedDestroyMixin, ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminOrManager]
    protected_error_message = "Cannot delete this customer because it is linked to existing orders."

    def perform_create(self, serializer):
        customer = serializer.save()
        log_action(self.request.user, AuditAction.CREATE, customer)

    def perform_update(self, serializer):
        customer = serializer.save()
        log_action(self.request.user, AuditAction.UPDATE, customer)

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditAction.DELETE, instance)
        instance.delete()


class OrderViewSet(ModelViewSet):
    queryset = Order.objects.select_related("customer", "created_by").prefetch_related("items__product")
    serializer_class = OrderSerializer
    permission_classes = [IsOrderRolePermission]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = create_order(
            customer=serializer.validated_data["customer"],
            items=serializer.validated_data["items"],
            created_by=request.user,
        )
        output = self.get_serializer(order)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        order = update_order(instance, serializer.validated_data, request.user)
        return Response(self.get_serializer(order).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        delete_order(self.get_object(), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = change_order_status(
            self.get_object(),
            serializer.validated_data["status"],
            request.user,
        )
        return Response(self.get_serializer(order).data)
