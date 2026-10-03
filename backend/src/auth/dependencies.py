"""
FastAPI authentication dependencies.

M1 moves the real get_current_user implementation here.

backend/src/routes.py will re-export this function so existing imports such as:

    from routes import get_current_user

continue to work without changing M2/M3/Wave B code.
"""

import secrets
import uuid

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from sqlmodel import Session, select

from auth.jwt import decode_token, generate_csrf_token
from db import get_session
from models import User

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def _unauthorized() -> HTTPException:
    """Return the standard authentication failure."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    """
    Authenticate the request using the httpOnly access_token cookie.

    Flow:

        access_token cookie
              ↓
        JWT validation
              ↓
        user_id from sub
              ↓
        User database row
              ↓
        authenticated User
    """
    token = request.cookies.get(ACCESS_COOKIE_NAME)

    if not token:
        raise _unauthorized()

    try:
        payload = decode_token(
            token,
            expected_type="access",
        )
    except jwt.InvalidTokenError:
        raise _unauthorized()

    raw_user_id = payload.get("sub")

    if not raw_user_id:
        raise _unauthorized()

    try:
        user_id = (
            uuid.UUID(raw_user_id)
            if isinstance(raw_user_id, str)
            else raw_user_id
        )
    except ValueError:
        raise _unauthorized()

    user = session.exec(
        select(User).where(User.user_id == user_id)
    ).first()

    if user is None:
        raise _unauthorized()

    return user


def ensure_csrf_cookie(request: Request, response: Response) -> None:
    """
    Ensure a CSRF cookie exists.

    The CSRF cookie is intentionally NOT httpOnly because the frontend must
    read it and copy the value into X-CSRF-Token.
    """
    existing = request.cookies.get(CSRF_COOKIE_NAME)

    if existing:
        return

    token = generate_csrf_token()

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        secure=False,
        samesite="strict",
        path="/",
    )


def require_csrf(request: Request) -> None:
    """
    Double-submit CSRF protection for state-changing requests.

    The browser sends:
        csrf_token cookie

    The frontend must additionally send:
        X-CSRF-Token header

    Both values must match exactly.
    """
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if not cookie_token or not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed.",
        )

    if not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed.",
        )