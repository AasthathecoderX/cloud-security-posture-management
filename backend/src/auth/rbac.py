"""Role-based authorization dependencies for FastAPI endpoints."""
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from auth.dependencies import get_current_user
from auth.audit import log_event
from db import get_session
from models import User, UserRole


def require_role(*roles: UserRole) -> Callable:
    """Return a dependency that permits only the supplied roles.

    Usage: dependencies=[Depends(require_role(UserRole.ADMIN))].
    Role denial is 403; resource-ownership denial remains 404.
    """
    allowed = frozenset(roles)

    def role_dependency(
        request: Request,
        user: User = Depends(get_current_user),
        session: Session = Depends(get_session),
    ) -> User:
        if not allowed or user.role not in allowed:
            log_event(
                session=session,
                user_id=user.user_id,
                action="role_check_denied",
                ip_address=request.client.host if request.client else None,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return user

    return role_dependency
