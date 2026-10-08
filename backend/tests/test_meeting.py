import io

WAV = b"RIFF" + b"\x24\x00\x00\x00" + b"WAVE" + b"fmt " + b"\x00" * 20
MP3 = b"ID3" + b"\x00" * 50
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 50


def up(client, h, data, name="a.wav"):
    return client.post("/api/upload", files={"file": (name, io.BytesIO(data), "application/octet-stream")}, headers=h)


# ---- 업로드와 받아쓰기

def test_upload_wav_returns_body_only(client, team, fake_ai):
    r = up(client, team["owner"], WAV)
    assert r.status_code == 200 and r.json() == {"body": "받아쓴 본문"}
    assert client.get(f"/api/teams/{team['id']}/meetings", headers=team["owner"]).json() == []  # 저장 없음


def test_upload_mp3_ok(client, team):
    assert up(client, team["owner"], MP3, "a.mp3").status_code == 200


def test_upload_type_by_content_not_extension(client, team):
    r = up(client, team["owner"], MP4, "회의.wav")
    assert (r.status_code, r.json()["code"]) == (415, "UNSUPPORTED_MEDIA_TYPE")


def test_upload_over_25mb(client, team):
    r = up(client, team["owner"], WAV + b"\x00" * (25 * 1024 * 1024))
    assert (r.status_code, r.json()["code"]) == (413, "PAYLOAD_TOO_LARGE")


def test_upload_needs_login(client):
    assert up(client, {}, WAV).status_code == 401


# ---- 저장과 세 항목 구분

def test_create_splits_into_three(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    assert m["summary"].startswith("2차 스프린트")
    assert m["decisions"] == ["업로드 용량 상한은 25MB"]
    assert [t["what"] for t in m["todos"]] == ["목록 화면 및 검색 구현", "사용자 다섯 분 인터뷰"]
    assert client.get(f"/api/teams/{team['id']}/activities", headers=team["owner"]).json()[0]["kind"] == "meeting_add"


def test_unmatched_assignee_is_left_blank_not_invented(api, team):
    m = api.meeting(team["owner"], team["id"])
    by = {t["what"]: t for t in m["todos"]}
    assert by["사용자 다섯 분 인터뷰"]["assignee_id"] is None
    assert by["사용자 다섯 분 인터뷰"]["due_text"] == "미정"
    # "김대리" 는 팀원 이름이라 연결된다
    assert by["목록 화면 및 검색 구현"]["assignee_name"] == "김대리"


def test_no_decision_and_no_todo(api, fake_ai, team):
    fake_ai["split"] = {"summary": "논의만 함", "decisions": [], "todos": []}
    m = api.meeting(team["owner"], team["id"])
    assert m["decisions"] == [] and m["todos"] == []


def test_split_failure_keeps_meeting_with_empty_three(api, fake_ai, team):
    fake_ai["split"] = {"summary": "", "decisions": [], "todos": []}
    m = api.meeting(team["owner"], team["id"])
    assert m["id"] and m["summary"] == ""


def test_required_fields(client, team):
    r = client.post(
        f"/api/teams/{team['id']}/meetings",
        json={"title": " ", "met_at": "2026-09-24T05:00:00Z", "body": "x"},
        headers=team["owner"],
    )
    assert (r.status_code, r.json()["code"]) == (400, "VALIDATION_ERROR")


def test_parse_split_handles_noise():
    from app.gemini import parse_split

    d = parse_split('```json\n{"summary":"a","decisions":["b"],"todos":[{"what":"c","who":"","due":""}]}\n```')
    assert d["todos"] == [{"what": "c", "who": "미정", "due": "미정"}]


# ---- 목록 · 검색 · 상세

def test_list_has_counts_and_no_body(api, client, team):
    api.meeting(team["owner"], team["id"])
    row = client.get(f"/api/teams/{team['id']}/meetings", headers=team["member"]).json()[0]
    assert "body" not in row
    assert (row["todo_total_count"], row["todo_done_count"], row["decision_count"]) == (2, 0, 1)


def test_list_sorted_by_met_at_desc(api, client, team):
    for title, when in (("가", "2026-09-10T00:00:00Z"), ("나", "2026-09-24T00:00:00Z")):
        client.post(
            f"/api/teams/{team['id']}/meetings",
            json={"title": title, "met_at": when, "body": "본문"},
            headers=team["owner"],
        )
    titles = [m["title"] for m in client.get(f"/api/teams/{team['id']}/meetings", headers=team["owner"]).json()]
    assert titles == ["나", "가"]


def test_search_title_and_attendees_only_not_body(api, client, team):
    api.meeting(team["owner"], team["id"], title="배포 환경 점검", body="비밀단어")
    base = f"/api/teams/{team['id']}/meetings"
    h = team["owner"]
    assert len(client.get(base, params={"q": "배포"}, headers=h).json()) == 1
    assert len(client.get(base, params={"q": "박과장"}, headers=h).json()) == 1  # 참석자
    r = client.get(base, params={"q": "비밀단어"}, headers=h)
    assert r.status_code == 200 and r.json() == []  # 본문은 검색 대상이 아님. 404 가 아니라 200 + 빈 배열


def test_date_range(api, client, team):
    api.meeting(team["owner"], team["id"])  # 2026-09-24
    base = f"/api/teams/{team['id']}/meetings"
    h = team["owner"]
    assert len(client.get(base, params={"from": "2026-09-24", "to": "2026-09-24"}, headers=h).json()) == 1
    assert client.get(base, params={"from": "2026-09-25"}, headers=h).json() == []


def test_detail_has_body_and_not_found(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    d = client.get(f"/api/meetings/{m['id']}", headers=team["member"]).json()
    assert d["body"] and len(d["todos"]) == 2
    r = client.get("/api/meetings/9999", headers=team["member"])
    assert (r.status_code, r.json()["code"]) == (404, "MEETING_NOT_FOUND")


def test_other_team_meeting_is_hidden(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    other = api.signup("x@example.com")
    api.team(other, "다른팀")
    assert client.get(f"/api/meetings/{m['id']}", headers=other).status_code == 404


# ---- 수정과 삭제

def test_update_keeps_three_items_and_can_edit_flag(api, client, team):
    m = api.meeting(team["member"], team["id"])  # 박과장이 올림
    before = client.get(f"/api/meetings/{m['id']}", headers=team["member"]).json()
    r = client.put(f"/api/meetings/{m['id']}", json={"title": "새 제목", "body": "고친 본문"}, headers=team["member"])
    assert r.status_code == 200
    after = r.json()
    assert after["title"] == "새 제목" and after["body"] == "고친 본문"
    assert (after["summary"], after["decisions"], after["todos"]) == (before["summary"], before["decisions"], before["todos"])
    assert after["can_edit"] is True


def test_only_author_and_owner_can_edit_or_delete(api, client, team):
    m = api.meeting(team["owner"], team["id"])  # owner 가 올림
    r = client.get(f"/api/meetings/{m['id']}", headers=team["member"]).json()
    assert r["can_edit"] is False
    r = client.put(f"/api/meetings/{m['id']}", json={"title": "x"}, headers=team["member"])
    assert (r.status_code, r.json()["code"]) == (403, "FORBIDDEN")
    assert client.delete(f"/api/meetings/{m['id']}", headers=team["member"]).status_code == 403


def test_owner_can_edit_members_meeting(api, client, team):
    m = api.meeting(team["member"], team["id"])
    assert client.put(f"/api/meetings/{m['id']}", json={"title": "x"}, headers=team["owner"]).status_code == 200


def test_delete_removes_todos_and_comments(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    client.post(f"/api/meetings/{m['id']}/comments", json={"content": "의견"}, headers=team["member"])
    assert client.delete(f"/api/meetings/{m['id']}", headers=team["owner"]).status_code == 204
    assert client.get(f"/api/teams/{team['id']}/todos", headers=team["owner"]).json() == []
    assert client.get(f"/api/meetings/{m['id']}", headers=team["owner"]).status_code == 404


def test_detail_carries_team_members_for_assignment(api, client, team):
    m = api.meeting(team["owner"], team["id"])
    names = [x["name"] for x in client.get(f"/api/meetings/{m['id']}", headers=team["member"]).json()["members"]]
    assert names == ["김대리", "박과장"]
