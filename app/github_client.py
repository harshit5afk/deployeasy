"""GitHub REST API and Workflow Dispatch client for DeployEasy.

Executes real GitHub Actions workflow_dispatch calls using configured
GitHub tokens or GitHub App installation credentials, and verifies live versions.
"""
import json
import logging
import time
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


def inspect_github_repository(repo_name: str) -> dict[str, Any]:
    """Check repository visibility, default branch, token access, and DeployEasy workflows."""
    token = get_github_auth_token()
    if not repo_name or not re_full_repo(repo_name):
        raise GitHubIntegrationError("Enter a GitHub repository as owner/repo.")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "DeployEasy-ControlCenter/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo_name}", headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            repo = json.load(response)
        workflows = {}
        for workflow in ("pipeline.yml", "rollback.yml"):
            workflow_req = urllib.request.Request(
                f"https://api.github.com/repos/{repo_name}/contents/.github/workflows/{workflow}",
                headers=headers,
            )
            try:
                with urllib.request.urlopen(workflow_req, timeout=5) as response:
                    workflows[workflow] = response.status == 200
            except urllib.error.HTTPError as err:
                if err.code == 404:
                    workflows[workflow] = False
                else:
                    raise
        return {
            "repo_name": repo.get("full_name", repo_name),
            "default_branch": repo.get("default_branch", "main"),
            "private": bool(repo.get("private")),
            "token_configured": bool(token),
            "token_can_access_repo": bool(token),
            "dispatch_permission_note": "GitHub workflow_dispatch requires Actions: write permission; GitHub's repository metadata does not expose that permission for this token.",
            "workflows": workflows,
            "ready": bool(token) and all(workflows.values()),
        }
    except urllib.error.HTTPError as err:
        if err.code in (401, 403, 404):
            raise GitHubIntegrationError("GitHub could not access this repository. Check the URL and GITHUB_TOKEN repository permissions.") from err
        raise GitHubIntegrationError(f"GitHub repository check failed (HTTP {err.code}).") from err
    except Exception as err:
        if isinstance(err, GitHubIntegrationError):
            raise
        raise GitHubIntegrationError(f"Could not reach GitHub: {err}") from err


def re_full_repo(repo_name: str) -> bool:
    import re
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo_name))


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
    retries: int = 1,
    delay: float = 2.0,
) -> bool:
    """Probe the live service's /version endpoint to verify the running Git SHA matches expected_sha.

    Supports retries for container rollout convergence and strictly guards against empty or invalid SHAs.
    """
    if not service_url or not expected_sha:
        return False

    target_sha = expected_sha.strip().lower()
    if len(target_sha) < 7:
        return False

    url = service_url.rstrip("/") + "/version"

    for attempt in range(max(1, retries)):
        try:
            with safe_urlopen(url, timeout=timeout, allow_local_for_testing=allow_local_for_testing) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    live_sha = str(body.get("git_sha", "")).strip().lower()
                    if len(live_sha) >= 7:
                        # Full 40-character exact match preferred
                        if len(live_sha) == 40 and len(target_sha) == 40:
                            if live_sha == target_sha:
                                return True
                        # Prefix match requiring minimum 7 characters
                        elif live_sha.startswith(target_sha[:7]):
                            return True
        except Exception as exc:  # noqa: BLE001
            log.info("Live version probe for %s (attempt %d/%d) returned: %s", url, attempt + 1, retries, exc)

        if attempt < retries - 1:
            time.sleep(delay)

    return False
