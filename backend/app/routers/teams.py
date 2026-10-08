import secrets

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import config, models
from ..deps import current_user, get_db, membership_of, record, require_member
from ..errors import AppError, bad, owner_only, validation

router = APIRouter(prefix="/teams", tags=["team"])

CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class TeamIn(BaseModel):
    name: str


class JoinIn(BaseModel):
    invite_code: str


def new_code(db: Session) -> str:
    while True:
        code = "MN-" + "".join(secrets.choice(CODE_CHARS) for _ in range(4))
        if not db.query(models.Team).filter_by(invite_code=code).first():
            return code


def team_view(db: Session, team: models.Team, role: str) -> dict:
    count = db.query(func.count(models.Membership.id)).filter_by(team_id=team.id).scalar()
    return {"id": team.id, "name": team.name, "invite_code": team.invite_code, "role": role, "member_count": count}


@router.post("", status_code=201)
def create_team(body: TeamIn, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    if not body.name.strip():
        raise validation("팀 이름을 입력해야 함")
    if membership_of(db, user.id):
        raise AppError(409, "VALIDATION_ERROR", "이미 소속 팀이 있음")
    team = models.Team(name=body.name.strip(), invite_code=new_code(db), owner_id=user.id)
    db.add(team)
    db.flush()
    db.add(models.Membership(team_id=team.id, user_id=user.id, role="owner"))
    db.commit()
    return team_view(db, team, "owner")


@router.get("")
def list_teams(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    m = membership_of(db, user.id)
    if m is None:
        return []
    return [team_view(db, db.get(models.Team, m.team_id), m.role)]


@router.post("/join")
def join(body: JoinIn, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    team = db.query(models.Team).filter_by(invite_code=body.invite_code.strip().upper()).first()
    if team is None:
        raise bad("INVITE_NOT_FOUND", "없는 초대코드", 404)
    if membership_of(db, user.id):
        raise AppError(409, "VALIDATION_ERROR", "이미 소속 팀이 있음")
    count = db.query(func.count(models.Membership.id)).filter_by(team_id=team.id).scalar()
    if count >= config.TEAM_LIMIT:
        raise bad("TEAM_FULL", "팀 정원이 찼음", 409)
    db.add(models.Membership(team_id=team.id, user_id=user.id, role="member"))
    record(db, team.id, user.id, "member_join", f"{team.name}에 합류")
    db.commit()
    return team_view(db, team, "member")


@router.get("/{team_id}/members")
def members(team_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    rows = (
        db.query(models.User, models.Membership)
        .join(models.Membership, models.Membership.user_id == models.User.id)
        .filter(models.Membership.team_id == team_id)
        .order_by(models.Membership.id)
        .all()
    )
    out = []
    for u, m in rows:
        todo_count = (
            db.query(func.count(models.Todo.id))
            .join(models.Meeting, models.Meeting.id == models.Todo.meeting_id)
            .filter(models.Meeting.team_id == team_id, models.Todo.assignee_id == u.id)
            .scalar()
        )
        out.append({"id": u.id, "name": u.name, "email": u.email, "role": m.role, "todo_count": todo_count})
    return out


def owner_team(db: Session, user: models.User, team_id: int) -> models.Team:
    m = require_member(db, user, team_id)
    if m.role != "owner":
        raise owner_only()
    return db.get(models.Team, team_id)


@router.put("/{team_id}/code")
def reissue_code(team_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    team = owner_team(db, user, team_id)
    team.invite_code = new_code(db)  # 앞의 코드는 더 쓸 수 없고 기존 멤버십은 그대로
    db.commit()
    return {"invite_code": team.invite_code}


@router.put("/{team_id}")
def rename(team_id: int, body: TeamIn, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    team = owner_team(db, user, team_id)
    if not body.name.strip():
        raise validation("팀 이름을 입력해야 함")
    team.name = body.name.strip()
    db.commit()
    return team_view(db, team, "owner")
