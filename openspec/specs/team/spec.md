# team Specification

## Purpose
한 사람이 한 팀에 속해 회의록과 할 일을 함께 쓰도록 팀을 만들고, 초대코드로 합류시키며, 팀 이름 · 멤버 · 권한을 관리하는 기능이다.

## Requirements

### Requirement: 팀 생성
<!-- 근거: F-02 / team.html -->
소속 팀이 없는 사용자는 팀 이름을 입력해 팀을 만들 수 있어야 한다(SHALL). 만든 사람은 그 팀의 owner 가 되고, 팀에는 초대코드가 하나 발급된다. 한 사람은 한 팀에만 속한다.

#### Scenario: 소속 팀 없는 로그인
- **WHEN** 로그인했지만 소속 팀이 0개이다
- **THEN** `team.html` 의 "아직 소속 팀이 없음" 상태로 가고, 회의록 화면으로는 갈 수 없다

#### Scenario: 팀 만들기
- **WHEN** 팀 이름을 넣고 "만들기" 를 누른다
- **THEN** `POST /api/teams` 가 팀을 만들고 사용자는 owner 가 되며 팀 설정 화면이 보인다

### Requirement: 초대코드로 합류
<!-- 근거: B-11 · F-02 · F-03 · F-06 / team.html, login.html -->
사용자는 초대코드로 팀에 합류할 수 있어야 한다(SHALL). 없는 코드는 404 `INVITE_NOT_FOUND`, 정원(6명)이 찬 팀은 409 `TEAM_FULL` 이다. 합류에 실패해도 가입 계정은 그대로 유지한다.

#### Scenario: 합류 성공
- **WHEN** 맞는 초대코드로 `POST /api/teams/join` 을 부른다
- **THEN** 사용자는 member 로 합류하고 활동 기록에 `member_join` 이 남는다

#### Scenario: 없는 초대코드
- **WHEN** 존재하지 않는 코드를 넣는다
- **THEN** 404 `INVITE_NOT_FOUND` 를 받고 화면은 "없는 초대코드" 알림을 보인다

#### Scenario: 정원 초과
- **WHEN** 이미 6명인 팀의 코드로 합류한다
- **THEN** 409 `TEAM_FULL` 을 받고 "팀 정원이 찼음" 알림이 보인다

### Requirement: 팀 설정 화면
<!-- 근거: F-01 / team.html -->
팀 설정 화면은 팀 이름, 초대코드, 멤버 목록, 활동 기록을 보여줘야 한다(SHALL). 멤버 목록은 이름 · 이메일 · role 과 1인당 할 일 수를 담고, 팀당 6명 이내이며 "4 / 6" 처럼 정원을 함께 보인다.

#### Scenario: 팀 설정 열기
- **WHEN** 소속 팀이 있는 사용자가 `team.html` 을 연다
- **THEN** 팀 이름 · 초대코드 · 멤버 카드 · 활동 기록이 보이고 멤버 수와 정원이 함께 표시된다

### Requirement: 초대코드 복사와 재발급
<!-- 근거: F-04 · F-05 / team.html -->
초대코드는 팀당 하나이며 사람마다 따로 발급하지 않는다(MUST). owner 는 코드를 다시 발급할 수 있고, 이전 코드는 더 쓸 수 없으며 이미 합류한 멤버는 그대로 둔다.

#### Scenario: 코드 복사
- **WHEN** "복사" 를 누른다
- **THEN** 코드가 복사되고 "초대코드를 복사함" 알림이 보인다

#### Scenario: 코드 재발급
- **WHEN** owner 가 "재발급" 을 누른다
- **THEN** `PUT /api/teams/{id}/code` 가 200 으로 새 코드를 돌려주고 이전 코드는 합류에 쓸 수 없으며 기존 멤버십은 영향받지 않는다

### Requirement: 팀 이름 변경
<!-- 근거: F-07 / team.html -->
팀 이름 변경은 owner 만 할 수 있어야 한다(SHALL). member 가 부르면 403 `OWNER_ONLY` 를 돌려준다.

#### Scenario: owner 가 이름 저장
- **WHEN** owner 가 팀 이름을 바꾸고 "이름 저장" 을 누른다
- **THEN** `PUT /api/teams/{id}` 가 200 을 돌려주고 새 이름이 보인다

#### Scenario: member 가 이름 변경 시도
- **WHEN** member 가 같은 API 를 부른다
- **THEN** 403 `OWNER_ONLY` 를 받는다

### Requirement: member 권한 표시
<!-- 근거: F-08 / team.html -->
권한 등급은 owner 와 member 둘뿐이다. member 로 들어온 사용자의 화면은 owner 전용 컨트롤(이름 저장 · 초대코드 복사와 재발급)을 흐리게 하고 누를 수 없게 해야 한다(SHALL). 서버의 403 판정은 그대로 둔다.

#### Scenario: member 의 팀 설정
- **WHEN** member 가 `team.html` 을 연다
- **THEN** 팀 이름 입력은 읽기 전용이고 "이름 저장" · "복사" · "재발급" 은 흐리며 눌러도 동작하지 않는다
