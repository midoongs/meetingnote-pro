def test_create_team_makes_owner_and_code(api, client):
    h = api.signup("kim@example.com")
    t = api.team(h)
    assert t["role"] == "owner" and t["invite_code"].startswith("MN-")
    assert client.get("/api/teams", headers=h).json()[0]["id"] == t["id"]


def test_one_team_per_user(api, client):
    h = api.signup("kim@example.com")
    api.team(h)
    assert client.post("/api/teams", json={"name": "다른팀"}, headers=h).status_code == 409


def test_join_ok_records_activity(client, team):
    acts = client.get(f"/api/teams/{team['id']}/activities", headers=team["owner"]).json()
    assert [a["kind"] for a in acts] == ["member_join"]


def test_join_unknown_code(api, client):
    h = api.signup("lee@example.com")
    r = api.join(h, "MN-0000")
    assert (r.status_code, r.json()["code"]) == (404, "INVITE_NOT_FOUND")
    assert client.get("/api/auth/me", headers=h).status_code == 200  # 계정은 그대로


def test_team_full_at_six(api):
    owner = api.signup("o@example.com")
    t = api.team(owner)
    for i in range(5):
        assert api.join(api.signup(f"m{i}@example.com"), t["invite_code"]).status_code == 200
    r = api.join(api.signup("late@example.com"), t["invite_code"])
    assert (r.status_code, r.json()["code"]) == (409, "TEAM_FULL")


def test_members_list_has_todo_count(client, team):
    r = client.get(f"/api/teams/{team['id']}/members", headers=team["member"])
    assert r.status_code == 200
    rows = {m["name"]: m for m in r.json()}
    assert rows["김대리"]["role"] == "owner" and rows["박과장"]["role"] == "member"
    assert "todo_count" in rows["김대리"]


def test_non_member_cannot_see_members(api, client, team):
    other = api.signup("x@example.com")
    assert client.get(f"/api/teams/{team['id']}/members", headers=other).status_code == 403


def test_reissue_code_owner_only_and_old_code_dies(api, client, team):
    old = team["team"]["invite_code"]
    r = client.put(f"/api/teams/{team['id']}/code", headers=team["member"])
    assert (r.status_code, r.json()["code"]) == (403, "OWNER_ONLY")
    r = client.put(f"/api/teams/{team['id']}/code", headers=team["owner"])
    assert r.status_code == 200 and r.json()["invite_code"] != old
    late = api.signup("late@example.com")
    assert api.join(late, old).status_code == 404
    # 이미 합류한 멤버는 그대로
    assert client.get(f"/api/teams/{team['id']}/members", headers=team["member"]).status_code == 200


def test_rename_owner_only(client, team):
    r = client.put(f"/api/teams/{team['id']}", json={"name": "새이름"}, headers=team["member"])
    assert (r.status_code, r.json()["code"]) == (403, "OWNER_ONLY")
    r = client.put(f"/api/teams/{team['id']}", json={"name": "새이름"}, headers=team["owner"])
    assert r.status_code == 200 and r.json()["name"] == "새이름"
