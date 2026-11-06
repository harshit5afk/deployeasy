"""Authentication, password security, session management, CSRF, and authorization for DeployEasy."""
import hashlib
import hmac
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from . import config
from .db import Project, User, UserSession, get_db

log = logging.getLogger("deployeasy")

SESSION_COOKIE_NAME = "deployeasy_session"
CSRF_COOKIE_NAME = "deployeasy_csrf"
SESSION_LIFETIME_DAYS = 7

# In-memory sliding window rate limiter for login/registration: {ip_address: [timestamps]}
_AUTH_RATE_LIMITS: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_ATTEMPTS = 5


def check_auth_rate_limit(request: Request) -> None:
    """Enforce rate limiting on authentication attempts (max 5 attempts per minute per IP)."""
    client_ip = (request.client.host if request.client else "127.0.0.1").strip()
    now = time.time()
    attempts = _AUTH_RATE_LIMITS.get(client_ip, [])
    # Keep only attempts in current window
    valid_attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW_SECONDS]

    if len(valid_attempts) >= RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again in 60 seconds.",
        )

    valid_attempts.append(now)
    _AUTH_RATE_LIMITS[client_ip] = valid_attempts


def reset_auth_rate_limits() -> None:
    """Helper to reset rate limits during testing."""
    _AUTH_RATE_LIMITS.clear()


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


def create_user_session(db: Session, user: User) -> UserSession:
    """Generate and persist a cryptographically secure session in the database."""
    session_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(days=SESSION_LIFETIME_DAYS)

    session_record = UserSession(
        session_token=session_token,
        csrf_token=csrf_token,
        user_id=user.id,
        expires_at=expires_at,
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return session_record


def set_session_cookies(response: Response, session: UserSession) -> None:
    """Set secure HTTP-only session cookie and companion CSRF cookie."""
    # HttpOnly session cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.session_token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=SESSION_LIFETIME_DAYS * 24 * 3600,
        path="/",
    )
    # Accessible CSRF cookie for client header inclusion
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=session.csrf_token,
        httponly=False,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=SESSION_LIFETIME_DAYS * 24 * 3600,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    """Clear session and CSRF cookies on logout."""
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


def extract_token_from_request(request: Request) -> str | None:
    """Extract session token from HttpOnly cookie or Authorization Bearer header."""
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return auth_header.strip()

    return None


def get_current_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> tuple[UserSession, User]:
    """Retrieve and validate the active database session and user."""
    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_record = (
        db.query(UserSession)
        .filter(
            UserSession.session_token == token,
            UserSession.expires_at > datetime.now(UTC),
        )
        .first()
    )

    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again.",
        )

    user = db.query(User).filter(User.id == session_record.user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or disabled.",
        )

    return session_record, user


def get_current_user(
    session_and_user: Annotated[tuple[UserSession, User], Depends(get_current_session)],
) -> User:
    """Dependency that returns the authenticated User object."""
    return session_and_user[1]


def verify_csrf_protection(
    request: Request,
    session_and_user: Annotated[tuple[UserSession, User], Depends(get_current_session)],
    x_csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    """Validate CSRF token on state-changing requests when authenticated via cookies."""
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        session_record, _ = session_and_user
        # If authenticated via cookie, CSRF header is required
        if request.cookies.get(SESSION_COOKIE_NAME) and (
            not x_csrf_token or not hmac.compare_digest(x_csrf_token.strip(), session_record.csrf_token)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing or invalid. Include the X-CSRF-Token header.",
            )


def get_authorized_project(
    project_id: int,
    user: User,
    db: Session,
    require_write: bool = False,
) -> Project:
    """Enforce strict owner-scoped read and write authorization on project assets."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Admins have full access
    if user.role == "admin":
        return project

    # Demo accounts are strictly read-only
    if require_write and user.role == "demo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo account has read-only access. Sign up as a developer to perform deployments or modifications.",
        )

    # Check project ownership
    if project.owner_id is not None and project.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to access this project.",
        )

    return project
