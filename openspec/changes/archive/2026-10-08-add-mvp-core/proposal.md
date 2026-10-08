# Proposal

## Why

로그인한 팀이 함께 쓰는 회의록 서비스 MeetingNote Pro 를 처음부터 만든다. 녹취를 받아쓴 본문이 요약 · 결정사항 · 할 일로 나뉘고, 할 일은 칸반으로 추적되며, 댓글과 활동 기록이 남는다. 정의서(`docs/` 프로그램 정의서)는 기능 6종을 1회차에 모두 구현하도록 정했고, 화면은 `publish/` 의 확정 디자인이 곧 명세다. 지금은 코드가 없고 OpenSpec 의 spec 도 비어 있어, 이 change 가 첫 기준선이 된다.

## What Changes

- Backend(FastAPI + SQLAlchemy)와 Frontend(Vanilla JS + Tailwind CDN)를 새로 만든다. 로컬은 SQLite, 배포는 Neon, 코드는 한 벌이다.
- API 26개와 DB 7테이블, 화면 6종(상태 62종)을 구현한다. 화면은 `publish/*.html` 을 새로 디자인하지 않고 그 색 · 클래스 규칙(`theme.js` 의 `window.UI` · `STRIPE` · `LABEL`)을 그대로 따른다.
- 녹취 업로드(mp3 · wav, 4.5MB 이하) → Gemini 받아쓰기 → 저장 시 요약 · 결정사항 · 할 일 구분.
- 정의서 · 스토리보드 · publish 가 어긋난 곳은 explore 에서 다음과 같이 정했다. 아래 결정은 spec 과 design 에 반영한다.
  - 비밀번호 변경은 현재 비밀번호를 함께 받고, 틀리면 `UNAUTHORIZED` 401 (이름만 바꿀 때는 받지 않음).
  - 회의록 수정은 제목 · 시각 · 참석자 · 본문을 입력칸으로 연다 (화면은 6종 그대로).
  - 할 일 기한은 자유 글자이며, 배지를 누르면 인라인 입력칸이 열린다. 상세 화면에도 같은 칸을 둔다.
  - 초대코드 없이 가입하면 가입만 되고, 팀이 없으므로 `team.html` 의 onboard 에서 팀을 만든다.
  - 버튼은 `h-11` 하나, 카드 `rounded-xl` · 패널 `rounded-2xl`. 배지 · 칩 · 탭 · `select` · 기한 입력칸 같은 보조 컨트롤과 진행 막대의 인라인 style 은 허용 목록 예외로 둔다.
  - 사용자에게 보이는 문구는 publish HTML 기준(~않음체). `#note` 줄과 STATE 바는 구현하지 않는다.
  - 권한이 없는 버튼은 흐리게 하고 누를 수 없게 한다. 판정은 서버가 응답의 `can_edit` · `can_delete` 로 내려 준다.
- 화면별 API 호출은 스토리보드 I-01 통합 매핑표(화면 x API x DB)를 따른다. 고유 경로 26개 · 쓰이지 않는 경로 0개이며, 표와 다른 곳은 로그아웃 한 칸뿐이다(확정 HTML 대로 버튼이 `profile.html` 에 있음).
- Swagger UI(`/docs`)를 로컬에서 켜서 화면 없이 API 를 눌러 시험할 수 있게 한다. 배포(`DATABASE_URL` 있음)에서는 끈다.
- 로그인 · 가입 응답과 `auth/me` 에 `team_id` 를 더한다. 표에 팀 id 를 얻는 호출이 없어서, 화면이 이 값을 `localStorage` 에 두고 쓴다.
- 개발이 끝나면 pytest 를 마무리해 전체를 돌리고 통과 · 실패 · 건너뜀과 실패 원인을 보고한다. tasks 맨 아래에 사람이 눈으로 확인하는 수락 항목 하나를 둔다.
- 오류 코드 목록에 `UNAUTHORIZED` 를 더하고, 회의록 응답에 `can_edit`, 할 일 응답에 `can_delete` 를 더한다 (정의서 7-1 · 7-2 보강).

## Capabilities

### New Capabilities

- `auth`: 회원가입 · 로그인 · JWT(24h) · bcrypt · 내 정보 조회와 수정(이름, 현재 비밀번호 확인 후 변경) · 로그아웃
- `team`: 팀 생성 · 목록 · 초대코드 발급과 재발급 · 합류 · 멤버 목록 · 팀 이름 변경(owner) · 정원 6명 · owner 와 member 권한
- `meeting`: 녹취 업로드와 받아쓰기 · 요약 / 결정사항 / 할 일 구분 · 회의록 CRUD · 제목과 참석자 검색 · 기간 필터
- `todo`: 할 일 칸반 3열(대기 · 진행 · 완료) · 끌거나 눌러서 상태 변경 · 담당자 배정 · 기한 입력 · 삭제(owner)
- `comment`: 회의록 댓글 작성 · 목록 · 삭제(쓴 사람과 owner) · 500자 제한
- `activity`: 팀 활동 기록과 내 활동 · 행위자 · 시점 · 대상 · kind 5종

### Modified Capabilities

(없음 - 기존 spec 이 없음)

## Impact

- 새 디렉터리: `backend/`(FastAPI), `frontend/`(publish 의 HTML 과 `theme.js` 를 옮겨 실제 API 와 연결). 프로젝트 루트의 `.env` 는 `GEMINI_API_KEY` · `GEMINI_MODEL` 두 줄만 두고 `.env.example` 을 함께 만든다.
- 개발 도구: pytest(spec 시나리오 단위 테스트, Gemini 는 가짜로 대체), Swagger UI(FastAPI 기본 제공, 로컬 전용).
- 외부 의존: Google Gemini API(받아쓰기와 세 항목 구분), Vercel + Neon(배포).
- 범위 외: 실시간 녹음, 화자 구분, 외부 연동(캘린더 · 메일), 3등급 이상의 권한, 분할 업로드, 푸시 알림.
- 배포(Vercel + Neon)와 로컬 · 배포 환경 분리는 기능이 아니라 구현 방식이므로 별도 spec 없이 design.md 에 둔다.
