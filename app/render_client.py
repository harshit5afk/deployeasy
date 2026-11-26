"""Small client for creating user-confirmed Render web and static services."""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from . import config


class RenderIntegrationError(RuntimeError):
    """A safe, user-facing Render API error."""


def create_render_service(
    *,
    repo_name: str,
    branch: str,
    project_name: str,
    project_id: int,
    service_type: str,
    runtime: str,
    region: str,
    build_command: str,
    start_command: str,
    publish_path: str,
) -> dict[str, str]:
    api_key = config.RENDER_API_KEY.strip()
    owner_id = config.RENDER_OWNER_ID.strip()
    if not api_key:
        raise RenderIntegrationError("Render is not connected yet. Add RENDER_API_KEY to the DeployEasy Render service environment.")
    if not owner_id:
        raise RenderIntegrationError("Add RENDER_OWNER_ID (your Render workspace ID) to the DeployEasy service environment.")

    slug = re.sub(r"[^a-z0-9-]+", "-", project_name.lower()).strip("-") or "app"
    name = f"{slug[:45]}-{project_id}"
    body: dict[str, Any] = {
        "type": service_type,
        "name": name,
        "ownerId": owner_id,
        "repo": f"https://github.com/{repo_name}",
        "branch": branch,
        "autoDeployTrigger": "commit",
    }

    if service_type == "static_site":
        body["serviceDetails"] = {
            "buildCommand": build_command,
            "publishPath": publish_path,
            "routes": [
                {
                    "type": "rewrite",
                    "source": "/*",
                    "destination": "/index.html",
                }
            ],
        }
    else:
        details: dict[str, Any] = {
            "runtime": runtime,
            "plan": "free",
            "region": region,
            "numInstances": 1,
        }
        if runtime == "docker":
            details["envSpecificDetails"] = {"dockerfilePath": "./Dockerfile"}
        else:
            details["envSpecificDetails"] = {
                "buildCommand": build_command,
                "startCommand": start_command,
            }
        body["serviceDetails"] = details

    request = urllib.request.Request(
        "https://api.render.com/v1/services",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        # Don't return request headers or API key details to the browser.
        try:
            error_body = json.loads(exc.read().decode("utf-8", errors="replace"))
            reason = error_body.get("message") or error_body.get("error")
        except (ValueError, AttributeError):
            reason = None
        if exc.code == 402:
            raise RenderIntegrationError("Render requires billing setup or this account cannot create the selected service.") from exc
        if exc.code == 401:
            raise RenderIntegrationError("Render rejected the API key. Check RENDER_API_KEY in the DeployEasy service environment.") from exc
        if exc.code == 403:
            raise RenderIntegrationError("This Render API key cannot create services in the selected workspace. Check its permissions and RENDER_OWNER_ID.") from exc
        raise RenderIntegrationError(f"Render could not create the service (HTTP {exc.code}). {reason or 'Check the repository and service settings.'}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RenderIntegrationError("Could not reach Render. Try again in a moment.") from exc

    service = result.get("service") or {}
    service_details = service.get("serviceDetails") or {}
    service_id = service.get("id")
    service_url = service_details.get("url")
    if not service_id or not service_url:
        raise RenderIntegrationError("Render accepted the request but did not return the service ID and public URL.")
    return {
        "service_id": str(service_id),
        "service_url": str(service_url),
        "dashboard_url": str(service.get("dashboardUrl") or ""),
        "deploy_id": str(result.get("deployId") or ""),
    }


def get_latest_render_deploy_status(service_id: str) -> str | None:
    """Return the latest deployment status for a Render service."""
    api_key = config.RENDER_API_KEY.strip()
    if not api_key:
        raise RenderIntegrationError("Render API is not connected.")

    request = urllib.request.Request(
        f"https://api.render.com/v1/services/{service_id}/deploys?limit=1",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RenderIntegrationError("Render rejected the API key or it cannot access this service.") from exc
        raise RenderIntegrationError(f"Could not retrieve Render deployment status (HTTP {exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RenderIntegrationError("Could not reach Render to retrieve deployment status.") from exc
    except (ValueError, TypeError) as exc:
        raise RenderIntegrationError("Render returned an invalid deployment status response.") from exc

    if not isinstance(result, list) or not result:
        return None

    latest = result[0]
    if isinstance(latest, dict):
        deploy = latest.get("deploy", latest)
        if isinstance(deploy, dict):
            deploy_status = deploy.get("status")
            if isinstance(deploy_status, str) and deploy_status:
                return deploy_status[:30]

    raise RenderIntegrationError("Render returned an invalid deployment status response.")


def get_render_service_environment(service_id: str) -> dict[str, str]:
    """Fetch Render environment variables for server-side validation only."""
    api_key = config.RENDER_API_KEY.strip()
    if not api_key:
        raise RenderIntegrationError("Render API is not connected.")

    variables: dict[str, str] = {}
    cursor = None
    seen_cursors: set[str] = set()
    for _ in range(10):
        query: dict[str, str | int] = {"limit": 100}
        if cursor:
            query["cursor"] = cursor
        request = urllib.request.Request(
            f"https://api.render.com/v1/services/{service_id}/env-vars?{urllib.parse.urlencode(query)}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                page = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise RenderIntegrationError("Render rejected the API key or it cannot access this service's environment.") from exc
            raise RenderIntegrationError(f"Could not retrieve Render environment variables (HTTP {exc.code}).") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RenderIntegrationError("Could not reach Render to retrieve environment variables.") from exc
        except (ValueError, TypeError) as exc:
            raise RenderIntegrationError("Render returned an invalid environment variables response.") from exc

        if not isinstance(page, list):
            raise RenderIntegrationError("Render returned an invalid environment variables response.")
        if not page:
            return variables

        for item in page:
            env_var = item.get("envVar") if isinstance(item, dict) else None
            if (
                not isinstance(env_var, dict)
                or not isinstance(env_var.get("key"), str)
                or not isinstance(env_var.get("value"), str)
                or not isinstance(item.get("cursor"), str)
                or not item["cursor"]
            ):
                raise RenderIntegrationError("Render returned an invalid environment variable entry.")
            variables[env_var["key"]] = env_var["value"]

        next_cursor = page[-1]["cursor"]
        if next_cursor in seen_cursors:
            raise RenderIntegrationError("Render returned invalid pagination for environment variables.")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    raise RenderIntegrationError("Render returned too many environment variable pages to audit safely.")
