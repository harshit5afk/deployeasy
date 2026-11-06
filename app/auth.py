"""Authentication, password security, session management, and authorization for DeployEasy."""
import hashlib
import hmac
import secrets
import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .db import Project, User, get_db

# Active session token store: token -> {"user_id": int, "role": str, "expires_at": float}
_ACTIVE_SESSIONS: dict[str, dict] = {}
SESSION_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with cryptographic salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${key.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify password against stored salt$key hash."""
    try:
        salt, key_hex = stored_hash.split("$", 1)
        key = bytes.fromhex(key_hex)
        computed = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return hmac.compare_digest(key, computed)
    except (ValueError, TypeError, AttributeError):
        return False


def create_session(user: User) -> str:
    """Generate a cryptographically secure session token."""
    token = secrets.token_urlsafe(32)
    _ACTIVE_SESSIONS[token] = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }
    return token


def revoke_session(token: str) -> None:
    """Invalidate an active session token."""
    _ACTIVE_SESSIONS.pop(token, None)


def get_token_payload(token: str) -> dict | None:
    """Validate token and check expiration."""
    if not token:
        return None
    session = _ACTIVE_SESSIONS.get(token)
    if not session:
        return None
    if time.time() > session["expires_at"]:
        _ACTIVE_SESSIONS.pop(token, None)
        return None
    return session


def extract_bearer_token(authorization: str | None = Header(None, alias="Authorization")) -> str | None:
    """Extract Bearer token from HTTP Authorization header."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return authorization.strip()


def get_current_user(
    token: Annotated[str | None, Depends(extract_bearer_token)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Enforce authentication: raises 401 if token is missing, invalid, or expired."""
    payload = get_token_payload(token) if token else None
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or disabled.",
        )
    return user


def get_optional_user(
    token: Annotated[str | None, Depends(extract_bearer_token)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Optional authentication for public read endpoints with contextual user permissions."""
    if not token:
        return None
    payload = get_token_payload(token)
    if not payload:
        return None
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if user and user.is_active:
        return user
    return None


def verify_project_permission(project: Project, user: User, action: str = "mutate") -> None:
    """Enforce project ownership and prevent demo accounts from mutating production assets."""
    if action == "read":
        return

    # Demo accounts are strictly read-only
    if user.role == "demo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo account has read-only access. Sign up or log in as a developer to trigger deployments or rollbacks.",
        )

    # Admins have full access
    if user.role == "admin":
        return

    # Developers can modify their own projects or unassigned sample projects
    if project.owner_id is not None and project.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this project.",
        )
