# backend/src/auth/routes.py
import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from auth.dependencies import get_current_user
from auth.hashing import hash_password, verify_password
from auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_csrf_token,
)
from auth.schemas import LoginRequest, SignupRequest, UserResponse
from db import get_session
from models import User
from rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_ACCESS_TOKEN_KEY = "access_token"
COOKIE_REFRESH_TOKEN_KEY = "refresh_token"
COOKIE_CSRF_TOKEN_KEY = "csrf_token"
HEADER_CSRF_TOKEN_KEY = "X-CSRF-Token"


def _verify_csrf(
    x_csrf_token: Annotated[
        str | None,
        Header(alias=HEADER_CSRF_TOKEN_KEY),
    ] = None,
    csrf_token: Annotated[
        str | None,
        Cookie(alias=COOKIE_CSRF_TOKEN_KEY),
    ] = None,
) -> None:
    if not x_csrf_token or not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing.",
        )

    if not verify_csrf_token(x_csrf_token, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed.",
        )


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    response.set_cookie(
        key=COOKIE_ACCESS_TOKEN_KEY,
        value=access_token,
        httponly=True,
    )

    response.set_cookie(
        key=COOKIE_REFRESH_TOKEN_KEY,
        value=refresh_token,
        httponly=True,
        path="/auth",
    )


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
def signup(
    request: Request,
    payload: SignupRequest,
    response: Response,
    session: Session = Depends(get_session),
    _: None = Depends(_verify_csrf),
) -> UserResponse:
    existing_user = session.exec(
        select(User).where(User.email == payload.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="VIEWER",
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    acc_token = create_access_token(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
    )

    ref_token = create_refresh_token(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
    )

    _set_auth_cookies(response, acc_token, ref_token)

    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
    )


@router.post(
    "/login",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
    _: None = Depends(_verify_csrf),
) -> UserResponse:
    generic_auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )

    user = session.exec(
        select(User).where(User.email == payload.email)
    ).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise generic_auth_error

    acc_token = create_access_token(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
    )

    ref_token = create_refresh_token(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
    )

    _set_auth_cookies(response, acc_token, ref_token)

    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
    )


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
)
def refresh(
    response: Response,
    refresh_token: Annotated[
        str | None,
        Cookie(alias=COOKIE_REFRESH_TOKEN_KEY),
    ] = None,
    _: None = Depends(_verify_csrf),
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing.",
        )

    try:
        payload = decode_token(
            refresh_token,
            expected_type="refresh",
        )
        new_refresh_token = rotate_refresh_token(refresh_token)

        user_id = payload["sub"]
        email = str(payload.get("email", ""))
        role = str(payload.get("role", ""))

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    new_access_token = create_access_token(
        user_id=user_id,
        email=email,
        role=role,
    )

    _set_auth_cookies(response, new_access_token, new_refresh_token)

    return {"message": "Token refreshed"}


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    response: Response,
    refresh_token: Annotated[
        str | None,
        Cookie(alias=COOKIE_REFRESH_TOKEN_KEY),
    ] = None,
    _: None = Depends(_verify_csrf),
):
    if refresh_token:
        revoke_refresh_token(refresh_token)

    response.delete_cookie(key=COOKIE_ACCESS_TOKEN_KEY)
    response.delete_cookie(key=COOKIE_REFRESH_TOKEN_KEY, path="/auth")

    return None


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
def get_me(
    request: Request,
    response: Response,
    access_token: Annotated[
        str | None,
        Cookie(alias=COOKIE_ACCESS_TOKEN_KEY),
    ] = None,
    session: Session = Depends(get_session),
):
    csrf_token = generate_csrf_token()

    if not access_token:
        res = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Not authenticated."},
        )
        res.set_cookie(
            key=COOKIE_CSRF_TOKEN_KEY,
            value=csrf_token,
            httponly=False,
        )
        return res

    response.set_cookie(
        key=COOKIE_CSRF_TOKEN_KEY,
        value=csrf_token,
        httponly=False,
    )

    user = get_current_user(
        request=request,
        session=session,
    )

    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
    )