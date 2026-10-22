
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.config import settings


def create_proxy_test_app():
    application = FastAPI()

    @application.get("/client-ip")
    def get_client_ip(request: Request):
        return {"ip": request.client.host}

    return ProxyHeadersMiddleware(
        application,
        trusted_hosts=["127.0.0.1"],
    )


def test_untrusted_proxy_headers_are_ignored():
    application = create_proxy_test_app()

    with TestClient(
        application,
        client=("198.51.100.20", 50000),
    ) as test_client:
        response = test_client.get(
            "/client-ip",
            headers={
                "X-Forwarded-For": "203.0.113.50",
            },
        )

    assert response.status_code == 200
    assert response.json()["ip"] == "198.51.100.20"


def test_trusted_proxy_headers_are_accepted():
    application = create_proxy_test_app()

    with TestClient(
        application,
        client=("127.0.0.1", 50000),
    ) as test_client:
        response = test_client.get(
            "/client-ip",
            headers={
                "X-Forwarded-For": "203.0.113.50",
            },
        )

    assert response.status_code == 200
    assert response.json()["ip"] == "203.0.113.50"


def test_forged_ip_cannot_bypass_login_limit(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "login_ip_max_attempts",
        1,
    )

    first_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "spoof-a@vulnflow.dev",
            "password": "IncorrectPassword2026!",
        },
        headers={
            "X-Forwarded-For": "203.0.113.10",
            "X-Real-IP": "203.0.113.10",
        },
    )

    assert first_response.status_code == 401

    blocked_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "spoof-b@vulnflow.dev",
            "password": "IncorrectPassword2026!",
        },
        headers={
            "X-Forwarded-For": "203.0.113.20",
            "X-Real-IP": "203.0.113.20",
        },
    )

    assert blocked_response.status_code == 429
