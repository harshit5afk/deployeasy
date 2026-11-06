"""GitHub REST API and Workflow Dispatch client for DeployEasy.

Executes real GitHub Actions workflow_dispatch calls using configured
GitHub tokens or GitHub App installation credentials, and verifies live versions.
"""
import json
import logging
import urllib.request
from typing import Any

from . import config
from .ssrf import safe_urlopen

log = logging.getLogger("deployeasy")


class GitHubIntegrationError(RuntimeError):
    """Raised when GitHub Actions workflow dispatch fails or is misconfigured."""


def get_github_auth_token() -> str:
    """Retrieve GitHub token from environment or GitHub App configuration."""
    if config.GITHUB_TOKEN:
        return config.GITHUB_TOKEN.strip()
    return ""


def dispatch_github_workflow(
    repo_name: str,
    workflow_file: str,
    inputs: dict[str, Any] | None = None,
    ref: str = "main",
) -> dict[str, Any]:
    """Execute real workflow_dispatch call to GitHub Actions API.
    
    Target URL: https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches
    """
    token = get_github_auth_token()
    if not token:
        raise GitHubIntegrationError(
            "No GitHub authentication configured. Set GITHUB_TOKEN or configure a GitHub App in environment variables."
        )

    if not repo_name or "/" not in repo_name:
        raise GitHubIntegrationError(f"Invalid repository name format '{repo_name}'. Expected 'owner/repo'.")

    url = f"https://api.github.com/repos/{repo_name}/actions/workflows/{workflow_file}/dispatches"
    payload = {
        "ref": ref or "main",
        "inputs": inputs or {},
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "DeployEasy-ControlCenter/1.0",
        "Content-Type": "application/json",
    }

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            # GitHub returns 204 No Content on successful dispatch
            if resp.status in (200, 201, 204):
                return {
                    "dispatched": True,
                    "repo": repo_name,
                    "workflow": workflow_file,
                    "ref": ref,
                    "inputs": inputs or {},
                }
            raise GitHubIntegrationError(f"GitHub API returned unexpected status {resp.status}")
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8", errors="replace")
        raise GitHubIntegrationError(f"GitHub API workflow dispatch error (HTTP {exc.code}): {err_msg}") from exc
    except Exception as exc:
        raise GitHubIntegrationError(f"Failed to dispatch GitHub workflow: {exc}") from exc


def verify_live_version(
    service_url: str,
    expected_sha: str,
    timeout: float = 4.0,
    allow_local_for_testing: bool = False,
) -> bool:
    """Probe the live service's /version endpoint to verify the running Git SHA matches expected_sha."""
    if not service_url:
        return False

    url = service_url.rstrip("/") + "/version"
    try:
        with safe_urlopen(url, timeout=timeout, allow_local_for_testing=allow_local_for_testing) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                live_sha = str(body.get("git_sha", "")).strip().lower()
                target_sha = expected_sha.strip().lower()
                # Check 40-char exact or prefix match
                if live_sha == target_sha or live_sha.startswith(target_sha[:7]) or target_sha.startswith(live_sha[:7]):
                    return True
    except Exception as exc:  # noqa: BLE001
        log.info("Live version probe for %s returned: %s", url, exc)
        return False
    return False
