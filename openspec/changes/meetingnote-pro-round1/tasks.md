# Tasks

## 1. 프로젝트 뼈대와 환경

- [x] 1.1 루트에 `backend/` · `frontend/` 를 만들고, `.env.example`(키 이름 `GEMINI_API_KEY` · `GEMINI_MODEL` 두 줄만)과 `.gitignore`(`.env` 제외)를 둔다. `ls` 로 구조와 `.env.example` 의 두 줄만 있는 것을 확인한다
- [x] 1.2 FastAPI + SQLAlchemy + bcrypt + JWT + Gemini 클라이언트 의존성을 `backend/requirements.txt` 에 적고 설치한다. `pip install -r backend/requirements.txt` 가 성공하고 `pytest --version` 이 나오는지 확인한다
- [x] 1.3 앱 진입점(`/api` 라우터, StaticFiles 로 `frontend/` 서빙, CORS 허용 도메인 명시, `{code, msg}` 오류 본문, 키 4종 환경 변수 읽기)을 만든다. `uvicorn` 으로 띄워 `/login.html` 이 서빙되고 없는 API 경로가 `{code, msg}` 를 돌려주는 테스트가 통과하는지 확인한다

- [x] 1.4 Swagger UI 를 켠다(design D11). 로컬(`DATABASE_URL` 없음)에서 `/docs` 가 열려 모든 `/api` 경로가 보이고, 로그인 후 받은 JWT 를 Authorize 에 넣어 `GET /api/auth/me` 를 화면에서 호출하면 200 이 오는지 확인한다. `DATABASE_URL` 이 있으면 `/docs` 와 `/openapi.json` 이 404 인 것을 테스트로 확인한다

## 2. 데이터 계층 (design D8)

- [x] 2.1 `users` · `teams` · `memberships` · `meetings` · `todos` · `comments` · `activities` 7테이블 모델을 만든다. `activities.kind` 는 5종만 허용하고 `DATABASE_URL` 유무로 Neon / SQLite 를 고른다. 모델 테스트로 테이블 7개 생성과 kind 5종 외 값 거부를 확인한다
- [x] 2.2 회의록 삭제 시 딸린 할 일과 댓글이 연쇄 삭제되고, 사용자당 membership 이 한 줄뿐임을 테스트로 확인한다

## 3. auth (specs/auth)

- [x] 3.1 `POST /api/auth/signup` 을 구현한다(이메일 형식 · 8자 이상 · bcrypt · 201 + JWT, `EMAIL_INVALID` · `PASSWORD_TOO_WEAK` · `EMAIL_DUPLICATED`). 시나리오 4개를 테스트로 만들어 통과시킨다
- [x] 3.2 `POST /api/auth/login` 과 JWT 24시간 검증을 구현한다(`INVALID_CREDENTIALS` 한 메시지, 만료는 `TOKEN_EXPIRED`). 존재하지 않는 이메일과 틀린 비밀번호가 같은 응답이고 만료 토큰이 401 인지 테스트로 확인한다
- [x] 3.3 `GET /api/auth/me`(id · name · email · role) · `PUT /api/auth/me`(이름만, 또는 현재 비밀번호 + 새 비밀번호, 틀리면 `UNAUTHORIZED`) · `POST /api/auth/logout`(200 만)을 구현한다. 이름만 보내면 비밀번호 유지, 현재 비밀번호 틀림 401, 약한 비밀번호 400 을 테스트로 확인한다
- [x] 3.4 `login.html` 을 `frontend/` 로 옮기고 `theme.js` 의 `window.UI` 이름으로 클래스를 바꾼다. STATE 바와 `#note` 줄은 뺀다. 11개 상태를 브라우저에서 눌러 보며 문구가 spec 과 같은지 확인한다. 로그인 · 가입 응답의 `team_id` 를 화면이 `localStorage` 에 저장해 두고(design D12), 팀이 있으면 `meetings.html`, 없으면 `team.html` 로 가는지 확인한다. 이 화면이 부르는 API 는 매핑표대로 signup · login · teams/join 셋뿐이다
- [x] 3.5 `profile.html` 에 "현재 비밀번호" 칸과 `UNAUTHORIZED` 오류 상태를 더해 구현한다(스토리보드 7개 + 현재 비밀번호 오류 1개 = 8개). "로그아웃" 버튼은 확정 HTML 대로 이 화면에 두고 `POST /api/auth/logout` 에 연결한다(매핑표와 다른 한 칸, design D12). 브라우저에서 확인 칸 불일치가 서버 호출 없이 막히는지, 이름만 저장은 현재 비밀번호 없이 되는지 확인한다

## 4. team (specs/team)

- [x] 4.1 `POST /api/teams`(owner 지정 + 초대코드 발급) · `GET /api/teams` · `POST /api/teams/join`(`INVITE_NOT_FOUND` · `TEAM_FULL`, 6명 정원) · `GET /api/teams/{id}/members`(todo_count 포함)를 구현하고 시나리오를 테스트로 통과시킨다
- [x] 4.2 `PUT /api/teams/{id}/code`(owner, 이전 코드 폐기) · `PUT /api/teams/{id}`(owner, `OWNER_ONLY`)를 구현한다. member 로 부르면 403 `OWNER_ONLY` 이고 기존 멤버십은 유지됨을 테스트로 확인한다
- [x] 4.3 `team.html` 을 옮겨 8개 상태를 구현한다. 이름 저장 버튼을 `btnPrimary`(`h-11`)로 바꾸고, member 로 들어오면 이름 · 복사 · 재발급이 흐리게 되어 눌러도 동작하지 않는지 브라우저에서 확인한다

## 5. meeting (specs/meeting)

- [x] 5.1 `POST /api/upload`(mp3 · wav 내용 판정, 25MB 상한, 받아쓰기 60초, 본문만 반환)를 구현한다. Gemini 호출은 테스트에서 가짜로 바꾸고, 415 · 413 · 200 시나리오를 테스트로 통과시킨다
- [x] 5.2 세 항목 구분 모듈을 만든다(요약 3~5줄 · 합의된 것만 · `내용 | 담당자 | 기한` 한 줄씩). 가짜 응답으로 결정 없음 · 할 일 없음 · 담당자 미정이 각각 비거나 "미정" 으로 저장되고, 응답 형식이 어긋나면 세 칸을 비운 채 회의록은 저장되는지 테스트한다
- [x] 5.3 `POST` · `GET`(목록, body 제외 + 집계 3개, met_at 내림차순, `?q=` 제목과 참석자만, `?from=&to=`) · `GET /api/meetings/{id}`(body 포함, `MEETING_NOT_FOUND`)를 구현한다. 검색이 본문을 보지 않는 것과 0건이 200 + 빈 배열인 것을 테스트로 확인한다
- [x] 5.4 `PUT` · `DELETE /api/meetings/{id}` 를 구현한다. 올린 사람과 owner 만 허용하고 응답에 `can_edit` 을 싣는다. 본문을 고쳐도 세 항목이 그대로이고 삭제가 할 일 · 댓글을 함께 지우는지 테스트로 확인한다
- [x] 5.5 `meetings.html` 을 옮겨 11개 상태를 구현한다. 진행 막대의 인라인 style 은 허용 목록 예외로 둔다. 새 회의록 패널에서 업로드 → 본문 채움 → 정리하기 → 목록 맨 위 추가와 입력칸 비움을 브라우저에서 확인한다
- [x] 5.6 `detail.html` 을 옮겨 13개 상태를 구현한다. 수정 상태에서 제목 · 시각 · 참석자 · 본문이 입력칸이 되게 하고, 수정 · 삭제 버튼은 `h-11` 버튼 이름으로 바꾼다. `can_edit` 이 false 면 흐리게 되는지, 삭제 확인 문구가 spec 과 같은지 브라우저에서 확인한다

## 6. todo (specs/todo)

- [x] 6.1 `GET /api/teams/{id}/todos` · `GET /api/me/todos`(meeting_title · assignee_name 포함, status 다음 due_text 정렬) · `PUT /api/todos/{id}`(status · 담당자 · due_text) · `DELETE /api/todos/{id}`(owner, `can_delete` 포함)를 구현한다. 되돌림 허용, member 삭제 403 `OWNER_ONLY` 를 테스트로 통과시킨다
- [x] 6.2 `todos.html` 을 옮겨 12개 상태를 구현한다. 포인터 이벤트 끌기(네이티브 `draggable` 금지)와 눌러서 칸 고르기, 담당자 배지 선택, 기한 배지 클릭 → 인라인 입력칸(Enter 나 포커스 잃을 때 저장, 비우면 "미정")을 만든다. 데스크톱 폭에서 끌기, 360px 폭에서 눌러 고르기가 모두 동작하는지 브라우저에서 확인한다
- [x] 6.3 `detail.html` 의 할 일 칸에도 담당자 옆에 같은 기한 입력칸을 더한다. 담당자와 기한을 바꾸면 활동 기록과 `PUT /api/todos/{id}` 가 한 번씩만 불리는지 확인한다
- [x] 6.4 기한 지남 표시(붉은 띠 + 붉은 글자, 완료 제외)와 담당자 필터(서버 재호출 없음, "미정" 포함)를 구현하고 브라우저에서 확인한다

## 7. comment (specs/comment)

- [x] 7.1 `POST` · `GET /api/meetings/{id}/comments`(created_at 오름차순, `can_delete`, 500자 제한) · `DELETE /api/comments/{id}`(쓴 사람과 owner, 아니면 403 `FORBIDDEN`)를 구현한다. 501자 400, 남의 댓글 삭제 403 을 테스트로 통과시킨다
- [x] 7.2 `detail.html` 의 댓글 영역을 API 에 연결하고 댓글 입력 · 등록 · 없음 · 삭제 상태를 구현한다. `can_delete` 가 false 인 댓글의 삭제가 흐린지, 등록 후 입력칸이 비워지는지 브라우저에서 확인한다

## 8. activity (specs/activity)

- [x] 8.1 5종 kind 를 남기는 훅을 meeting · todo · comment · team 흐름에 붙이고 서버가 완성 문장을 만든다. 이름 · 비밀번호 변경은 기록하지 않는 것과 kind 5종 외 값이 없는 것을 테스트로 확인한다
- [x] 8.2 `GET /api/teams/{id}/activities`(최근 순 50건) · `GET /api/me/activities` 를 구현하고 빈 배열 200 을 테스트로 확인한다
- [x] 8.3 `team.html` 과 `profile.html` 의 활동 목록을 연결하고 kind 별 띠 색(meeting_add blue, todo_assign orange, todo_done green, comment_add · member_join purple)을 확인한다

## 9. 통합과 배포

- [x] 9.1 `window.UI` · `STRIPE` · `LABEL` 이름만 쓰는지 검사한다. `frontend/` 에서 `h-9` · `h-10` 이 버튼에 없고 `!important` 가 없고 허용 목록 밖의 인라인 style 이 없는지 `grep` 으로 확인한다
- [x] 9.2 정의서 시나리오 4개(리더 흐름, 팀원 칸반, 신규 합류자 검색과 댓글, 내 정보 변경과 활동 확인)를 브라우저에서 처음부터 끝까지 한 번씩 돌린다. 라이트와 다크, 360px 폭에서 깨지는 화면이 없는지 확인한다
- [x] 9.3 Vercel + Neon 배포 설정을 더하고 `DATABASE_URL` 유무로 Neon / SQLite 가 바뀌는 것을 확인한다. 배포 환경의 `JWT_SECRET` · `GEMINI_*` 등록 방법을 `README.md` 에 적고, 적힌 명령대로 로컬에서 서버가 뜨는지 확인한다
- [x] 9.4 성능 지표를 측정한다(일반 API 100ms 이내, 가입 · 로그인 250ms 이내, 목록 렌더 50ms 이내). 측정 방법과 결과를 `README.md` 에 적고 기준 안에 드는지 확인한다

- [x] 9.5 매핑표 검증(스토리보드 I-01, design D12). `frontend/` 의 화면 6개에서 `fetch` 호출을 `grep` 으로 뽑아 화면별 경로가 표와 같은지 대조한다. 같은 경로를 한 번만 세어 고유 26개이고 어느 화면에서도 쓰지 않는 경로가 0개인지 확인한다. 표와 다른 곳은 로그아웃 한 칸(`profile.html`)뿐이어야 한다

## 10. pytest 실행과 보고

- [x] 10.1 개발이 끝나면 pytest 를 마무리한다. spec 6개의 Scenario 를 테스트 이름과 대조해 빠진 시나리오의 테스트를 보강하고, 외부 호출(Gemini)은 가짜로 바꾼다. `pytest backend -q` 전체를 실행해 오류 없이 끝나는지 확인한다
- [x] 10.2 실행 결과를 사용자에게 보고한다. 통과 · 실패 · 건너뜀 개수와 소요 시간, 실패한 테스트의 이름과 원인을 적는다. 실패가 있으면 숨기지 않고 그대로 보고하며, 고친 뒤 다시 돌린 결과도 함께 적는다

## 11. 수락 (사람이 눈으로 확인)

- [ ] 11.1 사용자가 로컬 서버를 직접 열어 정의서 시나리오 4개를 처음부터 끝까지 따라가고, 62개 상태가 스토리보드와 같은 모양인지, 라이트 · 다크 · 360px 폭에서 깨지지 않는지, `/docs`(Swagger UI)에서 API 를 직접 눌러 보는 것이 되는지 눈으로 확인한다. 사용자가 확인했다고 답하기 전에는 이 항목을 체크하지 않는다

## Workflow follow-up

- 구현이 끝나면 change 를 검토한 뒤 archive 한다.
- archive 뒤 `openspec/specs/` 에 spec 6개가 합쳐졌는지 확인한다.
