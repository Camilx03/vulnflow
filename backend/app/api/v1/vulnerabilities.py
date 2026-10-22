import uuid


from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.asset import Asset
from app.models.user import User, UserRole
from app.services.audit import create_audit_log
from app.models.vulnerability import (
    Vulnerability,
    VulnerabilitySeverity,
    VulnerabilityStatus,
)
from app.schemas.vulnerability import (
    VulnerabilityCreate,
    VulnerabilityResponse,
    VulnerabilityUpdate,
)


router = APIRouter(
    prefix="/vulnerabilities",
    tags=["Vulnerabilities"],
)


@router.post(
    "",
    response_model=VulnerabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vulnerability(
    vulnerability_data: VulnerabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.ANALYST,
        )
    ),
):
    asset = db.get(
        Asset,
        vulnerability_data.asset_id,
    )

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    if vulnerability_data.assigned_user_id is not None:
        assigned_user = db.get(
            User,
            vulnerability_data.assigned_user_id,
            with_for_update=True,
            populate_existing=True,
        )

        if assigned_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )

        if not assigned_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign vulnerability to an inactive user",
            )

    vulnerability = Vulnerability(
        cve=(
            vulnerability_data.cve.upper()
            if vulnerability_data.cve
            else None
        ),
        title=vulnerability_data.title.strip(),
        description=(
            vulnerability_data.description.strip()
            if vulnerability_data.description
            else None
        ),
        severity=vulnerability_data.severity,
        cvss=vulnerability_data.cvss,
        asset_id=vulnerability_data.asset_id,
        assigned_user_id=vulnerability_data.assigned_user_id,
    )


    db.add(vulnerability)
    db.flush()

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="CREATE",
        entity_type="vulnerability",
        entity_id=vulnerability.id,
        changes={
            "title": vulnerability.title,
            "severity": vulnerability.severity,
            "cvss": vulnerability.cvss,
            "status": vulnerability.status,
            "asset_id": vulnerability.asset_id,
            "assigned_user_id": vulnerability.assigned_user_id,
        },
    )

    db.commit()
    db.refresh(vulnerability)

    return vulnerability


@router.get(
    "",
    response_model=list[VulnerabilityResponse],
)
def list_vulnerabilities(
    severity: VulnerabilitySeverity | None = None,
    vulnerability_status: VulnerabilityStatus | None = None,
    asset_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Vulnerability)

    if severity is not None:
        query = query.where(
            Vulnerability.severity == severity
        )

    if vulnerability_status is not None:
        query = query.where(
            Vulnerability.status == vulnerability_status
        )

    if asset_id is not None:
        query = query.where(
            Vulnerability.asset_id == asset_id
        )

    query = query.order_by(
        Vulnerability.created_at.desc()
    )

    return db.scalars(query).all()


@router.get(
    "/{vulnerability_id}",
    response_model=VulnerabilityResponse,
)
def get_vulnerability(
    vulnerability_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vulnerability = db.get(Vulnerability, vulnerability_id)

    if vulnerability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability not found",
        )

    return vulnerability


@router.patch(
    "/{vulnerability_id}",
    response_model=VulnerabilityResponse,
)
def update_vulnerability(
    vulnerability_id: uuid.UUID,
    vulnerability_data: VulnerabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.ANALYST)
    ),
):
    vulnerability = db.get(Vulnerability, vulnerability_id)

    if vulnerability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability not found",
        )

    update_data = vulnerability_data.model_dump(exclude_unset=True)

    if "asset_id" in update_data:
        asset_id = update_data["asset_id"]

        if asset_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Asset cannot be null",
            )

        if db.get(Asset, asset_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found",
            )

    if "assigned_user_id" in update_data:
        assigned_user_id = update_data["assigned_user_id"]

        if assigned_user_id is not None:
            assigned_user = db.get(
                User,
                assigned_user_id,
                with_for_update=True,
                populate_existing=True,
            )

            if assigned_user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assigned user not found",
                )

            if not assigned_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign vulnerability to an inactive user",
                )

    for field in ("title", "severity", "status"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field} cannot be null",
            )

    if "title" in update_data:
        title = update_data["title"].strip()

        if not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Title cannot be empty",
            )

        update_data["title"] = title

    if "cve" in update_data and update_data["cve"] is not None:
        update_data["cve"] = update_data["cve"].upper()

    if "description" in update_data and update_data["description"] is not None:
        update_data["description"] = update_data["description"].strip()


    changes = {}

    for field, value in update_data.items():
        old_value = getattr(vulnerability, field)

        if old_value != value:
            changes[field] = {
                "old": old_value,
                "new": value,
            }

            setattr(vulnerability, field, value)

    if changes:
        create_audit_log(
            db=db,
            user_id=current_user.id,
            action="UPDATE",
            entity_type="vulnerability",
            entity_id=vulnerability.id,
            changes=changes,
        )

        db.commit()
        db.refresh(vulnerability)

    return vulnerability


@router.delete(
    "/{vulnerability_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_vulnerability(
    vulnerability_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.ANALYST)
    ),
) -> Response:
    vulnerability = db.get(Vulnerability, vulnerability_id)

    if vulnerability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability not found",
        )


    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="DELETE",
        entity_type="vulnerability",
        entity_id=vulnerability.id,
        changes={
            "cve": vulnerability.cve,
            "title": vulnerability.title,
            "severity": vulnerability.severity,
            "cvss": vulnerability.cvss,
            "status": vulnerability.status,
            "asset_id": vulnerability.asset_id,
            "assigned_user_id": vulnerability.assigned_user_id,
        },
    )

    db.delete(vulnerability)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
