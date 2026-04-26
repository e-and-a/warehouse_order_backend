from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.audit.constants import AuditAction
from apps.audit.services import log_action
from apps.users.models import User
from apps.users.permissions import IsAdminRole
from apps.users.serializers import CurrentUserSerializer, UserSerializer


class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by("email")
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    lookup_value_regex = r"\d+"

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="me",
    )
    def me(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)

    def perform_create(self, serializer):
        user = serializer.save()
        log_action(self.request.user, AuditAction.CREATE, user)

    def perform_update(self, serializer):
        user = serializer.save()
        log_action(self.request.user, AuditAction.UPDATE, user)

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditAction.DELETE, instance)
        instance.delete()
