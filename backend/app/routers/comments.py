from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import config, models
from ..deps import current_user, get_db, membership_of, record
from ..errors import AppError, forbidden, validation
from .meetings import iso, load_meeting

router = APIRouter(tags=["comment"])


class CommentIn(BaseModel):
    content: str


def row(db: Session, c: models.Comment, user: models.User, is_owner: bool) -> dict:
    who = db.get(models.User, c.user_id)
    return {
        "id": c.id,
        "user_id": c.user_id,
        "user_name": who.name if who else "",
        "content": c.content,
        "created_at": iso(c.created_at),
        "can_delete": c.user_id == user.id or is_owner,  # 쓴 사람과 owner 만
    }


@router.post("/meetings/{meeting_id}/comments", status_code=201)
def add_comment(meeting_id: int, body: CommentIn, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    m = load_meeting(db, user, meeting_id)
    text = body.content.strip()
    if not text or len(text) > config.COMMENT_LIMIT:
        raise validation("댓글은 1자 이상 500자 이내")
    c = models.Comment(meeting_id=m.id, user_id=user.id, content=text)
    db.add(c)
    record(db, m.team_id, user.id, "comment_add", f"회의록 「{m.title}」에 댓글 작성")
    db.commit()
    mem = membership_of(db, user.id)
    return row(db, c, user, mem.role == "owner")


@router.get("/meetings/{meeting_id}/comments")
def list_comments(meeting_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    m = load_meeting(db, user, meeting_id)
    owner = membership_of(db, user.id).role == "owner"
    rows = db.query(models.Comment).filter_by(meeting_id=m.id).order_by(models.Comment.created_at, models.Comment.id)
    return [row(db, c, user, owner) for c in rows]


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(models.Comment, comment_id)
    m = db.get(models.Meeting, c.meeting_id) if c else None
    mem = membership_of(db, user.id)
    if c is None or mem is None or mem.team_id != m.team_id:
        raise AppError(404, "NOT_FOUND", "없는 댓글")
    if c.user_id != user.id and mem.role != "owner":
        raise forbidden("쓴 사람과 owner 만 지울 수 있음")
    db.delete(c)
    db.commit()
