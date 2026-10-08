from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .errors import AppError, forbidden
from .security import read_token

bearer = HTTPBearer(auto_error=False, description="로그인으로 받은 JWT")


def get_db(request: Request):
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


def current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> models.User:
    if cred is None:
        raise AppError(401, "TOKEN_EXPIRED", "세션이 만료됨")
    user = db.get(models.User, read_token(cred.credentials))
    if user is None:
        raise AppError(401, "TOKEN_EXPIRED", "세션이 만료됨")
    return user


def membership_of(db: Session, user_id: int) -> models.Membership | None:
    return db.query(models.Membership).filter_by(user_id=user_id).first()


def require_member(db: Session, user: models.User, team_id: int) -> models.Membership:
    m = membership_of(db, user.id)
    if m is None or m.team_id != team_id:
        raise forbidden("이 팀의 멤버가 아님")
    return m


def record(db: Session, team_id: int, actor_id: int, kind: str, sentence: str) -> None:
    """활동 기록 (정의서 6: kind 5종 외의 값을 만들지 않음)."""
    if kind not in models.ACTIVITY_KINDS:
        raise ValueError(kind)
    db.add(models.Activity(team_id=team_id, actor_id=actor_id, kind=kind, target=sentence))
