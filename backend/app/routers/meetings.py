from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import config, gemini, models
from ..deps import current_user, get_db, membership_of, record, require_member
from ..errors import bad, forbidden, validation

router = APIRouter(tags=["meeting"])


class MeetingIn(BaseModel):
    title: str
    met_at: str
    attendees: str = ""
    body: str


class MeetingPatch(BaseModel):
    title: str | None = None
    met_at: str | None = None
    attendees: str | None = None
    body: str | None = None


def iso(dt: datetime) -> str:
    return dt.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def parse_when(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise validation("회의 시각 형식이 올바르지 않음")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def decision_lines(m: models.Meeting) -> list[str]:
    return [x for x in m.decisions.split("\n") if x.strip()]


def can_edit(db: Session, user: models.User, m: models.Meeting) -> bool:
    mem = membership_of(db, user.id)
    return m.author_id == user.id or (mem is not None and mem.team_id == m.team_id and mem.role == "owner")


def list_view(db: Session, user: models.User, m: models.Meeting) -> dict:
    done = sum(1 for t in m.todos if t.status == "DONE")
    return {
        "id": m.id,
        "title": m.title,
        "met_at": iso(m.met_at),
        "attendees": m.attendees,
        "summary": m.summary,
        "created_at": iso(m.created_at),
        "todo_done_count": done,
        "todo_total_count": len(m.todos),
        "decision_count": len(decision_lines(m)),
        "can_edit": can_edit(db, user, m),
    }


def todo_row(db: Session, t: models.Todo) -> dict:
    who = db.get(models.User, t.assignee_id) if t.assignee_id else None
    return {
        "id": t.id,
        "what": t.what,
        "assignee_id": t.assignee_id,
        "assignee_name": who.name if who else None,
        "due_text": t.due_text,
        "status": t.status,
    }


def team_members(db: Session, team_id: int) -> list[dict]:
    rows = (
        db.query(models.User)
        .join(models.Membership, models.Membership.user_id == models.User.id)
        .filter(models.Membership.team_id == team_id)
        .order_by(models.Membership.id)
        .all()
    )
    return [{"id": u.id, "name": u.name} for u in rows]


def detail_view(db: Session, user: models.User, m: models.Meeting) -> dict:
    v = list_view(db, user, m)
    v.update(
        body=m.body,
        decisions=decision_lines(m),
        todos=[todo_row(db, t) for t in m.todos],
        author_id=m.author_id,
        members=team_members(db, m.team_id),  # 화면이 담당자 선택지를 따로 부르지 않도록
    )
    return v


def load_meeting(db: Session, user: models.User, meeting_id: int) -> models.Meeting:
    m = db.get(models.Meeting, meeting_id)
    mem = membership_of(db, user.id)
    # 다른 팀의 회의록은 있는지도 드러내지 않는다
    if m is None or mem is None or mem.team_id != m.team_id:
        raise bad("MEETING_NOT_FOUND", "없는 회의록", 404)
    return m


def sniff_audio(data: bytes) -> str | None:
    """확장자가 아니라 내용 형식으로 판정한다."""
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return "audio/mpeg"
    return None


@router.post("/upload")
async def upload(file: UploadFile, _: models.User = Depends(current_user)):
    data = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise bad("PAYLOAD_TOO_LARGE", "25MB 를 넘는 파일", 413)
    mime = sniff_audio(data)
    if mime is None:
        raise bad("UNSUPPORTED_MEDIA_TYPE", "mp3 또는 wav 만 올릴 수 있음", 415)
    return {"body": gemini.transcribe(data, mime)}


def apply_split(db: Session, m: models.Meeting, split: dict) -> None:
    m.summary = split["summary"]
    m.decisions = "\n".join(split["decisions"])
    names = {
        u.name: u.id
        for u in db.query(models.User)
        .join(models.Membership, models.Membership.user_id == models.User.id)
        .filter(models.Membership.team_id == m.team_id)
    }
    for t in split["todos"]:
        # 팀원과 맞지 않거나 미정이면 지어내지 않고 비워 둔다
        m.todos.append(models.Todo(what=t["what"], assignee_id=names.get(t["who"]), due_text=t["due"] or "미정"))


@router.post("/teams/{team_id}/meetings", status_code=201)
def create_meeting(team_id: int, body: MeetingIn, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    if not body.title.strip() or not body.met_at.strip() or not body.body.strip():
        raise validation("제목 · 회의 시각 · 본문이 필수")
    m = models.Meeting(
        team_id=team_id,
        title=body.title.strip(),
        met_at=parse_when(body.met_at),
        attendees=body.attendees.strip(),
        body=body.body,
        author_id=user.id,
    )
    apply_split(db, m, gemini.split_body(body.body))
    db.add(m)
    db.flush()
    record(db, team_id, user.id, "meeting_add", f"회의록 「{m.title}」 등록")
    db.commit()
    return detail_view(db, user, m)


@router.get("/teams/{team_id}/meetings")
def list_meetings(
    team_id: int,
    q: str | None = None,
    from_: date | None = Query(None, alias="from"),
    to: date | None = None,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    require_member(db, user, team_id)
    query = db.query(models.Meeting).filter(models.Meeting.team_id == team_id)
    if q:
        like = f"%{q.strip()}%"  # 제목과 참석자만. 본문은 검색 대상이 아님
        query = query.filter(or_(models.Meeting.title.ilike(like), models.Meeting.attendees.ilike(like)))
    if from_:
        query = query.filter(models.Meeting.met_at >= datetime.combine(from_, datetime.min.time()))
    if to:
        query = query.filter(models.Meeting.met_at < datetime.combine(to, datetime.min.time()).replace(hour=23, minute=59, second=59, microsecond=999999))
    rows = query.order_by(models.Meeting.met_at.desc(), models.Meeting.id.desc()).all()
    return [list_view(db, user, m) for m in rows]


@router.get("/meetings/{meeting_id}")
def get_meeting(meeting_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    return detail_view(db, user, load_meeting(db, user, meeting_id))


@router.put("/meetings/{meeting_id}")
def update_meeting(meeting_id: int, body: MeetingPatch, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    m = load_meeting(db, user, meeting_id)
    if not can_edit(db, user, m):
        raise forbidden("올린 사람과 owner 만 고칠 수 있음")
    if body.title is not None:
        if not body.title.strip():
            raise validation("제목을 입력해야 함")
        m.title = body.title.strip()
    if body.met_at is not None:
        m.met_at = parse_when(body.met_at)
    if body.attendees is not None:
        m.attendees = body.attendees.strip()
    if body.body is not None:
        m.body = body.body  # 받아쓰기와 요약은 다시 돌리지 않는다
    db.commit()
    return detail_view(db, user, m)


@router.delete("/meetings/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    m = load_meeting(db, user, meeting_id)
    if not can_edit(db, user, m):
        raise forbidden("올린 사람과 owner 만 지울 수 있음")
    db.delete(m)  # 딸린 할 일과 댓글도 함께 지운다
    db.commit()
