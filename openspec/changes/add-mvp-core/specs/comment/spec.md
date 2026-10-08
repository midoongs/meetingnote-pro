# Spec Delta

## Purpose

팀원이 회의록의 결정에 의견을 남기고 신규 합류자가 맥락을 질문할 수 있도록, 회의록에 댓글을 달고 읽고 지우는 기능이다.

## ADDED Requirements

### Requirement: 댓글 작성
<!-- 근거: D-09 · D-10 / detail.html -->
팀원은 회의록에 댓글을 달 수 있어야 한다(SHALL). 댓글은 500자 이내이고, 등록하면 201 을 받아 입력칸이 비워지며 목록 맨 아래에 붙는다. 등록은 활동 기록에 `comment_add` 로 남는다.

#### Scenario: 댓글 등록
- **WHEN** "이 회의에 대한 의견" 칸에 글을 쓰고 "등록" 을 누른다
- **THEN** `POST /api/meetings/{id}/comments` 가 201 을 돌려주고 입력칸이 비워지며 새 댓글이 맨 아래에 보인다

#### Scenario: 500자 초과
- **WHEN** 501자 댓글을 등록한다
- **THEN** 400 `VALIDATION_ERROR` 를 받고 저장되지 않는다

### Requirement: 댓글 목록
<!-- 근거: D-01 · D-11 / detail.html -->
댓글 목록은 작성 시각 오름차순이고 각 줄에 작성자 이름 · 내용 · 시각 · 삭제 가능 여부(`can_delete`)가 있어야 한다(SHALL). 댓글이 없는 것이 기본 상태이며 그때는 200 + 빈 배열이다.

#### Scenario: 댓글 보기
- **WHEN** 상세를 연다
- **THEN** `GET /api/meetings/{id}/comments` 가 200 으로 오래된 것부터 돌려주고 "n건" 이 보인다

#### Scenario: 댓글 없음
- **WHEN** 댓글이 0건이다
- **THEN** 목록 자리에 "아직 댓글이 없음 - 결정에 의견이 있으면 여기에" 안내가 보인다

### Requirement: 댓글 삭제
<!-- 근거: D-12 / detail.html -->
댓글은 쓴 사람과 팀 owner 만 지울 수 있어야 한다(SHALL). 판정은 서버가 하고 응답의 `can_delete` 로 알린다. 권한이 없으면 403 `FORBIDDEN` 이다.

#### Scenario: 쓴 사람이 삭제
- **WHEN** 쓴 사람이 "삭제" 를 누른다
- **THEN** `DELETE /api/comments/{id}` 가 204 를 돌려주고 댓글이 사라진다

#### Scenario: 남의 댓글
- **WHEN** 쓴 사람도 owner 도 아닌 사람이 목록을 본다
- **THEN** 그 댓글의 `can_delete` 가 false 이고 "삭제" 는 흐리며 눌러도 동작하지 않고, 서버는 403 `FORBIDDEN` 으로 막는다
