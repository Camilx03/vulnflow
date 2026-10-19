
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID
    changes: dict[str, Any] | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AuditLogResponse]
