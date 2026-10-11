"""Best-effort security audit logging using the existing AuditLog table."""
import logging
from uuid import UUID

from sqlmodel import Session

from models import AuditLog

logger = logging.getLogger(__name__)


def log_event(
    session: Session,
    user_id: UUID | None,
    action: str,
    ip_address: str | None = None,
) -> None:
    """Persist a security event without allowing audit failure to break a request."""
    try:
        session.add(AuditLog(user_id=user_id, action=action, ip_address=ip_address))
        session.commit()
    except Exception:
        logger.exception("Could not persist security audit event: %s", action)
        try:
            session.rollback()
        except Exception:
            logger.exception("Could not roll back failed audit transaction")
