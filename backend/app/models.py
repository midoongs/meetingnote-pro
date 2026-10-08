"""DB 7테이블 (정의서 6). 시각은 UTC 로 저장한다."""
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

ACTIVITY_KINDS = ("meeting_add", "todo_assign", "todo_done", "comment_add", "member_join")
TODO_STATUSES = ("OPEN", "DOING", "DONE")


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=now)


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    invite_code: Mapped[str] = mapped_column(String(20), unique=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=now)


class Membership(Base):
    __tablename__ = "memberships"
    # 한 사람은 한 팀에만 속한다 (user_id 유일)
    __table_args__ = (UniqueConstraint("user_id"), CheckConstraint("role in ('owner','member')"))
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(10))
    joined_at: Mapped[datetime] = mapped_column(default=now)


class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    title: Mapped[str] = mapped_column(String(200))
    met_at: Mapped[datetime]
    attendees: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    decisions: Mapped[str] = mapped_column(Text, default="")  # 줄바꿈으로 구분
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=now)

    todos: Mapped[list["Todo"]] = relationship(cascade="all, delete-orphan", order_by="Todo.id")
    comments: Mapped[list["Comment"]] = relationship(cascade="all, delete-orphan", order_by="Comment.id")


class Todo(Base):
    __tablename__ = "todos"
    __table_args__ = (CheckConstraint("status in ('OPEN','DOING','DONE')"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    what: Mapped[str] = mapped_column(Text)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_text: Mapped[str] = mapped_column(String(100), default="미정")
    status: Mapped[str] = mapped_column(String(10), default="OPEN")


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=now)


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint("kind in ('meeting_add','todo_assign','todo_done','comment_add','member_join')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(20))
    target: Mapped[str] = mapped_column(Text)  # 서버가 만든 완성 문장
    created_at: Mapped[datetime] = mapped_column(default=now)
