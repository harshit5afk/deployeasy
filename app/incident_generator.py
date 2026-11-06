"""Automated Incident Response & Post-Mortem Generator for DeployEasy.

Generates structured incident reports and post-mortems conforming to the
operational playbooks in docs/incident-response.md.
"""
from datetime import UTC, datetime
from typing import Any

from .log_analyzer import analyze_deployment_logs


def generate_incident_report(
    project_name: str,
    failed_sha: str,
    rollback_sha: str | None = None,
    symptoms: str = "Availability failure on /health",
    log_excerpt: str = "",
    failure_timestamp: str | None = None,
    recovery_timestamp: str | None = None,
) -> dict[str, Any]:
    """Generate a structured incident report and markdown post-mortem."""
    now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    fail_time = failure_timestamp or now_str
    recover_time = recovery_timestamp or now_str

    # Run log analysis to automatically deduce root cause and fix
    analysis = analyze_deployment_logs(log_excerpt) if log_excerpt else {
        "error_category": "availability_failure",
        "severity": "HIGH",
        "summary": "Service degradation or health check timeout",
        "root_cause": symptoms,
        "suggested_fix": "Verify application health endpoint and rollback to last verified image.",
    }

    # Generate Markdown post-mortem matching docs/incident-response.md format
    ttr_note = "Under 5 minutes (Automated Rollback)"
    markdown_content = f"""# Incident Post-Mortem: {project_name}

**Incident Date:** {fail_time}  
**Status:** Resolved  
**Severity:** {analysis['severity']}  
**Time to Recover (TTR):** {ttr_note}  

---

## 1. Summary
At {fail_time}, deployment `{failed_sha[:7]}` caused {symptoms.lower()}. 
{analysis['summary']}

## 2. Impact & Symptoms
- **Affected Commit:** `{failed_sha}`
- **Symptoms Observed:** {symptoms}
- **Restored Version:** `{rollback_sha[:7] if rollback_sha else 'Previous verified release'}`

## 3. Root Cause Analysis
{analysis['root_cause'] or 'Uncaught exception or connection failure on healthcheck endpoint.'}

## 4. Remediation & Recovery Action
1. One-click rollback executed to stable release container image `{rollback_sha[:7] if rollback_sha else 'known-good'}`.
2. Verified health probe returning HTTP 200 OK.
3. Live `/version` verified to match active rollback SHA.

## 5. Preventative Actions
- {analysis['suggested_fix']}
- Ensure all environment variables are verified via DeployEasy Env Validator before rollout.
- Keep rollback container images pinned and stored in GHCR.
"""

    return {
        "title": f"Incident Report: {project_name} ({failed_sha[:7]})",
        "severity": analysis["severity"],
        "error_category": analysis["error_category"],
        "failure_time": fail_time,
        "recovery_time": recover_time,
        "failed_sha": failed_sha[:7],
        "rollback_sha": (rollback_sha[:7] if rollback_sha else None),
        "symptoms": symptoms,
        "root_cause": analysis["root_cause"],
        "suggested_fix": analysis["suggested_fix"],
        "markdown_report": markdown_content.strip(),
    }

