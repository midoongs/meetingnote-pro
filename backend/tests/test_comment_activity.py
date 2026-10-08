def add(client, h, mid, text="의견"):
    return client.post(f"/api/meetings/{mid}/comments", json={"content": text}, headers=h)


def test_comment_create_and_list_order(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    assert add(client, team["member"], m["id"], "첫째").status_code == 201
    add(client, team["owner"], m["id"], "둘째")
    rows = client.get(f"/api/meetings/{m['id']}/comments", headers=team["member"]).json()
    assert [c["content"] for c in rows] == ["첫째", "둘째"]  # 오래된 것부터
    assert rows[0]["user_name"] == "박과장"


def test_comment_limit_500(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    assert add(client, team["member"], m["id"], "가" * 500).status_code == 201
    r = add(client, team["member"], m["id"], "가" * 501)
    assert (r.status_code, r.json()["code"]) == (400, "VALIDATION_ERROR")


def test_comment_empty_list_is_200(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    r = client.get(f"/api/meetings/{m['id']}/comments", headers=team["owner"])
    assert r.status_code == 200 and r.json() == []


def test_can_delete_flag_and_forbidden(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    add(client, team["owner"], m["id"], "owner 글")
    add(client, team["member"], m["id"], "member 글")
    third = api.signup("lee@example.com", "이주임")
    api.join(third, team["team"]["invite_code"])
    rows = {c["content"]: c for c in client.get(f"/api/meetings/{m['id']}/comments", headers=third).json()}
    assert rows["owner 글"]["can_delete"] is False and rows["member 글"]["can_delete"] is False
    r = client.delete(f"/api/comments/{rows['owner 글']['id']}", headers=third)
    assert (r.status_code, r.json()["code"]) == (403, "FORBIDDEN")


def test_author_and_owner_can_delete(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    a = add(client, team["member"], m["id"], "member 글").json()
    b = add(client, team["member"], m["id"], "또 member 글").json()
    assert client.delete(f"/api/comments/{a['id']}", headers=team["member"]).status_code == 204  # 쓴 사람
    assert client.delete(f"/api/comments/{b['id']}", headers=team["owner"]).status_code == 204  # owner
    assert client.get(f"/api/meetings/{m['id']}/comments", headers=team["owner"]).json() == []


# ---- 활동 기록

def kinds(client, h, team_id):
    return [a["kind"] for a in client.get(f"/api/teams/{team_id}/activities", headers=h).json()]


def test_five_kinds_are_recorded(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    add(client, team["member"], m["id"])
    t = client.get(f"/api/teams/{team['id']}/todos", headers=team["owner"]).json()[0]
    pid = client.get("/api/auth/me", headers=team["member"]).json()["id"]
    client.put(f"/api/todos/{t['id']}", json={"assignee_id": pid}, headers=team["owner"])
    client.put(f"/api/todos/{t['id']}", json={"status": "DONE"}, headers=team["member"])
    got = set(kinds(client, team["owner"], team["id"]))
    assert got == {"member_join", "meeting_add", "comment_add", "todo_assign", "todo_done"}


def test_done_recorded_once_and_account_changes_not_recorded(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    t = client.get(f"/api/teams/{team['id']}/todos", headers=team["owner"]).json()[0]
    client.put(f"/api/todos/{t['id']}", json={"status": "DONE"}, headers=team["owner"])
    client.put(f"/api/todos/{t['id']}", json={"status": "DONE"}, headers=team["owner"])
    before = kinds(client, team["owner"], team["id"])
    assert before.count("todo_done") == 1
    client.put("/api/auth/me", json={"name": "김수석"}, headers=team["owner"])
    client.put("/api/auth/me", json={"current_password": "password1", "new_password": "newpass1234"}, headers=team["owner"])
    assert kinds(client, team["owner"], team["id"]) == before


def test_team_activities_latest_first_with_sentences(api, client, team):
    api.meeting(team["owner"], team["id"])
    rows = client.get(f"/api/teams/{team['id']}/activities", headers=team["member"]).json()
    assert rows[0]["kind"] == "meeting_add" and rows[0]["text"] == "회의록 「2차 스프린트 계획 회의」 등록"
    assert set(rows[0]) == {"id", "kind", "actor_name", "text", "created_at"}


def test_team_activities_limit_50(api, client, team):
    for i in range(55):
        api.meeting(team["owner"], team["id"], title=f"회의 {i}")
    assert len(client.get(f"/api/teams/{team['id']}/activities", headers=team["owner"]).json()) == 50


def test_my_activities_only_mine_and_empty_is_200(api, client, team):
    api.meeting(team["owner"], team["id"])
    mine = client.get("/api/me/activities", headers=team["owner"]).json()
    assert [a["kind"] for a in mine] == ["meeting_add"]
    other = client.get("/api/me/activities", headers=team["member"]).json()
    assert [a["kind"] for a in other] == ["member_join"]
    lonely = api.signup("z@example.com")
    r = client.get("/api/me/activities", headers=lonely)
    assert r.status_code == 200 and r.json() == []


def test_non_member_cannot_read_team_activities(api, client, team):
    other = api.signup("x@example.com")
    assert client.get(f"/api/teams/{team['id']}/activities", headers=other).status_code == 403
