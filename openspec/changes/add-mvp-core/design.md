# Design

## Context

코드가 없는 백지 상태다. 구현 스택과 제약은 정의서에서 이미 정해졌다(Backend FastAPI + SQLAlchemy, Frontend Vanilla JS + Tailwind CDN, 로컬 SQLite · 배포 Neon, Gemini 하나로 받아쓰기와 세 항목 구분). 화면 6종의 확정 디자인은 `publish/` 에 있고 `theme.js` 가 팔레트 · 공통 클래스 · 테마 토글을 한 곳에서 정의한다. 동기와 범위는 proposal.md 를 따른다. 요구 동작은 specs(auth · team · meeting · todo · comment · activity) 가 정한다.

폴더는 정의서 7-5 를 따른다: 루트 `.env`(키 두 줄) · `.env.example` · `backend/` · `frontend/` · `.gitignore`(`.env` 제외).

## Goals / Non-Goals

**Goals:**
- API 26개 · DB 7테이블 · 화면 6종(상태 62종)을 정의서 그대로 구현한다.
- 화면은 `publish/*.html` 의 구조와 클래스를 옮기고 새로 디자인하지 않는다.
- 같은 코드로 로컬(SQLite)과 배포(Neon)를 모두 돌린다.

**Non-Goals:**
- 실시간 녹음, 화자 구분, 캘린더 · 메일 연동, owner / member 외의 권한 등급, 분할 업로드, 푸시 알림.
- 마이크로서비스 분리, Sentry 같은 외부 관측 도구(logging 모듈만).
- 갱신 토큰, 서버 쪽 로그아웃 블랙리스트.

## Decisions

### D1. 정적 파일 위치와 화면 이식
`publish/` 의 HTML 9개 중 규격 3개(`index.html`, `components.html`, `theme.js` 의 STATE 바 부분)는 확인용이다. 구현에는 화면 6개(`login` · `meetings` · `detail` · `todos` · `team` · `profile`)와 `theme.js` 를 `frontend/` 로 옮기고, StaticFiles 가 `/login.html` 처럼 확장자를 붙여 서빙한다. `stateBar` 와 `#note` 줄(API 경로와 상태 코드를 적은 퍼블리싱 확인용 줄)은 옮기지 않는다. 토스트 본문의 API 경로 문구도 사람이 읽는 문구(예: "진행 칸으로 옮겼습니다" 같은 뜻)로 바꾼다.
- **대안:** 화면을 프레임워크(React 등)로 다시 쓰기 - 정의서가 Vanilla JS 로 고정했고 "AI 가 화면을 새로 디자인하지 않음" 에 어긋나 기각.

### D2. 디자인 규칙의 두 층
버튼은 `window.UI.btnPrimary / btnGhost / btnDanger`(`h-11`)만 쓰고, 카드는 `rounded-xl`, 패널은 `rounded-2xl` 만 쓴다. 클래스는 화면에서 조합하지 않고 `window.UI` · `STRIPE` · `LABEL` 의 이름을 가져다 쓴다. publish HTML 이 규칙을 어긴 곳(`team.html` 이름 저장의 `h-9` + `bg-blue-dot`, `detail.html` 수정 · 삭제 · 삭제 확인의 `h-10`)은 `h-11` 버튼 이름으로 바꾼다.

**허용 목록(예외):** 카드 안의 보조 컨트롤 - 배지 · 칩 · 탭 · `select` · 기한 입력칸 (`h-7`, `rounded-md`, `rounded-lg`) 과 업로드 진행 막대의 인라인 `style="width:..%"` 는 허용한다. 이 목록 밖의 새 크기 · 새 모서리 · 새 색은 만들지 않는다. 새 색이 필요하면 `theme.js` 팔레트에 먼저 등록한다.
- **대안:** 규칙 전체 엄격 적용 - 확정 디자인의 모양이 바뀌어 기각. HTML 그대로 복사 - 한 곳에서만 정의한다는 원칙이 깨져 기각.

### D3. 화면 문구
사용자에게 보이는 문구는 publish HTML 기준(~않음체)으로 쓴다. 스토리보드의 합쇼체와 다른 곳(예: 로그인 실패는 "이메일 또는 비밀번호가 올바르지 않음")은 HTML 을 따르고, 그 문구를 spec 의 Scenario 에 그대로 적었다.

### D4. 권한 판정은 서버, 화면은 보조
서버가 모든 쓰기 API 에서 최종 판정한다(owner 전용은 `OWNER_ONLY`, 그 외는 `FORBIDDEN`). 화면이 role 을 추측하지 않도록 응답에 판정 결과를 싣는다: 댓글은 `can_delete`(정의서 7-1), 회의록은 `can_edit`, 할 일은 `can_delete` 를 더한다(이 change 가 정의서 7-1 에 더하는 필드). 권한 없는 컨트롤은 `team.html` member 상태와 같은 방식으로 흐리게 하고 누를 수 없게 한다.

### D5. 응답 모양과 오류
오류 본문은 `{code, msg}` 이고 코드는 화면 10종(`EMAIL_INVALID` · `PASSWORD_TOO_WEAK` · `TOKEN_EXPIRED` · `INVITE_NOT_FOUND` · `MEETING_NOT_FOUND` · `EMAIL_DUPLICATED` · `TEAM_FULL` · `PAYLOAD_TOO_LARGE` · `UNSUPPORTED_MEDIA_TYPE` · `INVALID_CREDENTIALS`)에 `FORBIDDEN` · `OWNER_ONLY` · `VALIDATION_ERROR` · `NOT_FOUND` 와, 이 change 가 더하는 `UNAUTHORIZED`(현재 비밀번호 확인 실패, 401)이다. 목록 응답에는 body 를 싣지 않고, 필드는 정의서 7-1 을 따른다. 시각은 UTC ISO 8601 로 저장하고 화면에서 현지 시간으로 보인다.

### D6. 받아쓰기와 세 항목 구분
`POST /api/upload` 는 파일을 받아 Gemini 로 받아쓰고 본문 텍스트만 돌려준다(저장 없음). 저장(`POST /api/teams/{id}/meetings`)은 본문을 같은 모델로 요약 · 결정사항 · 할 일로 나눠 함께 저장한다. 결정사항은 줄바꿈으로 구분한 TEXT 한 칸이고, 할 일은 한 줄에 하나(`내용 | 담당자 | 기한`)로 받아 `todos` 행으로 푼다. 담당자 이름이 팀원과 맞지 않거나 비면 `assignee_id` 는 비우고 화면에서 "미정" 이다. 본문 수정(PUT)은 받아쓰기와 요약을 다시 돌리지 않는다. 형식 판정은 확장자가 아니라 파일 내용으로 한다.
- 모델은 정의서가 지정한 `GEMINI_MODEL` 환경 변수 하나를 쓴다. 키와 모델명은 루트 `.env` 에서만 읽고 코드에 두지 않는다.

### D7. 인증
bcrypt 해시로 저장하고 JWT 는 24시간, 갱신 없음이다. `JWT_SECRET` 은 배포 환경에서만 등록하고 로컬은 코드 기본값을 쓴다. 토큰은 `localStorage` 에 둔다(정의서가 검증하지 않고 두는 전제). 비밀번호 변경은 새 비밀번호가 있을 때만 현재 비밀번호를 요구한다(`UNAUTHORIZED` 401).

로그인 · 가입 응답과 `GET /api/auth/me` 에는 `team_id`(없으면 비어 있음)를 싣는다. 매핑표(D12)의 `todos.html` 과 `meetings.html` 은 `teams/{id}/...` 를 부르는데 팀 id 를 얻는 호출이 표에 없으므로, 화면은 로그인 · 합류 · 팀 생성 응답의 `team_id` 를 `localStorage` 에 두고 쓴다. `auth/me` 는 화면 머리의 팀 이름과 role 을 채울 때 다시 읽는다. 팀이 바뀌는 곳(합류 · 팀 생성)에서는 저장값을 갱신한다.

### D8. 데이터와 환경 분리
7테이블: `users` · `teams` · `memberships` · `meetings` · `todos` · `comments` · `activities`. 한 사람은 한 팀에만 속하므로 `memberships` 에는 사용자당 한 줄만 쓴다. `activities.kind` 는 5종으로 고정한다. `DATABASE_URL` 이 있으면 Neon, 없으면 로컬 SQLite 이며 SQLAlchemy 로 양쪽을 같은 코드로 쓴다. 회의록을 지우면 딸린 할 일과 댓글도 함께 지운다(외래키 연쇄 삭제).

### D9. 끌어서 옮기기
`publish/todos.html` 의 포인터 이벤트 방식을 그대로 쓴다. 놓는 순간 한 번만 `PUT /api/todos/{id}` 를 부르고, 실패하면 원래 칸으로 되돌린다. 좁은 화면(칸이 세로로 쌓임)은 카드를 눌러 칸을 고른다.

### D10. 배포
로컬은 일체형(StaticFiles)이고 배포는 Vercel + Vercel Storage Neon 이다. CORS 는 허용 도메인을 명시한다. `.env` 와 `.env.example` 은 `GEMINI_API_KEY` · `GEMINI_MODEL` 두 줄뿐이고 `JWT_SECRET` · `DATABASE_URL` · CORS 는 코드 기본값이나 배포 환경 변수로 둔다.

### D11. Swagger UI
FastAPI 의 `/docs`(Swagger UI)와 `/openapi.json` 을 로컬에서 켜서 화면 없이도 API 를 눌러 시험할 수 있게 한다. 보호된 API 는 Authorize 에 JWT 를 넣어 부른다. 켜고 끄는 기준은 새 환경 변수가 아니라 이미 있는 분기(`DATABASE_URL` 유무)를 쓴다: 로컬(없음)은 켜고 배포(있음)는 끈다. `.env` 는 키 두 줄만 둔다는 규칙(정의서 7-5)을 지키기 위해서다.
- **대안:** 배포에서도 항상 켜기 - 인터넷에서 누구나 API 목록을 보게 되어 기각. 별도 `ENABLE_DOCS` 변수 - 환경 변수를 더 만들지 않는다는 규칙에 어긋나 기각.

### D12. 매핑표 준수 (스토리보드 I-01)
화면별 API 호출은 스토리보드 I-01 통합 매핑표를 따른다. 화면이 표 밖의 API 를 부르지 않고, 표의 경로는 모두 어느 화면에선가 쓰여 고유 경로 26개 · 쓰이지 않는 경로 0개가 된다.

| 화면 | 호출 | 칸 |
|---|---|---|
| login.html | auth/signup · auth/login · teams/join | 3 |
| meetings.html | teams/{id}/meetings (POST · GET) · upload · auth/me · ~~auth/logout~~ | 4 |
| detail.html | meetings/{id} (GET · PUT · DELETE) · todos/{id} (PUT) · meetings/{id}/comments (POST · GET) · comments/{id} (DELETE) | 7 |
| todos.html | teams/{id}/todos · todos/{id} (PUT · DELETE) · me/todos | 4 |
| team.html | teams (POST · GET · PUT) · teams/join · teams/{id}/members · teams/{id}/code · teams/{id}/activities | 7 |
| profile.html | auth/me (GET · PUT) · me/todos · me/activities · auth/logout | 5 |

**표와 다른 한 칸:** 표는 `auth/logout` 을 `meetings.html` 에 적었지만 확정 HTML 의 "로그아웃" 버튼은 `profile.html` 에만 있다. 확정 디자인을 지키기 위해 버튼은 `profile.html` 에 두고 거기서 호출한다. 합계는 30칸 · 고유 26개로 그대로다. 표의 `team.html` 이 쓰는 `PUT /api/teams`(`/{id}`)는 팀 이름 변경이다.

## Risks / Trade-offs

- **세 항목 구분이 모델 응답에 의존한다** → 프롬프트에 "없는 사실을 보태지 않음 · 합의가 끝난 것만 · 담당자 없으면 미정" 을 명시하고, 응답 형식이 어긋나면 세 칸을 비우고 저장은 유지한다(결정이 없는 회의와 구분되도록 오류 로그를 남긴다).
- **받아쓰기 60초 제한과 25MB 상한이 맞지 않을 수 있다** → 업로드 상한과 시간 제한을 각각 검사하고 초과는 413 으로 거절한다. 분할 업로드는 범위 외다.
- **기한이 자유 글자라 "지남" 판정이 부정확하다** → 서버는 판정하지 않는다(정의서). 화면은 정해 둔 지난 표현과 날짜 형식만 인식한다.
- **허용 목록 예외가 규칙을 흐릴 수 있다** → 목록을 spec 이 아니라 이 design 에 고정하고, 새 항목은 목록에 먼저 더한 뒤 쓴다.
- **회의록 삭제의 연쇄 삭제는 되돌릴 수 없다** → 삭제 확인 화면에서 미리 알린다(D-08).

## Open Questions

- 멤버가 초대코드를 복사하는 것을 막을지: 스토리보드 F-08 은 owner 전용을 이름 변경 · 코드 재발급 · 할 일 삭제 셋으로 적었고, `team.html` 의 member 상태는 복사 버튼도 막는다. 구현은 `team.html` 을 따른다. 달라지면 `team` spec 의 "member 권한 표시" 만 고치면 된다.
- 연쇄 삭제 범위: 정의서는 "딸린 할 일" 만 적었다. 댓글도 함께 지우도록 했다(고아 행을 남기지 않기 위해). 이견이 있으면 tasks 의 DB 단계에서 바꾼다.
