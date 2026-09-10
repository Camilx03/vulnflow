from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.asset import Asset
from app.models.user import User
from app.schemas.asset import AssetCreate, AssetResponse, AssetUpdate
import uuid

router = APIRouter(
    prefix="/assets",
    tags=["Assets"],
)


@router.post(
    "",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_asset(
    asset_data: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hostname = asset_data.hostname.strip().lower()

    existing_asset = db.scalar(
        select(Asset).where(Asset.hostname == hostname)
    )

    if existing_asset:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An asset with this hostname already exists",
        )

    asset = Asset(
        hostname=hostname,
        ip_address=(
            str(asset_data.ip_address)
            if asset_data.ip_address is not None
            else None
        ),
        operating_system=(
            asset_data.operating_system.strip()
            if asset_data.operating_system
            else None
        ),
        environment=asset_data.environment,
        description=(
            asset_data.description.strip()
            if asset_data.description
            else None
        ),
    )

    db.add(asset)
    db.commit()
    db.refresh(asset)

    return asset


@router.get(
    "",
    response_model=list[AssetResponse],
)
def list_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assets = db.scalars(
        select(Asset).order_by(Asset.created_at.desc())
    ).all()

    return assets


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
)
def get_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.get(Asset, asset_id)

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    return asset


@router.patch(
    "/{asset_id}",
    response_model=AssetResponse,
)
def update_asset(
    asset_id: uuid.UUID,
    asset_data: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.get(Asset, asset_id)

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    update_data = asset_data.model_dump(exclude_unset=True)

    if "hostname" in update_data:
        hostname = update_data["hostname"].strip().lower()

        existing_asset = db.scalar(
            select(Asset).where(
                Asset.hostname == hostname,
                Asset.id != asset_id,
            )
        )

        if existing_asset:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An asset with this hostname already exists",
            )

        asset.hostname = hostname

    if "ip_address" in update_data:
        asset.ip_address = (
            str(update_data["ip_address"])
            if update_data["ip_address"] is not None
            else None
        )

    if "operating_system" in update_data:
        asset.operating_system = (
            update_data["operating_system"].strip()
            if update_data["operating_system"]
            else None
        )

    if "environment" in update_data:
        asset.environment = update_data["environment"]

    if "description" in update_data:
        asset.description = (
            update_data["description"].strip()
            if update_data["description"]
            else None
        )

    db.commit()
    db.refresh(asset)

    return asset