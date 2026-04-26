from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "user", "user_email", "action", "entity", "entity_id", "created_at"]
        read_only_fields = fields
