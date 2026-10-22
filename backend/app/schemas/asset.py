
import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    field_validator,
)

from app.models.asset import AssetEnvironment


class AssetCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    ip_address: IPvAnyAddress | None = None
    operating_system: str | None = Field(default=None, max_length=120)
    environment: AssetEnvironment = AssetEnvironment.DEVELOPMENT
    description: str | None = None

    @field_validator("hostname", mode="before")
    @classmethod
    def normalize_hostname(cls, value):
        if isinstance(value, str):
            return value.strip().lower()

        return value


class AssetUpdate(BaseModel):
    hostname: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    ip_address: IPvAnyAddress | None = None
    operating_system: str | None = Field(default=None, max_length=120)
    environment: AssetEnvironment | None = None
    description: str | None = None

    @field_validator("hostname", mode="before")
    @classmethod
    def validate_hostname(cls, value):
        if value is None:
            raise ValueError("Hostname cannot be null")

        if isinstance(value, str):
            return value.strip().lower()

        return value

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, value):
        if value is None:
            raise ValueError("Environment cannot be null")

        return value


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
