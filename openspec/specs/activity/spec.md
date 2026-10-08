# activity Specification

## Purpose
팀원이 이번 주 팀의 흐름을 한곳에서 볼 수 있도록 회의록 등록 · 할 일 배정과 완료 · 댓글 · 합류를 행위자와 시점과 대상으로 기록하고 보여 주는 기능이다.

## Requirements

### Requirement: 활동 기록 남기기
<!-- 근거: D-10 · E-04 · F-01 · J-06 / team.html, profile.html -->
시스템은 다섯 가지 행위만 기록해야 한다(SHALL). `meeting_add` · `todo_assign` · `todo_done` · `comment_add` · `member_join` 이며 이 외의 kind 는 만들지 않는다(MUST NOT). 각 줄은 행위자 · 시점 · 대상을 가진다. 이름이나 비밀번호 변경은 팀 활동이 아니므로 남기지 않는다.

#### Scenario: 회의록 등록
- **WHEN** 회의록이 저장된다
- **THEN** `meeting_add` 줄이 "회의록 「2차 스프린트 계획 회의」 등록" 같은 문장으로 남는다

#### Scenario: 할 일 배정과 완료
- **WHEN** 담당자를 배정하거나 할 일을 완료로 옮긴다
- **THEN** 각각 `todo_assign` 과 `todo_done` 이 남는다

#### Scenario: 댓글과 합류
- **WHEN** 댓글을 달거나 초대코드로 합류한다
- **THEN** 각각 `comment_add` 와 `member_join` 이 남는다

#### Scenario: 계정 변경
- **WHEN** 내 정보에서 이름이나 비밀번호를 저장한다
- **THEN** 활동 기록에는 새 줄이 생기지 않는다

### Requirement: 팀 활동 기록
<!-- 근거: F-01 / team.html -->
팀 설정 화면은 팀 활동을 최근 순으로 최근 50건까지 보여야 한다(SHALL). 각 줄은 행위자 이름과 서버가 만든 완성 문장과 시각이고 화면은 문장을 그대로 그린다.

#### Scenario: 팀 활동 보기
- **WHEN** `GET /api/teams/{id}/activities` 를 부른다
- **THEN** 200 이고 최근 것부터 최대 50건이며 각 줄에 id · kind · actor_name · text · created_at 이 있다

### Requirement: 내 활동 기록
<!-- 근거: J-01 · J-07 / profile.html -->
내 정보 화면은 내가 한 활동을 최근 순으로 보여야 한다(SHALL). 활동이 없으면 200 + 빈 배열이고 화면은 "아직 활동이 없음" 과 쌓이는 방법을 안내한다.

#### Scenario: 내 활동 보기
- **WHEN** `GET /api/me/activities` 를 부른다
- **THEN** 200 이고 내가 한 활동이 최근 순으로 돌아오며 "n건" 이 보인다

#### Scenario: 합류 직후
- **WHEN** 활동이 한 건도 없다
- **THEN** 200 + 빈 배열이고 "회의록을 올리거나 할 일을 처리하면 여기에 쌓임" 이 보인다

### Requirement: 활동 줄의 띠 색
<!-- 근거: F-01 · J-01 / team.html, profile.html -->
활동 줄의 왼쪽 띠 색은 kind 로 정하며 팔레트 5색 안에서만 골라야 한다(MUST). `meeting_add` 는 blue, `todo_assign` 은 orange, `todo_done` 은 green, `comment_add` 와 `member_join` 은 purple 이다.

#### Scenario: 색 매핑
- **WHEN** 활동 줄을 그린다
- **THEN** kind 에 맞는 `STRIPE` 색이 쓰이고 카드 배경은 무채색 그대로이다
