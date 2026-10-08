def first_todo(client, team, who="owner"):
    return client.get(f"/api/teams/{team['id']}/todos", headers=team[who]).json()[0]


def test_team_and_mine_lists(api, client, team):
    api.meeting(team["owner"], team["id"])
    rows = client.get(f"/api/teams/{team['id']}/todos", headers=team["member"]).json()
    assert len(rows) == 2 and rows[0]["meeting_title"] == "2차 스프린트 계획 회의"
    mine = client.get("/api/me/todos", headers=team["owner"]).json()
    assert [t["what"] for t in mine] == ["목록 화면 및 검색 구현"]  # 김대리에게 배정된 것만
    assert client.get("/api/me/todos", headers=team["member"]).json() == []


def test_empty_is_200_empty_list(client, team):
    r = client.get("/api/me/todos", headers=team["owner"])
    assert r.status_code == 200 and r.json() == []


def test_non_member_cannot_list(api, client, team):
    other = api.signup("x@example.com")
    assert client.get(f"/api/teams/{team['id']}/todos", headers=other).status_code == 403


def test_sorted_by_status_then_due(api, client, team):
    api.meeting(team["owner"], team["id"])
    rows = client.get(f"/api/teams/{team['id']}/todos", headers=team["owner"]).json()
    client.put(f"/api/todos/{rows[0]['id']}", json={"status": "DONE"}, headers=team["owner"])
    again = client.get(f"/api/teams/{team['id']}/todos", headers=team["owner"]).json()
    assert [t["status"] for t in again] == ["OPEN", "DONE"]


def test_any_member_can_change_status_and_revert(api, client, team):
    api.meeting(team["owner"], team["id"])
    t = first_todo(client, team)
    r = client.put(f"/api/todos/{t['id']}", json={"status": "DOING"}, headers=team["member"])
    assert r.status_code == 200 and r.json()["status"] == "DOING"
    r = client.put(f"/api/todos/{t['id']}", json={"status": "DONE"}, headers=team["member"])
    r = client.put(f"/api/todos/{t['id']}", json={"status": "DOING"}, headers=team["member"])  # 되돌림 허용
    assert r.json()["status"] == "DOING"


def test_status_only_three_values(api, client, team):
    api.meeting(team["owner"], team["id"])
    t = first_todo(client, team)
    r = client.put(f"/api/todos/{t['id']}", json={"status": "ARCHIVED"}, headers=team["owner"])
    assert r.status_code == 400


def test_assign_and_unassign(api, client, team):
    api.meeting(team["owner"], team["id"])
    t = [x for x in client.get(f"/api/teams/{team['id']}/todos", headers=team["owner"]).json() if x["assignee_id"] is None][0]
    me = client.get("/api/auth/me", headers=team["member"]).json()["id"]
    r = client.put(f"/api/todos/{t['id']}", json={"assignee_id": me}, headers=team["owner"])
    assert r.json()["assignee_name"] == "박과장"
    r = client.put(f"/api/todos/{t['id']}", json={"assignee_id": None}, headers=team["owner"])
    assert r.json()["assignee_id"] is None  # 미정도 한 값


def test_cannot_assign_outsider(api, client, team):
    api.meeting(team["owner"], team["id"])
    t = first_todo(client, team)
    outsider = api.c.get("/api/auth/me", headers=api.signup("x@example.com")).json()["id"]
    assert client.put(f"/api/todos/{t['id']}", json={"assignee_id": outsider}, headers=team["owner"]).status_code == 400


def test_due_text_free_text_and_blank_becomes_undecided(api, client, team):
    api.meeting(team["owner"], team["id"])
    t = first_todo(client, team)
    r = client.put(f"/api/todos/{t['id']}", json={"due_text": "다음 주 금요일"}, headers=team["member"])
    assert r.json()["due_text"] == "다음 주 금요일"
    r = client.put(f"/api/todos/{t['id']}", json={"due_text": "  "}, headers=team["member"])
    assert r.json()["due_text"] == "미정"


def test_delete_is_owner_only_and_can_delete_flag(api, client, team):
    api.meeting(team["owner"], team["id"])
    as_member = first_todo(client, team, "member")
    assert as_member["can_delete"] is False
    r = client.delete(f"/api/todos/{as_member['id']}", headers=team["member"])
    assert (r.status_code, r.json()["code"]) == (403, "OWNER_ONLY")
    assert first_todo(client, team)["can_delete"] is True
    assert client.delete(f"/api/todos/{as_member['id']}", headers=team["owner"]).status_code == 204
    assert len(client.get(f"/api/teams/{team['id']}/todos", headers=team["owner"]).json()) == 1


def test_rows_carry_assignable_members(api, client, team):
    api.meeting(team["owner"], team["id"])
    rows = client.get(f"/api/teams/{team['id']}/todos", headers=team["member"]).json()
    assert [m["name"] for m in rows[0]["assignable"]] == ["김대리", "박과장"]
    one = client.put(f"/api/todos/{rows[0]['id']}", json={"due_text": "오늘"}, headers=team["member"]).json()
    assert len(one["assignable"]) == 2
