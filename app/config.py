"""All settings come from environment variables. No secrets in code."""
import os

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
GIT_SHA = os.getenv("GIT_SHA", "dev")
GITHUB_REPO = os.getenv("GITHUB_REPO", "harshit5afk/deployeasy")    # "owner/name", for the dashboard
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # optional, read-only
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./deployeasy.db")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
SERVICE_URL = os.getenv("SERVICE_URL", "")
RENDER_DEPLOY_HOOK_URL = os.getenv("RENDER_DEPLOY_HOOK_URL", "")
