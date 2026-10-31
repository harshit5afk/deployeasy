from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_version_has_version_and_sha():
    body = client.get("/version").json()
    assert "version" in body and "git_sha" in body


def test_metrics_are_numbers():
    body = client.get("/metrics").json()
    assert isinstance(body["process_uptime_seconds"], (int, float))
    assert isinstance(body["requests_since_process_start"], int)


def test_root_message():
    assert "DeployEasy" in client.get("/").json()["message"]


def test_runs_endpoint_never_crashes_without_config():
    r = client.get("/api/runs")
    assert r.status_code == 200 and "runs" in r.json()


def test_dashboard_page_served():
    r = client.get("/dashboard")
    assert r.status_code == 200 and "DeployEasy" in r.text
