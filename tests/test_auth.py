import pytest


pytestmark = pytest.mark.django_db


def test_user_login_returns_jwt(api_client, manager_user):
    response = api_client.post(
        "/api/auth/token/",
        {"email": "manager@example.com", "password": "Manager123!"},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


def test_token_refresh_returns_new_access_token(api_client, manager_user):
    login_response = api_client.post(
        "/api/auth/token/",
        {"email": "manager@example.com", "password": "Manager123!"},
        format="json",
    )

    refresh_response = api_client.post(
        "/api/auth/token/refresh/",
        {"refresh": login_response.data["refresh"]},
        format="json",
    )

    assert refresh_response.status_code == 200
    assert "access" in refresh_response.data


def test_invalid_login_returns_401(api_client, manager_user):
    response = api_client.post(
        "/api/auth/token/",
        {"email": "manager@example.com", "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401
    assert "detail" in response.data


def test_api_without_jwt_returns_401(api_client):
    response = api_client.get("/api/products/")

    assert response.status_code == 401


def test_stock_api_without_jwt_returns_401(api_client):
    response = api_client.get("/api/stock/")

    assert response.status_code == 401
