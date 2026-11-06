"""Environment Variable Validator for DeployEasy deployments.

Prevents production deployment crashes caused by missing, malformed,
or placeholder configuration and exposed secrets.
"""
import re
from typing import Any

SCHEMA_RULES = {
    "PORT": {"type": "integer", "min": 1, "max": 65535, "required": False, "default": "8080"},
    "APP_VERSION": {"type": "version", "required": False, "default": "1.0.0"},
    "DATABASE_URL": {"type": "database_url", "required": False, "default": "sqlite:///./deployeasy.db"},
    "SERVICE_URL": {"type": "url", "required": False},
    "RENDER_DEPLOY_HOOK_URL": {"type": "secret_url", "required": False},
    "GITHUB_REPO": {"type": "repo", "required": False},
    "GITHUB_TOKEN": {"type": "secret", "required": False},
}


def mask_secret(value: str) -> str:
    """Safely mask secret strings for UI display."""
    if not value:
        return ""
    if len(value) <= 8:
        return "********"
    return value[:4] + "..." + value[-4:]


def validate_environment(env_vars: dict[str, str]) -> dict[str, Any]:
    """Validate a dictionary of environment variables against production criteria."""
    errors: list[str] = []
    warnings: list[str] = []
    sanitized: dict[str, str] = {}

    for key, val in env_vars.items():
        key_clean = key.strip()
        val_clean = str(val).strip() if val is not None else ""

        # Validate variable name syntax
        if not re.match(r"^[A-Z0-9_]+$", key_clean):
            warnings.append(f"Environment variable '{key_clean}' should be UPPERCASE with underscores.")

        # Check placeholder secrets
        placeholders = ["your-username", "your-secret", "placeholder", "changeme", "secret", "xxx", "123456"]
        if any(p in val_clean.lower() for p in placeholders) and len(val_clean) < 35:
            warnings.append(f"Variable '{key_clean}' appears to contain a template placeholder value ('{val_clean}').")

        # Specific type validations
        if key_clean == "PORT":
            try:
                port_num = int(val_clean)
                if port_num < 1 or port_num > 65535:
                    errors.append(f"PORT must be an integer between 1 and 65535, got {port_num}.")
            except ValueError:
                errors.append(f"PORT must be a valid integer, got '{val_clean}'.")

        elif key_clean in ("SERVICE_URL", "RENDER_DEPLOY_HOOK_URL"):
            if val_clean and not val_clean.startswith(("http://", "https://")):
                errors.append(f"{key_clean} must be a valid HTTP or HTTPS URL, got '{val_clean}'.")

        elif key_clean == "DATABASE_URL":
            if val_clean and not re.match(r"^(sqlite|postgresql|postgres|mysql|mariadb):\/\/", val_clean):
                warnings.append(f"DATABASE_URL should specify a recognized protocol (sqlite://, postgresql://, etc.), got '{val_clean}'.")
            if "sqlite" in val_clean:
                warnings.append("DATABASE_URL uses SQLite. For multi-instance scaling, a managed PostgreSQL database is recommended.")

        elif key_clean == "GITHUB_REPO" and val_clean and not re.match(r"^[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+$", val_clean):
            errors.append(f"GITHUB_REPO must be in 'owner/repo' format, got '{val_clean}'.")

        # Mask secrets in sanitized output
        if any(sec in key_clean for sec in ("TOKEN", "SECRET", "KEY", "HOOK", "PASSWORD")):
            sanitized[key_clean] = mask_secret(val_clean)
        else:
            sanitized[key_clean] = val_clean

    is_valid = len(errors) == 0
    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "sanitized_variables": sanitized,
        "variables_evaluated": len(env_vars),
    }
