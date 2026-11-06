"""Webhook Notifications Engine for DeployEasy deployments.

Dispatches formatted deployment and incident alert payloads to Discord,
Slack, or custom webhook endpoints with SSRF protection.
"""
import json
import logging
from typing import Any

from .ssrf import SSRFValidationError, safe_urlopen, validate_webhook_url

log = logging.getLogger("deployeasy")


def format_discord_payload(
    event_type: str,
    project_name: str,
    commit_sha: str,
    message: str,
    status: str = "success",
) -> dict[str, Any]:
    """Format payload for Discord webhooks with embedded rich formatting."""
    color_map = {
        "success": 0x10B981,   # Green
        "failure": 0xEF4444,   # Red
        "rollback": 0x8B5CF6,  # Purple
        "degraded": 0xF59E0B,  # Amber
    }
    color = color_map.get(status.lower(), 0x6366F1)

    return {
        "username": "DeployEasy Alerts",
        "avatar_url": "https://raw.githubusercontent.com/harshit5afk/deployeasy/main/docs/logo.png",
        "embeds": [
            {
                "title": f"[{status.upper()}] {project_name}: {event_type.replace('_', ' ').title()}",
                "description": message,
                "color": color,
                "fields": [
                    {"name": "Commit SHA", "value": f"`{commit_sha[:7]}`", "inline": True},
                    {"name": "Status", "value": status.upper(), "inline": True},
                ],
                "footer": {"text": "DeployEasy Continuous Deployment Observatory"},
            }
        ],
    }


def format_slack_payload(
    event_type: str,
    project_name: str,
    commit_sha: str,
    message: str,
    status: str = "success",
) -> dict[str, Any]:
    """Format payload for Slack incoming webhooks."""
    emoji = "✅" if status == "success" else ("⏪" if status == "rollback" else "⚠️")
    return {
        "text": f"{emoji} *{project_name}*: {event_type.title()} ({status.upper()})",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{emoji} {project_name} - {event_type.title()}*\nStatus: `{status.upper()}` | Commit: `{commit_sha[:7]}`\n{message}",
                },
            }
        ],
    }


def dispatch_webhook(
    webhook_url: str,
    payload: dict[str, Any],
    platform: str = "discord",
    timeout: float = 4.0,
    allow_local_for_testing: bool = False,
) -> bool:
    """Send webhook payload with SSRF protection and platform allowlist verification."""
    if not webhook_url or not webhook_url.startswith("https://"):
        return False

    try:
        if not allow_local_for_testing:
            validate_webhook_url(webhook_url, platform)
    except SSRFValidationError as exc:
        log.warning("SSRF blocked webhook dispatch to %s: %s", webhook_url, exc)
        return False

    try:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": "DeployEasy-Webhook/1.0"}
        with safe_urlopen(
            webhook_url,
            data=data,
            headers=headers,
            timeout=timeout,
            allow_local_for_testing=allow_local_for_testing,
        ) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:  # noqa: BLE001
        log.warning("Webhook dispatch error: %s", exc)
        return False
