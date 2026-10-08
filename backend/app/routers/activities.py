from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import config, models
from ..deps import current_user, get_db, membership_of, require_member
from .meetings import iso

router = APIRouter(tags=["activity"])


def rows(db: Session, q) -> list[dict]:
    items = q.order_by(models.Activity.created_at.desc(), models.Activity.id.desc()).limit(config.ACTIVITY_LIMIT).all()
    out = []
    for a in items:
        who = db.get(models.User, a.actor_id)
        out.append({
            "id": a.id,
            "kind": a.kind,
            "actor_name": who.name if who else "",
            "text": a.target,  # 서버가 만든 완성 문장. 화면은 그대로 그린다
            "created_at": iso(a.created_at),
        })
    return out


@router.get("/teams/{team_id}/activities")
def team_activities(team_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    return rows(db, db.query(models.Activity).filter_by(team_id=team_id))


@router.get("/me/activities")
def my_activities(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    if membership_of(db, user.id) is None:
        return []
    return rows(db, db.query(models.Activity).filter_by(actor_id=user.id))
