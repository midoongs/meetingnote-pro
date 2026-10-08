# MeetingNote Pro

팀이 함께 쓰는 회의록. 녹취를 받아쓴 본문이 요약 · 결정사항 · 할 일로 나뉘고, 할 일은 칸반으로 추적되며, 댓글과 활동 기록이 남는다.

- Backend: FastAPI + SQLAlchemy (로컬 SQLite, 배포 Neon Postgres)
- Frontend: Vanilla JS + Tailwind CDN (`frontend/`, FastAPI 가 StaticFiles 로 함께 서빙)
- 받아쓰기 · 세 항목 구분: Google Gemini
- 기획 문서: `docs/`(정의서 · 스토리보드 · 디자인 시스템), 확정 디자인: `publish/`, 계획: `openspec/changes/meetingnote-pro-round1/`

## 로컬 실행

```bash
pip install -r backend/requirements.txt
cp .env.example .env        # GEMINI_API_KEY, GEMINI_MODEL 두 줄만 채운다 (받아쓰기에만 필요)
cd backend
python -m uvicorn app.main:app --reload
```

`http://127.0.0.1:8000` 이 열린다 (`/login.html` 로 이동). 키는 프로젝트 **루트**의 `.env` 에서 읽는다.
`.env` 가 없어도 서버는 뜨지만 `POST /api/upload` 와 세 항목 구분은 쓸 수 없다 (회의록 저장은 세 칸이 빈 채로 이어진다).

## Swagger UI

로컬(`DATABASE_URL` 없음)에서는 `http://127.0.0.1:8000/docs` 가 열린다.
`POST /api/auth/login` 으로 받은 `token` 을 오른쪽 위 **Authorize** 에 넣으면 보호된 API 를 화면에서 바로 시험할 수 있다.
`DATABASE_URL` 이 있는 배포 환경에서는 `/docs` 와 `/openapi.json` 이 꺼진다.

## 테스트

```bash
cd backend
python -m pytest -q
```

Gemini 호출은 테스트에서 가짜로 바꾼다. 메모리 SQLite 를 쓰므로 로컬 DB 는 건드리지 않는다.

## 환경 변수

| 이름 | 어디에 | 비고 |
|---|---|---|
| `GEMINI_API_KEY` | 로컬 `.env` · 배포 Vercel | 받아쓰기와 세 항목 구분 |
| `GEMINI_MODEL` | 로컬 `.env` · 배포 Vercel | 모델명 |
| `JWT_SECRET` | 배포 Vercel 에만 | 로컬은 코드 기본값 |
| `DATABASE_URL` | Neon 연결 시 자동 주입 | 있으면 Postgres, 없으면 SQLite(`meetingnote.db`) |
| `CORS_ORIGINS` | 배포 Vercel (선택) | 배포 도메인을 쉼표로 더한다 |

`.env` 와 `.env.example` 은 `GEMINI_API_KEY`, `GEMINI_MODEL` 두 줄뿐이다.

## 배포 (Vercel + Neon)

1. Vercel 프로젝트를 만들고 이 저장소를 연결한다. 진입점은 루트 `main.py`(`pyproject.toml` 의 `[tool.vercel]`)다.
2. Vercel Storage 에서 Neon Postgres 를 연결한다. `DATABASE_URL` 이 자동으로 들어온다.
3. 환경 변수에 `GEMINI_API_KEY`, `GEMINI_MODEL`, `JWT_SECRET`(임의의 긴 문자열)을 등록한다.
4. 배포 후 `https://<프로젝트>.vercel.app/login.html` 을 연다.

SQLite 는 배포 환경에서 파일을 쓸 수 없으므로 쓰지 않는다. 코드는 `DATABASE_URL` 유무로만 갈린다.

> 아직 실제 Vercel 계정으로 배포해 보지 않았다. 로컬에서는 위 명령으로 서버가 뜨고 루트 `main.py` 도 불러와지는 것까지만 확인했다.

## 화면과 API (스토리보드 I-01)

| 화면 | 호출 |
|---|---|
| `login.html` | `auth/signup` · `auth/login` · `teams/join` |
| `meetings.html` | `teams/{id}/meetings` (POST · GET) · `upload` · `auth/me` |
| `detail.html` | `meetings/{id}` (GET · PUT · DELETE) · `todos/{id}` (PUT) · `meetings/{id}/comments` (POST · GET) · `comments/{id}` (DELETE) |
| `todos.html` | `teams/{id}/todos` · `todos/{id}` (PUT · DELETE) · `me/todos` |
| `team.html` | `teams` (POST · GET) · `teams/{id}` (PUT) · `teams/join` · `teams/{id}/members` · `teams/{id}/code` · `teams/{id}/activities` |
| `profile.html` | `auth/me` (GET · PUT) · `auth/logout` · `me/todos` · `me/activities` |

표와 다른 곳은 `auth/logout` 한 칸이다. 확정 디자인의 "로그아웃" 버튼이 `profile.html` 에 있어서 거기서 부른다.
담당자 선택지는 회의록 단건 응답의 `members` 와 할 일 응답의 `assignable` 로 받아서, 화면이 팀원 목록 API 를 따로 부르지 않는다.

## 성능 (로컬 측정)

기준: API 100ms 이내(받아쓰기 · 인증 2종 제외), 가입 · 로그인 250ms 이내, 목록 렌더 50ms 이내.
SQLite · 같은 PC · 회의록 50건 기준으로 요청 40회의 중앙값과 95번째 백분위를 쟀다.

| 항목 | 결과 | 기준 |
|---|---|---|
| 가입 · 로그인 (bcrypt) | 중앙값 123ms, 최대 136ms | 250ms |
| `GET /api/auth/me` | 4ms (p95 6ms) | 100ms |
| `GET /api/teams/{id}/meetings` (50건) | 46ms (p95 60ms) | 100ms |
| `GET /api/teams/{id}/todos` | 12ms (p95 29ms) | 100ms |
| `GET /api/me/todos` | 10ms (p95 13ms) | 100ms |
| `GET /api/teams/{id}/members` | 7ms (p95 11ms) | 100ms |
| `GET /api/teams/{id}/activities` | 7ms (p95 10ms) | 100ms |
| `GET /api/meetings/{id}` | 8ms (p95 11ms) | 100ms |
| `GET /api/meetings/{id}/comments` | 6ms (p95 12ms) | 100ms |
| 목록 화면 렌더 (카드 50개) | 2ms (최대 3ms) | 50ms |

bcrypt 비용은 11 이다. 기본값 12 에서는 로그인이 최대 252ms 로 기준을 넘었다.
받아쓰기는 Gemini 응답 시간이라 측정하지 않았다 (60초 이내가 제약).
