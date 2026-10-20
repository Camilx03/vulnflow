from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.asset import Asset
from app.models.user import User, UserRole
from app.models.vulnerability import Vulnerability
from app.schemas.asset import AssetCreate, AssetResponse, AssetUpdate
from app.services.audit import create_audit_log
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
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.ANALYST,
        )
    ),
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
    db.flush()

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="CREATE",
        entity_type="asset",
        entity_id=asset.id,
        changes={
            "hostname": asset.hostname,
            "ip_address": asset.ip_address,
            "operating_system": asset.operating_system,
            "environment": asset.environment,
            "description": asset.description,
        },
    )

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
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.ANALYST,
        )
    ),
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


    original_values = db.get(
        Asset,
        asset_id,
    )

    changes = {}

    if asset in db.dirty:
        from sqlalchemy import inspect

        state = inspect(asset)

        for field in (
            "hostname",
            "ip_address",
            "operating_system",
            "environment",
            "description",
        ):
            history = state.attrs[field].history

            if history.has_changes():
                changes[field] = {
                    "old": history.deleted[0] if history.deleted else None,
                    "new": getattr(asset, field),
                }

    if changes:
        create_audit_log(
            db=db,
            user_id=current_user.id,
            action="UPDATE",
            entity_type="asset",
            entity_id=asset.id,
            changes=changes,
        )


    db.commit()
    db.refresh(asset)

    return asset


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.ANALYST,
        )
    ),
) -> Response:
    asset = db.get(Asset, asset_id)

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )
    associated_vulnerability = db.scalar(
        select(Vulnerability.id)
        .where(Vulnerability.asset_id == asset_id)
        .limit(1)
    )

    if associated_vulnerability is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete asset with associated vulnerabilities",
        )


    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="DELETE",
        entity_type="asset",
        entity_id=asset.id,
        changes={
            "hostname": asset.hostname,
            "ip_address": asset.ip_address,
            "operating_system": asset.operating_system,
            "environment": asset.environment,
            "description": asset.description,
        },
    )


    try:
        db.delete(asset)
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        original_error = exc.orig

        sqlstate = (
            getattr(original_error, "sqlstate", None)
            or getattr(original_error, "pgcode", None)
        )

        diagnostic = getattr(original_error, "diag", None)
        constraint_name = getattr(
            diagnostic,
            "constraint_name",
            None,
        )

        if (
            sqlstate == "23503"
            and constraint_name == "vulnerabilities_asset_id_fkey"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete asset with associated vulnerabilities",
            ) from None

        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)
