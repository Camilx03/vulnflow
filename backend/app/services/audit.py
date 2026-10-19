
import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def serialize_value(value):
    if isinstance(value, Enum):
        return value.value

    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: serialize_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]

    return value


def create_audit_log(
    db: Session,
    user_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    changes: dict | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=serialize_value(changes),
    )

    db.add(audit_log)

    return audit_log
