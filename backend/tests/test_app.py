from fastapi.testclient import TestClient

from app.main import create_app


def test_unknown_api_path_returns_code_and_msg(client):
    r = client.get("/api/없는경로")
    assert r.status_code == 404
    assert set(r.json()) == {"code", "msg"}


def test_static_login_page_is_served_with_extension(client):
    # frontend/ 가 채워지면 /login.html 이 서빙된다 (3.4 이후)
    r = client.get("/login.html")
    assert r.status_code in (200, 404)


def test_docs_on_locally(fake_ai):
    with TestClient(create_app("sqlite:///:memory:")) as c:  # DATABASE_URL 없음
        assert c.get("/docs").status_code == 200
        paths = c.get("/openapi.json").json()["paths"]
        assert "/api/auth/signup" in paths


def test_docs_off_when_deployed(fake_ai, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    with TestClient(create_app("sqlite:///:memory:")) as c:  # DATABASE_URL 있음
        assert c.get("/docs").status_code == 404
        assert c.get("/openapi.json").status_code == 404


def test_26_unique_api_operations(client):
    ops = [
        (p, m)
        for p, item in client.get("/openapi.json").json()["paths"].items()
        for m in item
    ]
    assert len(ops) == 26


import pytest


@pytest.mark.parametrize("page", ["login", "meetings", "detail", "todos", "team", "profile"])
def test_six_screens_are_served_with_extension(client, page):
    r = client.get(f"/{page}.html")
    assert r.status_code == 200
    assert "theme.js" in r.text and "app.js" in r.text
    assert "stateBar" not in r.text  # 퍼블리싱 확인용 STATE 바는 넣지 않는다


def test_theme_js_has_no_state_bar(client):
    js = client.get("/theme.js").text
    assert "stateBar" not in js and "window.UI" in js
