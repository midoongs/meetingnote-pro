import time

import jwt

from app import config


def signup(c, **kw):
    body = {"email": "kim@example.com", "password": "password1", "name": "김대리", **kw}
    return c.post("/api/auth/signup", json=body)


def test_signup_ok_returns_201_and_jwt(client):
    r = signup(client)
    assert r.status_code == 201
    assert r.json()["token"]
    assert r.json()["team_id"] is None


def test_signup_bad_email(client):
    r = signup(client, email="user@@example")
    assert (r.status_code, r.json()["code"]) == (400, "EMAIL_INVALID")


def test_signup_duplicate(client):
    signup(client)
    r = signup(client)
    assert (r.status_code, r.json()["code"]) == (409, "EMAIL_DUPLICATED")


def test_signup_weak_password(client):
    r = signup(client, password="1234")
    assert (r.status_code, r.json()["code"]) == (400, "PASSWORD_TOO_WEAK")


def test_password_stored_as_bcrypt(client):
    from app.models import User

    signup(client)
    s = client.app.state.session_factory()
    assert s.query(User).one().password_hash.startswith("$2")


def test_login_ok(client):
    signup(client)
    r = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password1"})
    assert r.status_code == 200 and r.json()["token"]


def test_login_failure_is_same_for_unknown_email_and_wrong_password(client):
    signup(client)
    a = client.post("/api/auth/login", json={"email": "none@example.com", "password": "password1"})
    b = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "wrongpass1"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()
    assert a.json()["code"] == "INVALID_CREDENTIALS"


def test_token_lasts_24_hours(client):
    t = signup(client).json()["token"]
    data = jwt.decode(t, config.JWT_SECRET, algorithms=["HS256"])
    assert abs((data["exp"] - time.time()) - 24 * 3600) < 60


def test_expired_token_is_401_token_expired(client):
    old = jwt.encode({"sub": "1", "exp": int(time.time()) - 10}, config.JWT_SECRET, algorithm="HS256")
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old}"})
    assert (r.status_code, r.json()["code"]) == (401, "TOKEN_EXPIRED")


def test_no_token_is_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_has_team_info(api, client):
    h = api.signup("kim@example.com")
    assert client.get("/api/auth/me", headers=h).json()["team_id"] is None
    api.team(h, "기획팀")
    me = client.get("/api/auth/me", headers=h).json()
    assert (me["team_name"], me["role"]) == ("기획팀", "owner")
    assert me["team_id"]


def test_update_name_only_keeps_password(api, client):
    h = api.signup("kim@example.com")
    r = client.put("/api/auth/me", json={"name": "김수석"}, headers=h)
    assert r.status_code == 200 and r.json()["name"] == "김수석"
    ok = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password1"})
    assert ok.status_code == 200


def test_change_password_needs_current(api, client):
    h = api.signup("kim@example.com")
    r = client.put("/api/auth/me", json={"current_password": "wrong", "new_password": "newpass1234"}, headers=h)
    assert (r.status_code, r.json()["code"]) == (401, "UNAUTHORIZED")
    r = client.put("/api/auth/me", json={"new_password": "newpass1234"}, headers=h)
    assert (r.status_code, r.json()["code"]) == (401, "UNAUTHORIZED")


def test_change_password_weak(api, client):
    h = api.signup("kim@example.com")
    r = client.put("/api/auth/me", json={"current_password": "password1", "new_password": "1234"}, headers=h)
    assert (r.status_code, r.json()["code"]) == (400, "PASSWORD_TOO_WEAK")


def test_change_password_ok(api, client):
    h = api.signup("kim@example.com")
    r = client.put("/api/auth/me", json={"current_password": "password1", "new_password": "newpass1234"}, headers=h)
    assert r.status_code == 200
    assert client.post("/api/auth/login", json={"email": "kim@example.com", "password": "newpass1234"}).status_code == 200


def test_logout_returns_200(api, client):
    h = api.signup("kim@example.com")
    assert client.post("/api/auth/logout", headers=h).status_code == 200


def test_swagger_has_bearer_authorize(client):
    spec = client.get("/openapi.json").json()
    assert any(s.get("scheme") == "bearer" for s in spec["components"]["securitySchemes"].values())
