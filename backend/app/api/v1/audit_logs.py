
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.audit_log import AuditLogListResponse


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


@router.get(
    "",
    response_model=AuditLogListResponse,
)
def list_audit_logs(
    action: str | None = Query(default=None, pattern="^(CREATE|UPDATE|DELETE)$"),
    entity_type: str | None = Query(
        default=None,
        pattern="^(asset|vulnerability|comment)$",
    ),
    entity_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
):
    filters = []

    if action is not None:
        filters.append(AuditLog.action == action)

    if entity_type is not None:
        filters.append(AuditLog.entity_type == entity_type)

    if entity_id is not None:
        filters.append(AuditLog.entity_id == entity_id)

    if user_id is not None:
        filters.append(AuditLog.user_id == user_id)

    if date_from is not None:
        filters.append(AuditLog.created_at >= date_from)

    if date_to is not None:
        filters.append(AuditLog.created_at <= date_to)

    total = db.scalar(
        select(func.count(AuditLog.id)).where(*filters)
    ) or 0

    query = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    audit_logs = db.scalars(query).all()

    return AuditLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=audit_logs,
    )
