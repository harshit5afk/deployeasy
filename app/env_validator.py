"""Environment Variable Validator for DeployEasy deployments.

Prevents production deployment crashes caused by missing, malformed,
or placeholder configuration and exposed secrets.
"""
import re
from typing import Any

SCHEMA_RULES: dict[str, dict[str, Any]] = {
    "PORT": {"type": "integer", "min": 1, "max": 65535, "required": False, "default": "8080"},
    "APP_VERSION": {"type": "version", "required": False, "default": "1.0.0"},
    "DATABASE_URL": {"type": "database_url", "required": False, "default": "sqlite:///./deployeasy.db"},
    "SERVICE_URL": {"type": "url", "required": False},
    "RENDER_DEPLOY_HOOK_URL": {"type": "secret_url", "required": False},
    "GITHUB_REPO": {"type": "repo", "required": False},
    "GITHUB_TOKEN": {"type": "secret", "required": False},
}

SENSITIVE_KEY_PATTERNS = ("TOKEN", "SECRET", "KEY", "HOOK", "PASSWORD", "PASS", "AUTH", "CREDENTIAL", "DATABASE_URL")


def mask_database_url(url: str) -> str:
    """Mask credentials in database connection strings (e.g., postgres://user:***@host:5432/db)."""
    if not url:
        return ""
    # Matches proto://user:password@host
    return re.sub(r"(://[^:]+):([^@]+)@", r"\1:***@", url)


def mask_secret(value: str) -> str:
    """Safely mask secret strings or database credentials for UI/API display."""
    if not value:
        return ""
    if "://" in value and "@" in value:
        return mask_database_url(value)
    if len(value) <= 8:
        return "********"
    return value[:4] + "..." + value[-4:]


def is_sensitive_key(key: str) -> bool:
    """Check if variable name implies sensitive credentials."""
    upper = key.upper()
    return any(p in upper for p in SENSITIVE_KEY_PATTERNS)


def sanitize_message_value(key: str, val: str) -> str:
    """Return a masked representation of value if key is sensitive, to prevent log/warning leakage."""
    if is_sensitive_key(key):
        return mask_secret(val)
    return val


def validate_environment(env_vars: dict[str, str]) -> dict[str, Any]:
    """Validate a dictionary of environment variables against production criteria and SCHEMA_RULES."""
    errors: list[str] = []
    warnings: list[str] = []
    sanitized: dict[str, str] = {}

    for key, val in env_vars.items():
        key_clean = key.strip()
        val_clean = str(val).strip() if val is not None else ""
        safe_val_display = sanitize_message_value(key_clean, val_clean)

        # Validate variable name syntax
        if not re.match(r"^[A-Z0-9_]+$", key_clean):
            warnings.append(f"Environment variable '{key_clean}' should be UPPERCASE with underscores.")

        # Check placeholder secrets
        placeholders = ["your-username", "your-secret", "placeholder", "changeme", "secret", "xxx", "123456", "todo"]
        if any(p in val_clean.lower() for p in placeholders) and len(val_clean) < 35:
            warnings.append(f"Variable '{key_clean}' appears to contain a template placeholder value ('{safe_val_display}').")

        # Specific type validations based on SCHEMA_RULES and key names
        rule = SCHEMA_RULES.get(key_clean)

        if key_clean == "PORT" or (rule and rule.get("type") == "integer"):
            try:
                port_num = int(val_clean)
                min_val = rule.get("min", 1) if rule else 1
                max_val = rule.get("max", 65535) if rule else 65535
                if port_num < min_val or port_num > max_val:
                    errors.append(f"PORT must be an integer between {min_val} and {max_val}, got {port_num}.")
            except ValueError:
                errors.append(f"PORT must be a valid integer, got '{safe_val_display}'.")

        elif key_clean in ("SERVICE_URL", "RENDER_DEPLOY_HOOK_URL") or (rule and rule.get("type") in ("url", "secret_url")):
            if val_clean and not val_clean.startswith(("http://", "https://")):
                errors.append(f"{key_clean} must be a valid HTTP or HTTPS URL, got '{safe_val_display}'.")

        elif key_clean == "DATABASE_URL" or (rule and rule.get("type") == "database_url"):
            if val_clean and not re.match(r"^(sqlite|postgresql|postgres|mysql|mariadb):\/\/", val_clean):
                warnings.append(f"DATABASE_URL should specify a recognized protocol (sqlite://, postgresql://, etc.), got '{safe_val_display}'.")
            if "sqlite" in val_clean:
                warnings.append("DATABASE_URL uses SQLite. For multi-instance scaling, a managed PostgreSQL database is recommended.")

        elif (key_clean == "GITHUB_REPO" or (rule and rule.get("type") == "repo")) and val_clean and not re.match(r"^[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+$", val_clean):
            errors.append(f"GITHUB_REPO must be in 'owner/repo' format, got '{safe_val_display}'.")

        # Mask secrets in sanitized output
        if is_sensitive_key(key_clean):
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
