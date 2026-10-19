
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.comment import Comment
from app.models.user import User, UserRole
from app.models.vulnerability import Vulnerability
from app.schemas.comment import CommentCreate, CommentResponse
from app.services.audit import create_audit_log


router = APIRouter(
    prefix="/vulnerabilities/{vulnerability_id}/comments",
    tags=["Comments"],
)


delete_router = APIRouter(
    prefix="/comments",
    tags=["Comments"],
)


@router.post(
    "",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    vulnerability_id: uuid.UUID,
    comment_data: CommentCreate,
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

    content = comment_data.content.strip()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Comment cannot be empty",
        )

    comment = Comment(
        vulnerability_id=vulnerability_id,
        user_id=current_user.id,
        content=content,
    )

    db.add(comment)
    db.flush()

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="CREATE",
        entity_type="comment",
        entity_id=comment.id,
        changes={
            "vulnerability_id": comment.vulnerability_id,
            "user_id": comment.user_id,
            "content": comment.content,
        },
    )

    db.commit()
    db.refresh(comment)

    return comment


@router.get(
    "",
    response_model=list[CommentResponse],
)
def list_comments(
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

    comments = db.scalars(
        select(Comment)
        .where(Comment.vulnerability_id == vulnerability_id)
        .order_by(Comment.created_at.asc())
    ).all()

    return comments


@delete_router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_comment(
    comment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.ANALYST)
    ),
) -> Response:
    comment = db.get(Comment, comment_id)

    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    if (
        current_user.role != UserRole.ADMIN
        and comment.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments",
        )

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="DELETE",
        entity_type="comment",
        entity_id=comment.id,
        changes={
            "vulnerability_id": comment.vulnerability_id,
            "user_id": comment.user_id,
            "content": comment.content,
        },
    )

    db.delete(comment)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
