import pytest
from django.contrib.auth.models import AnonymousUser

from apps.audit.constants import AuditAction
from apps.audit.models import AuditLog
from apps.audit.services import log_action


pytestmark = pytest.mark.django_db


def test_audit_log_access_admin_only(authenticated_client, admin_user, manager_user):
    log = log_action(admin_user, AuditAction.CREATE, entity="Manual", entity_id=1)

    admin_client = authenticated_client(admin_user)
    admin_list_response = admin_client.get("/api/audit-log/")
    admin_detail_response = admin_client.get(f"/api/audit-log/{log.id}/")

    manager_client = authenticated_client(manager_user)
    manager_response = manager_client.get("/api/audit-log/")

    assert admin_list_response.status_code == 200
    assert admin_detail_response.status_code == 200
    assert admin_detail_response.data["user_email"] == admin_user.email
    assert manager_response.status_code == 403
    assert str(log) == f"{AuditAction.CREATE} Manual#1"


def test_log_action_accepts_entity_fields_and_anonymous_user(admin_user):
    log = log_action(AnonymousUser(), AuditAction.UPDATE, entity="Manual", entity_id=7)

    assert log.user is None
    assert log.entity == "Manual"
    assert log.entity_id == "7"


def test_log_action_requires_instance_or_entity_fields():
    with pytest.raises(ValueError, match="Either instance or entity/entity_id"):
        log_action(None, AuditAction.CREATE)


def test_audit_log_created_by_model_instance(admin_user, product):
    log = log_action(admin_user, AuditAction.DELETE, product)

    assert AuditLog.objects.filter(pk=log.pk, entity="Product", entity_id=str(product.pk)).exists()
