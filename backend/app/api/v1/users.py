from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse


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
    current_user: User = Depends(get_current_user),
):
    users = db.scalars(
        select(User)
        .where(User.is_active.is_(True))
        .order_by(User.full_name)
    ).all()

    return users