import pytest
from django.contrib.auth import get_user_model

from apps.audit.models import AuditLog
from apps.users.constants import UserRole
from apps.users.permissions import user_has_role


pytestmark = pytest.mark.django_db


def test_me_endpoint_returns_current_user(authenticated_client, manager_user):
    client = authenticated_client(manager_user)

    response = client.get("/api/users/me/")

    assert response.status_code == 200
    assert response.data["email"] == manager_user.email
    assert response.data["role"] == UserRole.MANAGER


def test_admin_can_crud_users(authenticated_client, admin_user):
    client = authenticated_client(admin_user)

    create_response = client.post(
        "/api/users/",
        {
            "email": "new-user@example.com",
            "password": "NewUser123!",
            "first_name": "New",
            "last_name": "User",
            "role": UserRole.MANAGER,
            "is_active": True,
            "is_staff": False,
        },
        format="json",
    )
    user_id = create_response.data["id"]

    detail_response = client.get(f"/api/users/{user_id}/")
    patch_response = client.patch(
        f"/api/users/{user_id}/",
        {"first_name": "Updated", "password": "Updated123!"},
        format="json",
    )
    delete_response = client.delete(f"/api/users/{user_id}/")

    assert create_response.status_code == 201
    assert detail_response.status_code == 200
    assert patch_response.status_code == 200
    assert delete_response.status_code == 204
    assert AuditLog.objects.filter(entity="User", action="DELETE").exists()


def test_non_admin_cannot_manage_users(authenticated_client, manager_user):
    client = authenticated_client(manager_user)

    response = client.get("/api/users/")

    assert response.status_code == 403


def test_invalid_role_returns_400(authenticated_client, admin_user):
    client = authenticated_client(admin_user)

    response = client.post(
        "/api/users/",
        {
            "email": "bad-role@example.com",
            "password": "BadRole123!",
            "role": "INVALID",
            "is_active": True,
            "is_staff": False,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "role" in response.data


def test_user_manager_defaults_and_validation():
    User = get_user_model()

    user = User.objects.create_user("default-role@example.com", "Default123!")

    assert str(user) == "default-role@example.com"
    assert user.role == UserRole.WAREHOUSE_WORKER
    assert user_has_role(user, [UserRole.WAREHOUSE_WORKER])
    assert not user_has_role(None, [UserRole.ADMIN])


def test_user_manager_requires_email():
    User = get_user_model()

    with pytest.raises(ValueError, match="Email is required"):
        User.objects.create_user("", "Password123!")


def test_superuser_validation_errors():
    User = get_user_model()

    superuser = User.objects.create_superuser("root@example.com", "Root123!")

    assert superuser.is_staff is True
    assert superuser.is_superuser is True
    assert superuser.role == UserRole.ADMIN

    with pytest.raises(ValueError, match="is_staff=True"):
        User.objects.create_superuser("bad-staff@example.com", "Password123!", is_staff=False)
    with pytest.raises(ValueError, match="is_superuser=True"):
        User.objects.create_superuser("bad-super@example.com", "Password123!", is_superuser=False)
    with pytest.raises(ValueError, match="ADMIN role"):
        User.objects.create_superuser("bad-role-super@example.com", "Password123!", role=UserRole.MANAGER)
