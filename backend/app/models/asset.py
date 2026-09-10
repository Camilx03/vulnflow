import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AssetEnvironment(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TEST = "test"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    hostname: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    operating_system: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    environment: Mapped[AssetEnvironment] = mapped_column(
        SQLEnum(
            AssetEnvironment,
            name="asset_environment",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=AssetEnvironment.DEVELOPMENT,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )