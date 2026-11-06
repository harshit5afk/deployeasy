"""Pytest configuration and test isolation fixtures."""
import os

# Ensure test isolation before any app module imports
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///./test_deployeasy.db"

import pytest

from app.auth import reset_auth_rate_limits
from app.db import init_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure clean test database for the test session."""
    init_db()
    yield
    # Cleanup test sqlite database file after test session
    for path in ("test_deployeasy.db", "test_deployeasy.db-journal"):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


@pytest.fixture(autouse=True)
def reset_rate_limits_and_state():
    """Reset rate limiter state before every individual test."""
    reset_auth_rate_limits()
    yield
    reset_auth_rate_limits()
