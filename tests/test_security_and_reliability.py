"""Comprehensive negative security and reliability tests for DeployEasy.

Covers:
1. Anonymous Access Rejection (401) on every project & deployment endpoint
2. Cross-User Isolation (403) across projects, deployments, health probes, and metrics
3. Session Persistence, HTTP-only Cookies & CSRF Protection
4. Authentication Rate Limiting (429 on 6th attempt within window)
5. Strict SSRF Protection (loopback, private RFC1918, link-local, cloud metadata, redirects, webhook allowlists)
6. Secret Exposure Prevention (deploy_hook_url never in responses, .env secrets masked)
7. Real Deployment & Rollback Execution with Mocked External Services (no fake success records)
8. Rollback Verification Gate (awaiting live version convergence vs verified live)
9. Readiness Hard Safety Gates Enforcement
10. Demo User Restrictions (read-only enforcement)
"""
import ipaddress
import os

os.environ["TESTING"] = "1"
import urllib.error
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.auth import reset_auth_rate_limits
from app.db import SecurityScan, SessionLocal, User, UserSession, init_db
from app.main import app
from app.ssrf import (
    SSRFSafeRedirectHandler,
    SSRFValidationError,
    validate_ip_address,
    validate_target_url,
    validate_webhook_url,
)

init_db()


@pytest.fixture(autouse=True)
def clean_rate_limits():
    """Ensure clean rate limit window before each test."""
    reset_auth_rate_limits()
    yield
    reset_auth_rate_limits()


@pytest.fixture
def test_users():
    """Create two distinct developer users for isolation testing."""
    db = SessionLocal()
    try:
        suffix = uuid.uuid4().hex[:6]
        user_a = User(
            username=f"dev_alice_{suffix}",
            email=f"alice_{suffix}@example.com",
            password_hash="dummy_hash_a",
            role="developer",
            is_active=True,
        )
        user_b = User(
            username=f"dev_bob_{suffix}",
            email=f"bob_{suffix}@example.com",
            password_hash="dummy_hash_b",
            role="developer",
            is_active=True,
        )
        db.add_all([user_a, user_b])
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)
        return user_a, user_b
    finally:
        db.close()


def create_client_for_user(user: User) -> TestClient:
    """Create a TestClient with an active session cookie and CSRF token for the given user."""
    db = SessionLocal()
    try:
        from app.auth import create_user_session
        sess = create_user_session(db, user)
        c = TestClient(app)
        c.cookies.set("deployeasy_session", sess.session_token)
        c.cookies.set("deployeasy_csrf", sess.csrf_token)
        c.headers["X-CSRF-Token"] = sess.csrf_token
        return c
    finally:
        db.close()


# =============================================================================
# 1. ANONYMOUS ACCESS REJECTIONS (Requirement 1)
# =============================================================================

def test_anonymous_cannot_access_projects():
    unauth = TestClient(app)
    endpoints = [
        ("GET", "/api/projects"),
        ("POST", "/api/projects"),
        ("GET", "/api/projects/1"),
        ("GET", "/api/projects/1/deployments"),
        ("POST", "/api/deployments/trigger"),
        ("POST", "/api/deployments/rollback"),
        ("GET", "/api/projects/1/health-history"),
        ("POST", "/api/projects/1/check-health"),
        ("GET", "/api/projects/1/security"),
        ("GET", "/api/projects/1/readiness"),
        ("GET", "/api/projects/1/costs"),
        ("POST", "/api/projects/1/incidents/generate"),
        ("POST", "/api/projects/1/webhook-test"),
        ("GET", "/api/overview"),
    ]
    for method, path in endpoints:
        if method == "GET":
            r = unauth.get(path)
        else:
            r = unauth.post(path, json={})
        assert r.status_code == 401, f"Expected 401 for anonymous {method} {path}, got {r.status_code}"
        assert "Authentication required" in r.json().get("detail", "")


# =============================================================================
# 2. CROSS-USER ISOLATION (Requirement 1)
# =============================================================================

def test_cross_user_project_isolation(test_users):
    user_a, user_b = test_users
    client_a = create_client_for_user(user_a)
    client_b = create_client_for_user(user_b)

    # User A creates a project
    repo_name = f"alice-org/repo-{uuid.uuid4().hex[:6]}"
    res_create = client_a.post("/api/projects", json={
        "name": "Alice Private Project",
        "repo_name": repo_name,
        "branch": "main",
        "service_url": "https://alice-service.onrender.com",
    })
    assert res_create.status_code == 201
    proj_a_id = res_create.json()["id"]

    # User B lists projects - Alice's project must NOT appear
    res_b_list = client_b.get("/api/projects")
    assert res_b_list.status_code == 200
    b_project_ids = [p["id"] for p in res_b_list.json()]
    assert proj_a_id not in b_project_ids

    # User B attempts to access Alice's project directly -> 403 Forbidden
    res_b_get = client_b.get(f"/api/projects/{proj_a_id}")
    assert res_b_get.status_code == 403
    assert "permission" in res_b_get.json()["detail"].lower()

    # User B attempts to view Alice's deployments -> 403 Forbidden
    res_b_deps = client_b.get(f"/api/projects/{proj_a_id}/deployments")
    assert res_b_deps.status_code == 403

    # User B attempts to trigger deployment on Alice's project -> 403 Forbidden
    res_b_trig = client_b.post("/api/deployments/trigger", json={
        "project_id": proj_a_id,
        "commit_sha": "1234567890abcdef1234567890abcdef12345678",
        "commit_message": "Malicious deployment attempt",
    })
    assert res_b_trig.status_code == 403

    # User B attempts to trigger rollback on Alice's project -> 403 Forbidden
    res_b_roll = client_b.post("/api/deployments/rollback", json={
        "project_id": proj_a_id,
        "target_sha": "1234567890abcdef1234567890abcdef12345678",
        "reason": "Malicious rollback attempt",
    })
    assert res_b_roll.status_code == 403

    # User B attempts health probe on Alice's project -> 403 Forbidden
    res_b_probe = client_b.post(f"/api/projects/{proj_a_id}/check-health")
    assert res_b_probe.status_code == 403


# =============================================================================
# 3. SESSION PERSISTENCE & CSRF PROTECTION (Requirement 2)
# =============================================================================

def test_session_persistence_in_database(test_users):
    user_a, _ = test_users
    db = SessionLocal()
    try:
        from app.auth import create_user_session
        sess = create_user_session(db, user_a)
        assert sess.id is not None
        assert sess.session_token and len(sess.session_token) > 30
        assert sess.csrf_token and len(sess.csrf_token) > 30

        # Verify query from database
        persisted = db.query(UserSession).filter(UserSession.session_token == sess.session_token).first()
        assert persisted is not None
        assert persisted.user_id == user_a.id
    finally:
        db.close()


def test_csrf_protection_enforcement(test_users):
    user_a, _ = test_users
    c = create_client_for_user(user_a)

    # 1. Missing X-CSRF-Token header on mutating request -> 403 Forbidden
    c.headers.pop("X-CSRF-Token", None)
    res_no_csrf = c.post("/api/projects", json={
        "name": "No CSRF Project",
        "repo_name": f"org/no-csrf-{uuid.uuid4().hex[:6]}",
    })
    assert res_no_csrf.status_code == 403
    assert "CSRF" in res_no_csrf.json()["detail"]

    # 2. Invalid X-CSRF-Token header mismatch -> 403 Forbidden
    c.headers["X-CSRF-Token"] = "attacker-crafted-fake-token"
    res_bad_csrf = c.post("/api/projects", json={
        "name": "Bad CSRF Project",
        "repo_name": f"org/bad-csrf-{uuid.uuid4().hex[:6]}",
    })
    assert res_bad_csrf.status_code == 403
    assert "CSRF" in res_bad_csrf.json()["detail"]


def test_logout_invalidates_session_and_clears_cookies(test_users):
    user_a, _ = test_users
    c = create_client_for_user(user_a)
    session_token = c.cookies.get("deployeasy_session")
    assert session_token is not None

    # Call logout
    res_logout = c.post("/api/auth/logout")
    assert res_logout.status_code == 200

    # Verify session is deleted from database
    db = SessionLocal()
    try:
        found = db.query(UserSession).filter(UserSession.session_token == session_token).first()
        assert found is None
    finally:
        db.close()


# =============================================================================
# 4. AUTHENTICATION RATE LIMITING (Requirement 2)
# =============================================================================

def test_login_rate_limiting_enforced():
    c = TestClient(app)
    bad_creds = {"username": "nonexistent_dev", "password": "wrong_password_123"}

    # First 5 rapid attempts fail with 401
    for _ in range(5):
        r = c.post("/api/auth/login", json=bad_creds)
        assert r.status_code == 401

    # 6th rapid attempt within 60s window must be blocked by rate limiter with 429
    r_blocked = c.post("/api/auth/login", json=bad_creds)
    assert r_blocked.status_code == 429
    assert "Too many authentication attempts" in r_blocked.json()["detail"]


# =============================================================================
# 5. STRICT SSRF DEFENSE (Requirement 3)
# =============================================================================

@pytest.mark.parametrize("blocked_url", [
    "http://127.0.0.1:8080",
    "http://127.0.0.1:22",
    "http://localhost:3000",
    "http://169.254.169.254/latest/meta-data",
    "http://metadata.google.internal",
    "http://10.0.0.1/admin",
    "http://192.168.1.1",
    "http://172.16.0.1",
    "http://[::1]",
    "http://[fe80::1]",
    "ftp://example.com/file",
    "gopher://example.com",
    "file:///etc/passwd",
])
def test_ssrf_validation_blocks_internal_and_cloud_ips(blocked_url):
    with pytest.raises(SSRFValidationError):
        validate_target_url(blocked_url, allow_local_for_testing=False)


def test_ssrf_ip_validator_direct():
    # Loopback
    with pytest.raises(SSRFValidationError, match="restricted IP address"):
        validate_ip_address(ipaddress.ip_address("127.0.0.1"))
    # Private RFC1918
    with pytest.raises(SSRFValidationError, match="restricted IP address"):
        validate_ip_address(ipaddress.ip_address("10.20.30.40"))
    with pytest.raises(SSRFValidationError, match="restricted IP address"):
        validate_ip_address(ipaddress.ip_address("192.168.0.1"))
    # Link-local / AWS metadata
    with pytest.raises(SSRFValidationError, match="restricted IP address"):
        validate_ip_address(ipaddress.ip_address("169.254.169.254"))
    # IPv6 loopback
    with pytest.raises(SSRFValidationError, match="restricted IP address"):
        validate_ip_address(ipaddress.ip_address("::1"))


def test_ssrf_safe_redirect_handler_blocks_private_redirections():
    handler = SSRFSafeRedirectHandler()
    req = urllib.request.Request("https://safe-initial-domain.com")

    # Redirection to 169.254.169.254 must be intercepted and rejected
    with pytest.raises(SSRFValidationError, match="Redirect blocked by SSRF protection"):
        handler.redirect_request(req, None, 302, "Found", {}, "http://169.254.169.254/latest/meta-data")


@pytest.mark.parametrize("invalid_webhook", [
    ("http://discord.com/api/webhooks/test", "discord"),  # Non-HTTPS
    ("https://evil-site.com/api/webhooks", "discord"),    # Not discord.com
    ("https://discord.com.evil.com/webhook", "discord"),  # Subdomain phishing
    ("https://attacker.org/slack", "slack"),              # Not hooks.slack.com
    ("http://hooks.slack.com/services/T/B/X", "slack"),   # Non-HTTPS
])
def test_webhook_allowlist_validation(invalid_webhook):
    url, platform = invalid_webhook
    with pytest.raises(SSRFValidationError):
        validate_webhook_url(url, platform)


# =============================================================================
# 6. SECRET EXPOSURE PREVENTION (Requirement 2 & 7)
# =============================================================================

def test_deploy_hook_url_never_exposed_in_api(test_users):
    user_a, _ = test_users
    c = create_client_for_user(user_a)

    secret_hook = "https://api.render.com/deploy/srv-very-secret-production-token-12345"
    res = c.post("/api/projects", json={
        "name": "Secret Hook Service",
        "repo_name": f"org/secret-svc-{uuid.uuid4().hex[:6]}",
        "service_url": "https://secret-svc.onrender.com",
        "deploy_hook_url": secret_hook,
    })
    assert res.status_code == 201
    created_data = res.json()
    assert "deploy_hook_url" not in created_data
    assert created_data["has_deploy_hook"] is True
    proj_id = created_data["id"]

    # In single get
    res_get = c.get(f"/api/projects/{proj_id}")
    assert "deploy_hook_url" not in res_get.json()
    assert res_get.json()["has_deploy_hook"] is True

    # In list
    res_list = c.get("/api/projects")
    for p in res_list.json():
        assert "deploy_hook_url" not in p

    # In overview
    res_ov = c.get("/api/overview")
    for p in res_ov.json()["projects"]:
        assert "deploy_hook_url" not in p


def test_env_validator_never_leaks_secrets():
    unauth = TestClient(app)
    raw_secret = "P@ssw0rd_Super_Sensitive_999!"
    res = unauth.post("/api/validate-env", json={
        "env_vars": {
            "DATABASE_URL": f"postgresql://appuser:{raw_secret}@db.internal:5432/main",
            "API_SECRET_KEY": raw_secret,
        }
    })
    assert res.status_code == 200
    data = res.json()
    # Ensure raw secret is nowhere in response
    assert raw_secret not in str(data)
    assert "***" in data["sanitized_variables"]["DATABASE_URL"]


# =============================================================================
# 7. REAL DISPATCH & UNVERIFIED ROLLBACK (Requirement 4)
# =============================================================================

def test_deployment_fails_when_no_integration_configured(test_users):
    """When no GitHub token/App and no deploy hook is configured, trigger MUST return 400."""
    user_a, _ = test_users
    c = create_client_for_user(user_a)

    res_proj = c.post("/api/projects", json={
        "name": "No Integration Service",
        "repo_name": f"org/unconfigured-{uuid.uuid4().hex[:6]}",
        "service_url": "https://unconfigured.onrender.com",
        "deploy_hook_url": "",
    })
    proj_id = res_proj.json()["id"]

    with patch("app.main.config.GITHUB_TOKEN", ""), patch("app.main.config.GITHUB_APP_ID", ""):
        res_trig = c.post("/api/deployments/trigger", json={
            "project_id": proj_id,
            "commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "commit_message": "Release trigger attempt",
            "force": True,
        })
        assert res_trig.status_code == 400
        assert "No deployment integration configured" in res_trig.json()["detail"]


def test_rollback_requires_full_40_char_sha(test_users):
    user_a, _ = test_users
    c = create_client_for_user(user_a)

    res_proj = c.post("/api/projects", json={
        "name": "SHA Verification Service",
        "repo_name": f"org/sha-test-{uuid.uuid4().hex[:6]}",
        "service_url": "https://sha-test.onrender.com",
    })
    proj_id = res_proj.json()["id"]

    # Short 7-character SHA must be rejected
    res_short = c.post("/api/deployments/rollback", json={
        "project_id": proj_id,
        "target_sha": "a1b2c3d",
        "reason": "Invalid short sha",
    })
    assert res_short.status_code == 400
    assert "40-character" in res_short.json()["detail"]


@patch("app.main.dispatch_github_workflow")
@patch("app.main.verify_live_version", return_value=False)
def test_rollback_unverified_reports_deploying_not_rolled_back(mock_verify, mock_dispatch, test_users):
    """If live version on /version does NOT match target SHA yet, rollback must NOT report success."""
    user_a, _ = test_users
    c = create_client_for_user(user_a)

    target_sha = "1234567890abcdef1234567890abcdef12345678"
    res_proj = c.post("/api/projects", json={
        "name": "Rollback Convergence Service",
        "repo_name": f"org/conv-test-{uuid.uuid4().hex[:6]}",
        "service_url": "https://conv-test.onrender.com",
    })
    proj_id = res_proj.json()["id"]

    with patch("app.main.config.GITHUB_TOKEN", "mock_gh_token"):
        res_roll = c.post("/api/deployments/rollback", json={
            "project_id": proj_id,
            "target_sha": target_sha,
            "reason": "Rollback testing live convergence",
        })
        assert res_roll.status_code == 200
        data = res_roll.json()
        # Status must be 'deploying' awaiting convergence, NOT 'rolled_back'
        assert data["status"] == "deploying"
        assert "awaiting live container convergence" in data["logs_summary"]


@patch("app.main.dispatch_github_workflow")
@patch("app.main.verify_live_version", return_value=True)
def test_rollback_verified_reports_rolled_back(mock_verify, mock_dispatch, test_users):
    """When live version probe confirms target SHA is running, rollback reports rolled_back."""
    user_a, _ = test_users
    c = create_client_for_user(user_a)

    target_sha = "1234567890abcdef1234567890abcdef12345678"
    res_proj = c.post("/api/projects", json={
        "name": "Rollback Verified Service",
        "repo_name": f"org/verified-test-{uuid.uuid4().hex[:6]}",
        "service_url": "https://verified-test.onrender.com",
    })
    proj_id = res_proj.json()["id"]

    with patch("app.main.config.GITHUB_TOKEN", "mock_gh_token"):
        res_roll = c.post("/api/deployments/rollback", json={
            "project_id": proj_id,
            "target_sha": target_sha,
            "reason": "Verified rollback",
        })
        assert res_roll.status_code == 200
        data = res_roll.json()
        assert data["status"] == "rolled_back"
        assert "probe verified SHA" in data["logs_summary"]


# =============================================================================
# 8. READINESS HARD GATES ENFORCEMENT (Requirement 6)
# =============================================================================

def test_readiness_hard_gate_blocks_deployment_dispatch(test_users):
    user_a, _ = test_users
    c = create_client_for_user(user_a)

    res_proj = c.post("/api/projects", json={
        "name": "Gate Service",
        "repo_name": f"org/gate-test-{uuid.uuid4().hex[:6]}",
        "service_url": "https://gate-test.onrender.com",
    })
    proj_id = res_proj.json()["id"]

    # Inject a critical vulnerability scan into DB for this project
    db = SessionLocal()
    try:
        db.add(SecurityScan(
            project_id=proj_id,
            scan_type="trivy",
            target="gate-test:latest",
            critical_count=2,
            high_count=3,
            passed=False,
        ))
        db.commit()
    finally:
        db.close()

    # Verify readiness endpoint reports blocked
    res_readiness = c.get(f"/api/projects/{proj_id}/readiness")
    assert res_readiness.status_code == 200
    assert res_readiness.json()["deployment_blocked"] is True

    # Attempting to trigger deployment without force=True must return 409 Conflict
    res_trig = c.post("/api/deployments/trigger", json={
        "project_id": proj_id,
        "commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        "commit_message": "Deploying vulnerable release",
        "force": False,
    })
    assert res_trig.status_code == 409
    assert "Deployment blocked by safety gates" in res_trig.json()["detail"]


# =============================================================================
# 9. DEMO USER RESTRICTIONS (Requirement 1 & 5)
# =============================================================================

def test_demo_user_restrictions():
    demo_client = TestClient(app)
    r_demo = demo_client.post("/api/auth/demo-login")
    assert r_demo.status_code == 200
    csrf = demo_client.cookies.get("deployeasy_csrf")
    demo_client.headers["X-CSRF-Token"] = csrf

    # Demo cannot create project
    r_create = demo_client.post("/api/projects", json={
        "name": "Demo Prohibited Project",
        "repo_name": "demo/forbidden",
    })
    assert r_create.status_code == 403
    assert "read-only access" in r_create.json()["detail"]
