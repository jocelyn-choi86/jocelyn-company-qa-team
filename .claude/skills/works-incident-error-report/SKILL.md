---
name: works-incident-error-report
description: LINE Works Project(works.do / project.worksmobile.com) URL 하위 업무 중 등록일이 지정 기간(시작일~종료일)에 포함되고 유형이 '장애' 또는 '오류'인 이슈를 추출해 11개 컬럼 엑셀(장애>오류 → 어플리케이션 → 등록일 역순 정렬)로 만든다. '장애/오류 이슈 추출', '기간별 장애 오류 리스트' 요청 시 사용.
---

# LINE Works Project — 장애/오류 이슈 추출 (Incident & Error Report)

Jocelyn이 LINE Works Project URL과 기간을 주면서 "장애/오류 이슈 뽑아줘", "기간 내 장애·오류 리스트 정리해줘" 같은 요청을 할 때 사용한다.

## 입력값 (요청 시 받기)

| 입력 | 설명 |
|---|---|
| URL | `works.do/...` 단축링크 또는 `project.worksmobile.com/...` 프로젝트/업무 링크 |
| 시작일 | `YYYY-MM-DD` |
| 종료일 | `YYYY-MM-DD` |

셋 중 하나라도 빠졌으면 추출 전에 Jocelyn에게 물어본다. 시작일 > 종료일이면 그대로 진행하지 말고 확인한다.

## Access

project.worksmobile.com은 로그인 세션이 필요하므로 WebFetch는 로그인 리다이렉트로 막힌다. 항상 Claude-in-Chrome 도구(`tabs_context_mcp`, `navigate`, `javascript_tool`/`javascript_exec`, `computer`)로 이미 로그인된 브라우저 탭에서 작업한다.

Workspace 상수:
- `domainId`: `300018117`
- 플랫폼_워크스페이스 space slug: `s-300018117-b0ce5784-0782-46a2-b336-c5a0d79c8b32`

## URL → 추출 대상 결정

1. 인증된 탭에서 URL로 `navigate` 한 뒤 `location.href`를 읽어 최종 URL을 확인한다 (`works.do` 단축링크는 리다이렉트된 결과를 기준으로 한다).
2. 최종 URL 형태에 따라 범위를 정한다.
   - **프로젝트 링크** (projectId만 있음) → 해당 프로젝트의 전체 업무(하위업무 포함).
   - **업무 링크** (taskId 포함) → 그 업무 자신 + 하위업무 전체(재귀적으로 `parentTaskId` 체인을 따라 내려감).
   - **폴더/스페이스 링크** → `GET /rd/{domainId}/api/v1/spaces/{spaceSlug}`의 `rootFolder`를 재귀 탐색해 해당 폴더 하위의 모든 leaf 프로젝트(`jsonTypeHint: "FolderChildProject"`)의 업무.
3. 하위업무도 조건(기간·유형)만 맞으면 동일하게 한 행으로 포함한다 (계층 표시는 하지 않는다).

## API endpoints (인증 탭에서 `javascript_tool` fetch)

- `GET /rd/{domainId}/api/v1/spaces/{spaceSlug}` → `{ rootFolder }` (폴더 재귀 탐색용)
- `GET /rd/{domainId}/api/v1/projects/{projectId}` → `{ project }`, `project.name`, `project.customFields`(필드 정의)
- `GET /rd/{domainId}/api/v1/tasks?projectId={projectId}` → `{ projectTasks: [...] }`, 각 업무에 `customFieldValues` 포함
- `POST /api/v1/getContactUsers` body `{"ids": [...]}` → 사용자 ID → 표시 이름. 처리자/등록자 ID를 모두 모아 한 번에 호출한다.

## 필드 매핑 — 견고하게

- 필드 정의는 `fieldId`, 선택지 배열 `selectItems`의 항목은 `id`를 쓴다.
- `jsonTypeHint` 문자열로 분기하지 않는다 (같은 의미의 필드가 프로젝트마다 `SingleSelectCustomField` / `StatusSelectCustomField` 등으로 다르다). **값 객체에 존재하는 속성**으로 분기한다: `selectItemId`(단일 선택 → `selectItems`에서 라벨 조회), `selectItemIds`(다중 선택), `date`, `memberIds`, 텍스트 값.
- 필드는 프로젝트마다 `fieldId`가 다르므로 **프로젝트별로 필드 이름**으로 찾는다. 이름은 공백을 제거하고 비교한다.

| 출력 컬럼 | 소스 |
|---|---|
| 프로젝트명 | `project.name` |
| 유형 | 커스텀 필드 `유형` (단일 선택 라벨) |
| 진행상태 | 커스텀 필드 `진행 상태` (표시용 라벨) |
| 어플리케이션 | 커스텀 필드 `어플리케이션` |
| 업무제목 | 업무 제목(title) |
| 원인 | 유형이 장애면 `원인 (장애)`, 오류면 `원인 (오류)` 필드. 해당 필드가 없으면 이름에 `원인`이 포함된 필드 |
| 처리 내용 | 유형이 장애면 `처리 내용 (장애)`, 오류면 `처리 내용 (오류)` 필드. 없으면 이름에 `처리 내용`/`처리내용`이 포함된 필드 |
| 처리자 | 커스텀 멤버 필드 `처리자`가 있으면 그 값, 없으면 업무 담당자(assignee). 여러 명은 `, `로 연결 |
| 등록자 | 업무 생성자(creator) |
| 등록일 | 업무 생성일시(created) → KST 기준 `YYYY-MM-DD` |
| 완료일 | 업무 완료일시(완료 처리 시각, `status`의 완료 시각 등). 미완료면 `-` |

첫 실행 시 대상 프로젝트들의 `customFields` 이름 목록을 한 번 출력해서 위 매핑이 실제 필드와 맞는지 확인하고, 매칭되지 않는 컬럼이 있으면 추측하지 말고 Jocelyn에게 실제 필드명을 묻는다. 확인된 필드명은 이 SKILL.md에 반영한다.

행을 다 만든 뒤 `/^[0-9a-f]{8}-[0-9a-f]{4}-/` 정규식으로 GUID가 남은 셀이 없는지 검사한다.

## 추출 조건

1. **기간**: 등록일(KST 날짜)이 `시작일 <= 등록일 <= 종료일` — 양 끝 포함. 생성 시각은 UTC로 올 수 있으니 반드시 +9h 변환 후 날짜만 비교한다.
2. **유형**: `장애` 또는 `오류`만 포함 (라벨 앞뒤 공백 제거 후 정확히 일치).
3. **진행상태는 필터하지 않는다** — 완료/미완료 모두 포함.

## 정렬

1. 유형: `장애` → `오류`
2. 어플리케이션 오름차순 (빈 값 `-`은 맨 뒤)
3. 등록일 내림차순 (최신 먼저; 같은 날짜면 생성 시각 내림차순)

## 출력 형식 — 11개 컬럼, 이 순서 그대로

프로젝트명 / 유형 / 진행상태 / 어플리케이션 / 업무제목 / 원인 / 처리 내용 / 처리자 / 등록자 / 등록일 / 완료일

- 빈 값은 `-`
- 날짜는 `YYYY-MM-DD`
- 원인·처리 내용의 줄바꿈은 셀 안에서 유지한다 (wrap).

## 브라우저 탭에서 대량 텍스트 꺼내기

`get_page_text`는 대량 텍스트 회수에 신뢰할 수 없다. 대신:

1. 탭 안에서 결과를 JSON 문자열로 `window.__issueJson`에 만든다 (원인/처리 내용에 줄바꿈·`|`가 있을 수 있으므로 파이프 구분 대신 JSON 사용).
2. `javascript_tool`로 300자 단위 슬라이스를 읽는다:
   `(function(){const s=<start>,e=<end>;const c=window.__issueJson.slice(s,e);return c+'<<<END'+c.length+'>>>';})()`
3. 모든 청크에서 `<<<END` 뒤 숫자가 실제 길이와 일치하는지 확인한다 (조용한 잘림 방지).
4. 여러 청크는 `browser_batch`로 묶어 한 번에 읽는다.
5. 순서대로 이어붙여 `json.loads` 성공 + 행 수가 탭에서 계산한 `window.__issueJson`의 행 수와 같은지 검증한다.

`"Tab X is not in Claude's tab group"` 오류가 나도 실제로는 실행된 경우가 많다. `window.*` 상태를 먼저 확인하고, 필요하면 `tabs_context_mcp` 후 동일 호출을 재시도한다. 스크립트는 재실행해도 안전하게 작성한다.

## 엑셀 생성

`xlsx` 스킬 컨벤션(openpyxl)을 따르고, 기존 미완료 업무 리포트와 동일한 스타일을 쓴다.

- 폰트 Arial, 데이터 10pt. 헤더: 채우기 `4472C4`, 흰색 굵게, 가운데 정렬. 모든 셀에 얇은 `D9D9D9` 테두리.
- 1행 제목: 전체 컬럼 병합, 왼쪽 정렬, 12pt 굵게 — `"AGL 장애/오류 이슈 리스트 ({시작일} ~ {종료일}, 생성일: {오늘 YYYY-MM-DD})"`
- 2행에 요약: `장애 N건 / 오류 M건 / 합계 T건`
- 헤더 아래 틀 고정, 헤더 행 자동 필터.
- 가운데 정렬: 유형, 진행상태, 등록일, 완료일. 왼쪽 정렬 + 줄바꿈: 프로젝트명, 어플리케이션, 업무제목, 원인, 처리 내용, 처리자, 등록자.
- 유형 셀 강조: 장애 → 연한 빨강 `FCE4E4`, 오류 → 연한 노랑 `FFF4CC`.
- 컬럼 너비: 프로젝트명 ~24, 유형 ~8, 진행상태 ~12, 어플리케이션 ~16, 업무제목 ~40, 원인 ~40, 처리 내용 ~50, 처리자 ~14, 등록자 ~10, 등록일 ~11, 완료일 ~11.
- 결과가 0건이면 파일 대신 "조건에 맞는 장애/오류 이슈가 없습니다"라고 알린다.

## 파일명 및 전달

- `/mnt/user-data/outputs/장애_오류_이슈_{시작일}_{종료일}.xlsx` (날짜는 `YYYYMMDD`)
- `SendUserFile`로 전달하고, 답변에 장애/오류 건수 요약을 함께 적는다.
