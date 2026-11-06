"""All settings come from environment variables. No secrets in code."""
import os

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
GIT_SHA = os.getenv("GIT_SHA", "dev")
GITHUB_REPO = os.getenv("GITHUB_REPO", "harshit5afk/deployeasy")    # "owner/name", for the dashboard
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Personal Access Token or fine-grained token
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID", "")
GITHUB_APP_PRIVATE_KEY = os.getenv("GITHUB_APP_PRIVATE_KEY", "")
GITHUB_APP_INSTALLATION_ID = os.getenv("GITHUB_APP_INSTALLATION_ID", "")

# Normalize Postgres connection string for SQLAlchemy 2.x
_default_db = "sqlite:///./test_deployeasy.db" if os.getenv("TESTING") == "1" else "sqlite:///./deployeasy.db"
_raw_db_url = os.getenv("DATABASE_URL", _default_db)
if _raw_db_url.startswith("postgres://"):
    DATABASE_URL = _raw_db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif _raw_db_url.startswith("postgresql://") and not _raw_db_url.startswith("postgresql+"):
    DATABASE_URL = _raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = _raw_db_url

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
SERVICE_URL = os.getenv("SERVICE_URL", "")
RENDER_DEPLOY_HOOK_URL = os.getenv("RENDER_DEPLOY_HOOK_URL", "")

# Security and Demo Flags
DEPLOYEASY_DEMO_MODE = os.getenv("DEPLOYEASY_DEMO_MODE", "false").lower() in ("true", "1", "yes")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
