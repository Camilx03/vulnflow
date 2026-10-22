
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserAdminUpdate, UserResponse
from app.services.audit import create_audit_log


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "",
    response_model=list[UserResponse],
)
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.ANALYST)
    ),
):
    users = db.scalars(
        select(User)
        .where(User.is_active.is_(True))
        .order_by(User.full_name)
    ).all()

    return users



@router.patch(
    "/{user_id}",
    response_model=UserResponse,
)
def update_user(
    user_id: uuid.UUID,
    changes: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
):
    db.execute(
        text("SELECT pg_advisory_xact_lock(761152, 1)")
    )

    db.refresh(current_user, with_for_update=True)

    if (
        not current_user.is_active
        or current_user.role != UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify your own account",
        )

    removes_active_admin = (
        user.role == UserRole.ADMIN
        and user.is_active
        and (
            (
                changes.role is not None
                and changes.role != UserRole.ADMIN
            )
            or changes.is_active is False
        )
    )

    if removes_active_admin:
        active_admins = db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.role == UserRole.ADMIN,
                User.is_active.is_(True),
            )
        )

        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last active administrator",
            )

    updated_fields = {}

    if changes.role is not None and changes.role != user.role:
        updated_fields["role"] = {
            "old": user.role.value,
            "new": changes.role.value,
        }
        user.role = changes.role

    if (
        changes.is_active is not None
        and changes.is_active != user.is_active
    ):
        updated_fields["is_active"] = {
            "old": user.is_active,
            "new": changes.is_active,
        }
        user.is_active = changes.is_active

    if updated_fields:
        create_audit_log(
            db=db,
            user_id=current_user.id,
            action="UPDATE",
            entity_type="user",
            entity_id=user.id,
            changes=updated_fields,
        )

        db.commit()
        db.refresh(user)

    return user
