"""
Pydantic schemas for the authentication API.

JWTs are deliberately NOT represented in these response schemas.
Authentication tokens are delivered exclusively through httpOnly cookies.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuthCredentials(BaseModel):
    """
    Common email/password payload.

    The backend performs the authoritative validation.
    """

    email: str = Field(
        min_length=3,
        max_length=320,
    )

    password: str = Field(
        min_length=8,
        max_length=256,
    )


class SignupRequest(AuthCredentials):
    """Request body for POST /auth/signup."""


class LoginRequest(AuthCredentials):
    """Request body for POST /auth/login."""


class UserResponse(BaseModel):
    """
    Public authenticated-user representation.

    Never contains password_hash or JWTs.
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: str
    role: str


class AuthMessage(BaseModel):
    """
    Generic non-sensitive authentication response.

    Tokens are never returned here.
    """

    message: str