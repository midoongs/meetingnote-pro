import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app import models
from app.db import Base, make_engine, make_session_factory


@pytest.fixture
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = make_session_factory(engine)()
    yield s
    s.close()


def _team(db):
    u = models.User(email="a@b.co", password_hash="x", name="가")
    db.add(u)
    db.flush()
    t = models.Team(name="팀", invite_code="MN-AAAA", owner_id=u.id)
    db.add(t)
    db.flush()
    return u, t


def test_seven_tables(db):
    names = set(inspect(db.get_bind()).get_table_names())
    assert names == {"users", "teams", "memberships", "meetings", "todos", "comments", "activities"}


def test_activity_kind_only_five(db):
    u, t = _team(db)
    db.add(models.Activity(team_id=t.id, actor_id=u.id, kind="other_kind", target="x"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_one_membership_per_user(db):
    u, t = _team(db)
    t2 = models.Team(name="팀2", invite_code="MN-BBBB", owner_id=u.id)
    db.add(t2)
    db.flush()
    db.add(models.Membership(team_id=t.id, user_id=u.id, role="owner"))
    db.flush()
    db.add(models.Membership(team_id=t2.id, user_id=u.id, role="member"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_meeting_delete_cascades_todos_and_comments(db):
    u, t = _team(db)
    m = models.Meeting(team_id=t.id, title="회의", met_at=models.now(), author_id=u.id)
    m.todos.append(models.Todo(what="할 일"))
    m.comments.append(models.Comment(user_id=u.id, content="댓글"))
    db.add(m)
    db.commit()
    db.delete(m)
    db.commit()
    assert db.query(models.Todo).count() == 0
    assert db.query(models.Comment).count() == 0
