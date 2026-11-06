"""Intelligent CI/CD Deployment Failure Analysis & Diagnostic Engine.

Parses build, test, and deployment logs to automatically extract root causes,
categorize failure types, and recommend specific fixes for developers.
"""
import re
from typing import Any


def analyze_deployment_logs(log_text: str) -> dict[str, Any]:
    """Parse log text and return a structured diagnostic summary with suggested fixes."""
    if not log_text or not log_text.strip():
        return {
            "error_category": "none",
            "severity": "LOW",
            "summary": "No logs provided for analysis.",
            "root_cause": "",
            "suggested_fix": "Trigger a build or check the pipeline logs in GitHub Actions.",
            "detected": False,
        }

    # 1. Secret Leaks (Gitleaks)
    if "gitleaks" in log_text.lower() and ("leak" in log_text.lower() or "secret detected" in log_text.lower()):
        match = re.search(r"(finding:.*|rule:.*|secret:.*)", log_text, re.IGNORECASE)
        root = match.group(0) if match else "Gitleaks detected sensitive credentials in git history."
        return {
            "error_category": "secret_leak",
            "severity": "CRITICAL",
            "summary": "Security alert: Uncommitted or committed secrets detected by Gitleaks.",
            "root_cause": root,
            "suggested_fix": "Purge the secret using git-filter-repo, rotate the leaked credential immediately, and add the secret file/pattern to .gitignore.",
            "detected": True,
        }

    # 2. Trivy Container Vulnerability Gate
    if "trivy" in log_text.lower() and ("critical" in log_text.lower() or "high" in log_text.lower() or "exit code: 1" in log_text.lower()):
        cve_match = re.search(r"(CVE-\d{4}-\d+|GHSA-[a-z0-9\-]+)", log_text)
        cve = cve_match.group(0) if cve_match else "Unpatched High/Critical CVE"
        return {
            "error_category": "security_vulnerability",
            "severity": "CRITICAL",
            "summary": f"Security Gate Blocked: Container image contains high-severity vulnerabilities ({cve}).",
            "root_cause": f"Trivy scan failed with exit code 1 due to vulnerabilities: {cve}",
            "suggested_fix": "Update vulnerable package versions in requirements.txt or upgrade the base Docker image (e.g. python:3.12-slim) to include recent security patches.",
            "detected": True,
        }

    # 3. Pytest / Unit Test Failure
    if "failed" in log_text.lower() and ("pytest" in log_text.lower() or "assertionerror" in log_text.lower()):
        fail_match = re.search(r"(FAILED\s+[\w\/\.\:\-]+|AssertionError.*)", log_text)
        fail_detail = fail_match.group(0) if fail_match else "One or more pytest test assertions failed."
        return {
            "error_category": "test_failure",
            "severity": "HIGH",
            "summary": "Unit test suite failed in CI pipeline.",
            "root_cause": fail_detail,
            "suggested_fix": "Run `pytest -v` locally in your environment, fix the failing assertion or mock external services, and commit the fix.",
            "detected": True,
        }

    # 4. Ruff Linter Error
    if "ruff" in log_text.lower() and ("error" in log_text.lower() or "failed" in log_text.lower()):
        ruff_match = re.search(r"(\w+\.py:\d+:\d+:.*)", log_text)
        detail = ruff_match.group(0) if ruff_match else "Code style or linting rule violations detected by Ruff."
        return {
            "error_category": "lint_error",
            "severity": "MEDIUM",
            "summary": "Code linting / format check failed.",
            "root_cause": detail,
            "suggested_fix": "Run `ruff check --fix .` locally to automatically format and resolve linting violations.",
            "detected": True,
        }

    # 5. Deployment / Smoke Test Timeout
    if "timed out waiting for" in log_text.lower() or "smoke test" in log_text.lower() and "failed" in log_text.lower():
        timeout_match = re.search(r"(Timed out waiting for [0-9a-f]+ to go live.*)", log_text, re.IGNORECASE)
        detail = timeout_match.group(0) if timeout_match else "Health verification smoke test timed out waiting for the target SHA on /version."
        return {
            "error_category": "deployment_timeout",
            "severity": "HIGH",
            "summary": "Post-deploy smoke verification timed out.",
            "root_cause": detail,
            "suggested_fix": "Check Render service logs. If using a free instance, cold start might exceed the retry window. Verify that the Docker container starts cleanly on the assigned $PORT.",
            "detected": True,
        }

    # 6. Docker Build Failure
    if "docker build" in log_text.lower() and ("non-zero code" in log_text.lower() or "error" in log_text.lower()):
        build_match = re.search(r"(ERROR:.*|returned a non-zero code: \d+)", log_text)
        detail = build_match.group(0) if build_match else "Docker image build step failed."
        return {
            "error_category": "docker_build_failure",
            "severity": "HIGH",
            "summary": "Docker image compilation failed in CI.",
            "root_cause": detail,
            "suggested_fix": "Test building the image locally using `docker build -t test .` to reproduce the missing dependency or build step failure.",
            "detected": True,
        }

    # 7. Fallback / Normal logs
    return {
        "error_category": "none",
        "severity": "LOW",
        "summary": "No critical deployment failure patterns recognized in logs.",
        "root_cause": "",
        "suggested_fix": "All checks appear healthy or errors are outside standard CI failure signatures.",
        "detected": False,
    }

