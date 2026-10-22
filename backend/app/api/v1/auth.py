from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.api.dependencies import get_current_user
from app.services.login_rate_limit import (
    consume_login_attempt,
    consume_registration_attempt,
    reset_account_login_attempts,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)


def register_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    ip_address = (
        request.client.host
        if request.client is not None
        else "unknown"
    )

    retry_after = consume_registration_attempt(
        db,
        ip_address,
    )

    if retry_after > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Try again later.",
            headers={
                "Retry-After": str(retry_after),
            },
        )

    email = str(user_data.email).lower()

    statement = (
        insert(User)
        .values(
            email=email,
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name.strip(),
        )
        .on_conflict_do_nothing(
            index_elements=[User.email],
        )
        .returning(User)
    )

    user = db.scalar(statement)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    db.commit()
    db.refresh(user)

    return user



@router.post(
    "/login",
    response_model=TokenResponse,
)
def login_user(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    email = str(credentials.email).lower()
    ip_address = (
        request.client.host
        if request.client is not None
        else "unknown"
    )

    retry_after = consume_login_attempt(
        db,
        email,
        ip_address,
    )

    if retry_after > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={
                "Retry-After": str(retry_after),
            },
        )

    user = db.scalar(
        select(User).where(User.email == email)
    )

    password_hash = (
        user.password_hash
        if user is not None
        else DUMMY_PASSWORD_HASH
    )

    password_is_valid = verify_password(
        credentials.password,
        password_hash,
    )

    if user is None or not password_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    reset_account_login_attempts(db, email, ip_address)

    access_token = create_access_token(
        user_id=str(user.id),
        role=user.role.value,
    )

    return TokenResponse(
        access_token=access_token,
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_authenticated_user(
    current_user: User = Depends(get_current_user),
):
    return current_user