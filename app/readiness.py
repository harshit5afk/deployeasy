"""Pre-Deploy Readiness Score (0-100%) Calculator for DeployEasy.

Evaluates test outcomes, vulnerability gates, secrets scans, health baseline,
and rollback readiness to calculate deployment confidence before pushing to production.
"""
from typing import Any


def calculate_readiness_score(
    tests_passed: bool = True,
    critical_vulns: int = 0,
    high_vulns: int = 0,
    secrets_detected: bool = False,
    health_status: str = "operational",
    rollback_available: bool = True,
) -> dict[str, Any]:
    """Calculate pre-deploy confidence score and checklist."""
    score = 0
    checklist = []

    # 1. CI Tests (25 points)
    if tests_passed:
        score += 25
        checklist.append({"category": "CI Tests", "status": "PASS", "points": 25, "message": "All unit and integration tests passed."})
    else:
        checklist.append({"category": "CI Tests", "status": "FAIL", "points": 0, "message": "Failing test assertions in test suite."})

    # 2. Container Security & CVEs (25 points)
    if critical_vulns == 0 and high_vulns == 0:
        score += 25
        checklist.append({"category": "Vulnerability Scan", "status": "PASS", "points": 25, "message": "Zero Critical or High severity CVEs in container image."})
    elif critical_vulns == 0 and high_vulns > 0:
        score += 10
        checklist.append({"category": "Vulnerability Scan", "status": "WARN", "points": 10, "message": f"{high_vulns} High severity CVEs detected."})
    else:
        checklist.append({"category": "Vulnerability Scan", "status": "FAIL", "points": 0, "message": f"{critical_vulns} Critical CVEs detected in image."})

    # 3. Secrets Audit (20 points)
    if not secrets_detected:
        score += 20
        checklist.append({"category": "Secrets Audit", "status": "PASS", "points": 20, "message": "No exposed API keys or credentials detected by Gitleaks."})
    else:
        checklist.append({"category": "Secrets Audit", "status": "FAIL", "points": 0, "message": "Gitleaks detected credentials in repository."})

    # 4. Health Check Baseline (15 points)
    if health_status == "operational":
        score += 15
        checklist.append({"category": "Fleet Health", "status": "PASS", "points": 15, "message": "Production health endpoint returning HTTP 200 OK."})
    elif health_status == "degraded":
        score += 5
        checklist.append({"category": "Fleet Health", "status": "WARN", "points": 5, "message": "Service reporting degraded status or elevated latency."})
    else:
        checklist.append({"category": "Fleet Health", "status": "FAIL", "points": 0, "message": "Service is currently unreachable or down."})

    # 5. Rollback Image Readiness (15 points)
    if rollback_available:
        score += 15
        checklist.append({"category": "Rollback Readiness", "status": "PASS", "points": 15, "message": "Previous immutable container image tagged in GHCR."})
    else:
        checklist.append({"category": "Rollback Readiness", "status": "WARN", "points": 0, "message": "No verified previous container image found for instant rollback."})

    # Hard Safety Gates Check: A failure in tests, critical CVEs, or secrets is a hard blocker
    hard_blockers: list[str] = []
    if not tests_passed:
        hard_blockers.append("Automated test suite failed assertions.")
    if critical_vulns > 0:
        hard_blockers.append(f"{critical_vulns} Critical severity CVE(s) detected in container image.")
    if secrets_detected:
        hard_blockers.append("Hardcoded secrets or credentials detected by Gitleaks.")

    is_blocked = len(hard_blockers) > 0

    # Determine confidence tier with hard safety enforcement
    if is_blocked:
        # Cap score to failing threshold
        score = min(score, 35)
        tier = "Deployment Blocked"
        badge = "badge-danger"
        recommendation = "CRITICAL SAFETY GATE TRIPPED: " + "; ".join(hard_blockers) + " Deployment strictly prohibited."
    elif score >= 85:
        tier = "Ready for Production"
        badge = "badge-success"
        recommendation = "All critical gates passed. Safe to deploy."
    elif score >= 60:
        tier = "Deploy with Caution"
        badge = "badge-warning"
        recommendation = "Review warning items before promoting to production."
    else:
        tier = "Deployment Blocked"
        badge = "badge-danger"
        recommendation = "Resolve critical failures before deploying."

    return {
        "readiness_score": score,
        "max_score": 100,
        "confidence_tier": tier,
        "badge_class": badge,
        "recommendation": recommendation,
        "checklist": checklist,
        "deployment_blocked": is_blocked,
        "blocking_reasons": hard_blockers,
    }

