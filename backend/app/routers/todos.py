from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..deps import current_user, get_db, membership_of, record, require_member
from ..errors import AppError, owner_only, validation
from .meetings import team_members

router = APIRouter(tags=["todo"])

ORDER = {"OPEN": 0, "DOING": 1, "DONE": 2}


class TodoPatch(BaseModel):
    status: str | None = None
    assignee_id: int | None = None
    due_text: str | None = None
    # assignee_id 를 null 로 보내면 "미정" 으로 되돌린다. 보낸 필드는 model_fields_set 으로 구분한다


def row(db: Session, t: models.Todo, m: models.Meeting, is_owner: bool, members: list[dict]) -> dict:
    who = db.get(models.User, t.assignee_id) if t.assignee_id else None
    return {
        "id": t.id,
        "what": t.what,
        "assignee_id": t.assignee_id,
        "assignee_name": who.name if who else None,
        "due_text": t.due_text,
        "status": t.status,
        "meeting_id": m.id,
        "meeting_title": m.title,
        "can_delete": is_owner,
        "assignable": members,  # 담당자 선택지. 화면이 팀원 목록을 따로 부르지 않도록
    }


def team_rows(db: Session, user: models.User, team_id: int, mine: bool) -> list[dict]:
    mem = require_member(db, user, team_id)
    q = (
        db.query(models.Todo, models.Meeting)
        .join(models.Meeting, models.Meeting.id == models.Todo.meeting_id)
        .filter(models.Meeting.team_id == team_id)
    )
    if mine:
        q = q.filter(models.Todo.assignee_id == user.id)
    pairs = sorted(q.all(), key=lambda p: (ORDER[p[0].status], p[0].due_text, p[0].id))
    members = team_members(db, team_id)
    return [row(db, t, m, mem.role == "owner", members) for t, m in pairs]


@router.get("/teams/{team_id}/todos")
def team_todos(team_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    return team_rows(db, user, team_id, mine=False)


@router.get("/me/todos")
def my_todos(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    mem = membership_of(db, user.id)
    return team_rows(db, user, mem.team_id, mine=True) if mem else []


def load_todo(db: Session, user: models.User, todo_id: int):
    t = db.get(models.Todo, todo_id)
    m = db.get(models.Meeting, t.meeting_id) if t else None
    mem = membership_of(db, user.id)
    if t is None or mem is None or mem.team_id != m.team_id:
        raise AppError(404, "NOT_FOUND", "없는 할 일")
    return t, m, mem


@router.put("/todos/{todo_id}")
def update_todo(todo_id: int, body: TodoPatch, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    t, m, mem = load_todo(db, user, todo_id)
    sent = body.model_fields_set
    if "status" in sent:
        if body.status not in models.TODO_STATUSES:
            raise validation("상태는 OPEN · DOING · DONE 만 가능")
        became_done = body.status == "DONE" and t.status != "DONE"
        t.status = body.status
        if became_done:
            record(db, m.team_id, user.id, "todo_done", f"할 일 「{t.what}」 완료")
    if "assignee_id" in sent:
        new = body.assignee_id
        if new is not None:
            member = db.query(models.Membership).filter_by(team_id=m.team_id, user_id=new).first()
            if member is None:
                raise validation("팀원이 아닌 사람은 배정할 수 없음")
        if new != t.assignee_id:
            t.assignee_id = new
            if new is not None:
                who = db.get(models.User, new)
                record(db, m.team_id, user.id, "todo_assign", f"할 일 「{t.what}」를 {who.name}에게 배정")
    if "due_text" in sent:
        t.due_text = (body.due_text or "").strip() or "미정"
    db.commit()
    return row(db, t, m, mem.role == "owner", team_members(db, m.team_id))


@router.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    t, _, mem = load_todo(db, user, todo_id)
    if mem.role != "owner":
        raise owner_only()
    db.delete(t)
    db.commit()
