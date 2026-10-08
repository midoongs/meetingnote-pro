import pytest
from fastapi.testclient import TestClient

from app import gemini
from app.main import create_app

FAKE_SPLIT = {
    "summary": "2차 스프린트 계획을 다루었다.\n업로드 용량은 25MB 로 제한하기로 했다.",
    "decisions": ["업로드 용량 상한은 25MB"],
    "todos": [
        {"what": "목록 화면 및 검색 구현", "who": "김대리", "due": "다음 주 금요일"},
        {"what": "사용자 다섯 분 인터뷰", "who": "미정", "due": "미정"},
    ],
}


class Api:
    """테스트 도우미: 사용자 만들기 · 로그인 · 팀 만들기."""

    def __init__(self, client: TestClient):
        self.c = client

    def signup(self, email, name="김대리", pw="password1"):
        r = self.c.post("/api/auth/signup", json={"email": email, "password": pw, "name": name})
        assert r.status_code == 201, r.text
        return {"Authorization": "Bearer " + r.json()["token"]}

    def team(self, h, name="기획팀"):
        r = self.c.post("/api/teams", json={"name": name}, headers=h)
        assert r.status_code == 201, r.text
        return r.json()

    def join(self, h, code):
        return self.c.post("/api/teams/join", json={"invite_code": code}, headers=h)

    def meeting(self, h, team_id, title="2차 스프린트 계획 회의", body="김대리: 목록은 제가 하겠습니다."):
        r = self.c.post(
            f"/api/teams/{team_id}/meetings",
            json={"title": title, "met_at": "2026-09-24T05:00:00Z", "attendees": "김대리, 박과장", "body": body},
            headers=h,
        )
        assert r.status_code == 201, r.text
        return r.json()


@pytest.fixture
def fake_ai(monkeypatch):
    state = {"split": FAKE_SPLIT, "text": "받아쓴 본문"}
    monkeypatch.setattr(gemini, "split_body", lambda body: state["split"])
    monkeypatch.setattr(gemini, "transcribe", lambda data, mime: state["text"])
    return state


@pytest.fixture
def client(fake_ai):
    app = create_app("sqlite:///:memory:", docs=True)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def api(client):
    return Api(client)


@pytest.fixture
def team(api):
    """owner 한 명(김대리)과 member 한 명(박과장)이 있는 팀."""
    owner = api.signup("kim@example.com", "김대리")
    t = api.team(owner)
    member = api.signup("park@example.com", "박과장")
    assert api.join(member, t["invite_code"]).status_code == 200
    return {"team": t, "owner": owner, "member": member, "id": t["id"]}
