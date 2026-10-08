"""Gemini 로 받아쓰기와 세 항목 구분을 한다. 키와 모델명은 .env 에서만 읽는다."""
import json
import logging
import os
import re

from .errors import AppError

log = logging.getLogger("meetingnote.gemini")

SPLIT_PROMPT = """아래는 회의를 받아쓴 본문이다. 본문만 근거로 JSON 하나만 돌려줘.
{"summary": "회의 전체를 3~5줄로 요약. 줄바꿈으로 구분. 본문에 없는 사실을 보태지 말 것",
 "decisions": ["합의가 끝난 것만. '하기로 했다·확정·승인' 같은 것. 논의만 한 것은 넣지 말 것"],
 "todos": [{"what": "할 일 내용", "who": "담당자 이름. 말하지 않았으면 미정", "due": "기한 표현 그대로. 없으면 미정"}]}
담당자나 기한이 드러난 할 일만 todos 에 넣는다. 없으면 빈 배열이다.

본문:
"""


def _client():
    from google import genai
    from google.genai import types

    key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")
    if not key or not model:
        raise AppError(503, "AI_UNAVAILABLE", "받아쓰기 설정이 없음")
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=60000)), model, types


def transcribe(data: bytes, mime: str) -> str:
    client, model, types = _client()
    try:
        res = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=data, mime_type=mime),
                "이 녹취를 한국어 글로 그대로 받아써 줘. 설명 없이 본문만.",
            ],
        )
        return (res.text or "").strip()
    except AppError:
        raise
    except Exception:
        log.exception("transcribe failed")
        raise AppError(503, "AI_UNAVAILABLE", "받아쓰기에 실패함")


def split_body(body: str) -> dict:
    """요약 · 결정사항 · 할 일. 응답이 어긋나면 세 칸을 비우고 회의록 저장은 이어 간다."""
    empty = {"summary": "", "decisions": [], "todos": []}
    if not body.strip():
        return empty
    try:
        client, model, types = _client()
        res = client.models.generate_content(
            model=model,
            contents=SPLIT_PROMPT + body,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return parse_split(res.text or "")
    except Exception:
        log.exception("split failed")
        return empty


def parse_split(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no json")
    d = json.loads(m.group(0))
    todos = []
    for t in d.get("todos") or []:
        what = str(t.get("what", "")).strip()
        if what:
            todos.append({
                "what": what,
                "who": str(t.get("who", "미정")).strip() or "미정",
                "due": str(t.get("due", "미정")).strip() or "미정",
            })
    return {
        "summary": str(d.get("summary", "")).strip(),
        "decisions": [str(x).strip() for x in d.get("decisions") or [] if str(x).strip()],
        "todos": todos,
    }
