"""应用单元测试，作为流水线中构建镜像前的质量门禁。"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def client():
    app = create_app(Settings(app_name="test-app", version="1.2.3", host="127.0.0.1", port=8000, environment="test"))
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_index_returns_service_metadata(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_json()
    assert body["service"] == "test-app"
    assert body["version"] == "1.2.3"
    assert body["environment"] == "test"


def test_healthz_is_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["version"] == "1.2.3"
    assert body["uptime_seconds"] >= 0


def test_info_reports_architecture(client):
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    body = response.get_json()
    # 该字段用于验证多架构镜像：amd64 镜像返回 x86_64，arm64 镜像返回 aarch64
    assert body["architecture"]
    assert body["python_version"].startswith("3.")


def test_echo_roundtrip(client):
    response = client.post("/api/v1/echo", json={"radar": "Z9210", "site": "Z9210"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["echo"] == {"radar": "Z9210", "site": "Z9210"}
    assert body["keys"] == ["radar", "site"]


def test_echo_rejects_non_object_body(client):
    response = client.post("/api/v1/echo", json=["not", "an", "object"])
    assert response.status_code == 400
    assert "error" in response.get_json()
