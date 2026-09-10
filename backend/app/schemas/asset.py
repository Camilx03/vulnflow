import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress

from app.models.asset import AssetEnvironment


class AssetCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    ip_address: IPvAnyAddress | None = None
    operating_system: str | None = Field(default=None, max_length=120)
    environment: AssetEnvironment = AssetEnvironment.DEVELOPMENT
    description: str | None = None


class AssetUpdate(BaseModel):
    hostname: str | None = Field(default=None, min_length=1, max_length=255)
    ip_address: IPvAnyAddress | None = None
    operating_system: str | None = Field(default=None, max_length=120)
    environment: AssetEnvironment | None = None
    description: str | None = None
    

class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    hostname: str
    ip_address: str | None
    operating_system: str | None
    environment: AssetEnvironment
    description: str | None
    created_at: datetime
    updated_at: datetime