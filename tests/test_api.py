from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app

init_db()
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


def test_list_projects():
    r = client.get("/api/projects")
    assert r.status_code == 200
    projects = r.json()
    assert isinstance(projects, list)
    assert len(projects) >= 1
    assert "repo_name" in projects[0]


def test_create_project_and_get():
    new_repo = "test-org/microservice-worker"
    payload = {
        "name": "Microservice Worker",
        "repo_name": new_repo,
        "branch": "main",
        "service_url": "https://worker.onrender.com",
        "deploy_hook_url": "https://api.render.com/deploy/srv-worker",
    }
    r = client.post("/api/projects", json=payload)
    if r.status_code == 400:
        # Already exists from previous run
        pass
    else:
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Microservice Worker"
        project_id = data["id"]

        r_get = client.get(f"/api/projects/{project_id}")
        assert r_get.status_code == 200
        assert r_get.json()["repo_name"] == new_repo


def test_get_project_deployments():
    r_projects = client.get("/api/projects")
    project_id = r_projects.json()[0]["id"]
    r_deps = client.get(f"/api/projects/{project_id}/deployments")
    assert r_deps.status_code == 200
    deps = r_deps.json()
    assert isinstance(deps, list)
    assert len(deps) >= 1
    assert "commit_sha" in deps[0]


def test_trigger_deployment_and_rollback():
    r_projects = client.get("/api/projects")
    project_id = r_projects.json()[0]["id"]

    # Trigger a deployment
    trigger_payload = {
        "project_id": project_id,
        "commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        "commit_message": "test: trigger smoke test release",
        "branch": "main",
    }
    r_trig = client.post("/api/deployments/trigger", json=trigger_payload)
    assert r_trig.status_code == 201
    assert r_trig.json()["status"] == "success"

    # Trigger a rollback
    rollback_payload = {
        "project_id": project_id,
        "target_sha": "ef1482f7c0099ad4bb5e58db5f32cf8e51928014",
        "reason": "Test rollback from automated suite",
    }
    r_roll = client.post("/api/deployments/rollback", json=rollback_payload)
    assert r_roll.status_code == 200
    data = r_roll.json()
    assert data["status"] == "rolled_back"
    assert "ef1482f" in data["commit_sha"]


def test_health_check_probe_and_history():
    r_projects = client.get("/api/projects")
    project_id = r_projects.json()[0]["id"]

    # Run on-demand check
    r_check = client.post(f"/api/projects/{project_id}/check-health")
    assert r_check.status_code == 200
    assert r_check.json()["endpoint"] == "/health"

    # Get history
    r_hist = client.get(f"/api/projects/{project_id}/health-history")
    assert r_hist.status_code == 200
    hist = r_hist.json()
    assert isinstance(hist, list)
    assert len(hist) >= 1


def test_security_scans():
    r_projects = client.get("/api/projects")
    project_id = r_projects.json()[0]["id"]
    r_sec = client.get(f"/api/projects/{project_id}/security")
    assert r_sec.status_code == 200
    scans = r_sec.json()
    assert isinstance(scans, list)
    assert len(scans) >= 1
    assert scans[0]["scan_type"] in ("trivy", "gitleaks")


def test_system_overview():
    r = client.get("/api/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["total_projects"] >= 1
    assert data["successful_deployments"] >= 1
    assert "fleet_health" in data
    assert "recent_deployments" in data


def test_analyze_logs_endpoint():
    # Test 1: Test failure
    log_sample = """
    ============================= test session starts =============================
    FAILED tests/test_core.py::test_calculation - AssertionError: 42 != 43
    """
    r = client.post("/api/analyze-logs", json={"logs": log_sample})
    assert r.status_code == 200
    res = r.json()
    assert res["error_category"] == "test_failure"
    assert res["severity"] == "HIGH"
    assert "pytest" in res["suggested_fix"].lower()

    # Test 2: Trivy vulnerability gate
    trivy_sample = "2026-11-05T12:00:00Z FATAL Trivy scan detected CRITICAL CVE-2024-37891 exit code: 1"
    r2 = client.post("/api/analyze-logs", json={"logs": trivy_sample})
    assert r2.status_code == 200
    res2 = r2.json()
    assert res2["error_category"] == "security_vulnerability"
    assert res2["severity"] == "CRITICAL"


def test_deployment_log_analysis_record():
    r_projects = client.get("/api/projects")
    project_id = r_projects.json()[0]["id"]
    r_deps = client.get(f"/api/projects/{project_id}/deployments")
    dep_id = r_deps.json()[0]["id"]

    r_analysis = client.get(f"/api/deployments/{dep_id}/analysis")
    assert r_analysis.status_code == 200
    assert "error_category" in r_analysis.json()


def test_validate_env_endpoint():
    # Valid payload
    valid_env = {
        "PORT": "8080",
        "APP_VERSION": "1.2.0",
        "DATABASE_URL": "postgresql://user:pass@db:5432/prod",
        "SERVICE_URL": "https://service.onrender.com",
        "RENDER_DEPLOY_HOOK_URL": "https://api.render.com/deploy/srv-1234567890",
        "GITHUB_REPO": "my-team/api-server",
        "SECRET_KEY": "supersecretkey12345678",
    }
    r = client.post("/api/validate-env", json={"env_vars": valid_env})
    assert r.status_code == 200
    res = r.json()
    assert res["is_valid"] is True
    assert len(res["errors"]) == 0
    # Confirm secret masking
    assert "..." in res["sanitized_variables"]["SECRET_KEY"]

    # Invalid payload
    invalid_env = {
        "PORT": "not-a-port",
        "SERVICE_URL": "ftp://bad-url",
        "GITHUB_REPO": "invalid_repo_name_no_slash",
    }
    r_inv = client.post("/api/validate-env", json={"env_vars": invalid_env})
    assert r_inv.status_code == 200
    res_inv = r_inv.json()
    assert res_inv["is_valid"] is False
    assert len(res_inv["errors"]) >= 2


def test_project_readiness_score():
    r_projects = client.get("/api/projects")
    project_id = r_projects.json()[0]["id"]

    r_readiness = client.get(f"/api/projects/{project_id}/readiness")
    assert r_readiness.status_code == 200
    data = r_readiness.json()
    assert isinstance(data["readiness_score"], int)
    assert 0 <= data["readiness_score"] <= 100
    assert "confidence_tier" in data
    assert len(data["checklist"]) >= 4


def test_landing_page_served():
    r = client.get("/", headers={"accept": "text/html"})
    assert r.status_code == 200
    assert "DeployEasy" in r.text
    assert "Confidence" in r.text


def test_auth_pages_served():
    r_login = client.get("/login")
    assert r_login.status_code == 200
    assert "Sign In" in r_login.text or "Welcome" in r_login.text

    r_signup = client.get("/signup")
    assert r_signup.status_code == 200
    assert "DeployEasy" in r_signup.text


def test_auth_api_endpoints():
    r_demo = client.post("/api/auth/demo-login")
    assert r_demo.status_code == 200
    assert r_demo.json()["status"] == "authenticated"
    assert "token" in r_demo.json()

    r_me = client.get("/api/auth/me")
    assert r_me.status_code == 200
    assert r_me.json()["authenticated"] is True
    assert r_me.json()["username"] == "demo-developer"


def test_deployment_diff_endpoint():
    r_projects = client.get("/api/projects")
    project_id = r_projects.json()[0]["id"]
    r_deps = client.get(f"/api/projects/{project_id}/deployments")
    dep_id = r_deps.json()[0]["id"]

    r_diff = client.get(f"/api/deployments/{dep_id}/diff")
    assert r_diff.status_code == 200
    data = r_diff.json()
    assert "current_sha" in data
    assert "previous_sha" in data
    assert "diff_summary" in data


def test_project_costs_endpoint():
    r_projects = client.get("/api/projects")
    project_id = r_projects.json()[0]["id"]

    r_costs = client.get(f"/api/projects/{project_id}/costs")
    assert r_costs.status_code == 200
    data = r_costs.json()
    assert "projected_monthly_cost_usd" in data
    assert "breakdown" in data
    assert "recommendations" in data
    assert len(data["recommendations"]) >= 1


def test_incident_generator_endpoint():
    r_projects = client.get("/api/projects")
    project_id = r_projects.json()[0]["id"]

    payload = {
        "failed_sha": "badcommit1234567890abcdef1234567890abcd",
        "rollback_sha": "ef1482f7c0099ad4bb5e58db5f32cf8e51928014",
        "symptoms": "Smoke test timed out waiting for SHA on /version",
        "log_excerpt": "Timed out waiting for badcom to go live",
    }
    r_inc = client.post(f"/api/projects/{project_id}/incidents/generate", json=payload)
    assert r_inc.status_code == 200
    inc = r_inc.json()
    assert "title" in inc
    assert "markdown_report" in inc
    assert "Incident Post-Mortem" in inc["markdown_report"]
    assert inc["failed_sha"] == "badcomm"


def test_webhook_test_endpoint():
    r_projects = client.get("/api/projects")
    project_id = r_projects.json()[0]["id"]

    # Test discord format
    payload = {
        "webhook_url": "https://discord.com/api/webhooks/test/dummy",
        "platform": "discord",
    }
    r_wh = client.post(f"/api/projects/{project_id}/webhook-test", json=payload)
    assert r_wh.status_code == 200
    data = r_wh.json()
    assert data["platform"] == "discord"
    assert "sample_payload" in data
    assert "embeds" in data["sample_payload"]
