
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vulnerability_id: uuid.UUID
    user_id: uuid.UUID | None
    content: str
    created_at: datetime
    updated_at: datetime
