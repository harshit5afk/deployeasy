"""All settings come from environment variables. No secrets in code."""
import os

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
GIT_SHA = os.getenv("GIT_SHA", "dev")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")    # "owner/name", for the dashboard
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # optional, read-only
