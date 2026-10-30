---
name: "works-incomplete-tasks"
description: "LINE Works Project 미완료([완료] 안 된) 업무를 지정 15개 컬럼 양식의 엑셀로 추출. 워크스페이스 전체, 또는 works.do/프로젝트/업무 링크 기준(하위·연결 업무 포함). '미완료 항목 추출/정리해줘' 요청 시 사용."
---

# LINE Works Project 미완료 업무 엑셀 추출

사용자가 LINE Works Project(project.worksmobile.com)에서 "미완료 항목 추출/전환/정리"를 요청하면 이 절차와 양식을 그대로 따른다.

## 범위(모드) 결정
- **A. 워크스페이스 전체 모드**: 링크 없이 요청하면 플랫폼_워크스페이스 전체 프로젝트가 대상.
- **B. 링크 기준 모드**: works.do 단축링크나 project.worksmobile.com 링크를 주면 해당 위치를 기준으로 추출.
  - 단축링크는 새 탭에서 열어 `location.pathname`으로 실제 주소를 확인한다. `/300018117/t-...`는 업무, `/space/.../p-.../pv-...`는 프로젝트 뷰.
  - 업무 링크: 그 업무 + 하위업무 + 관련 리소스로 연결된 업무.
  - 프로젝트 링크: 그 프로젝트의 업무 전체 + 각 업무의 관련 리소스로 연결된 프로젝트 밖 업무.
  - 연결된 업무는 미완료(OPEN)만 포함. [완료]된 것과 404(TASK does not exist, 삭제됨)는 제외하고, 보고할 때 한 줄로 알린다.
  - 링크 기준 모드에서는 **프로젝트 행을 넣지 않는다**(업무 행만).

## 대상 정의
- 미완료 = 업무의 [완료] 체크가 안 된 업무 (`status.taskStatusType === 'OPEN'`). 진행상태 필드 값과 무관.
- 하위업무(`parentTaskId` 있음)는 다음 중 하나면 포함:
  - 하위업무 자체가 미완료(OPEN)
  - **하위업무는 [완료](CLOSE)됐지만 상위 업무가 미완료(OPEN)**: 상위가 끝나지 않았으므로 함께 표시
- 상위 업무가 [완료]된 경우에는 미완료(OPEN) 하위업무만 포함.
- `deleted` / `binned` 업무는 제외.
- 스페이스 폴더 트리에 있지만 프로젝트 조회가 404(PROJECT does not exist)인 항목은 삭제된 프로젝트로 보고 건너뛴다.
- (A 모드) **프로젝트 행**: 위 기준으로 업무가 1건 이상 포함된 프로젝트마다 프로젝트 자체를 한 행으로 추가(업무가 없는 프로젝트는 제외).

## 데이터 수집 (Claude in Chrome, 로그인된 탭에서 fetch)
- tenant/domain: `300018117`, 스페이스 ID: `s-300018117-b0ce5784-0782-46a2-b336-c5a0d79c8b32`
- 스페이스(폴더 트리): `GET /rd/300018117/api/v1/spaces/{spaceId}` → `rootFolder.children` 재귀 (Folder / FolderChildProject)
- 프로젝트: `GET /rd/300018117/api/v1/projects/{projectId}` → `.project` (projectName, projectStatus, projectDuration{start,end}, created, customFields[fieldId, fieldName, fieldDataType, selectItems[id,value]]). 프로젝트 생성자·완료일은 API에 없음.
- 업무 목록: `GET /rd/300018117/api/v1/tasks?projectId={projectId}` → `.projectTasks` (title, status{taskStatusType, lastModified}, parentTaskId, due{start,end}, assignees[{assigneeId}], createdBy.userId, created, customFieldValues). 완료(CLOSE) 업무도 내려오므로 taskId → task 맵으로 상위 업무 상태/제목을 조회한다. 목록에는 태그된 프로젝트·관련 리소스 정보가 없다.
- **업무 상세**: `GET /rd/300018117/api/v1/tasks/{taskId}` → `.task` (mainProjectId, **taggedProjectKeys[{projectId}]**, **relatedResources[{relatedTaskId, relatedTaskTitle}]**, subTaskIds, parentTaskId, status, due, assignees, createdBy, created, deleted, binned). 커스텀 필드 값은 여기 없으니 프로젝트별 업무 목록에서 가져온다. 404면 삭제된 업무.
- 생성일은 **업무 상세의 `created`**를 쓴다. 태그된 다른 프로젝트 목록의 created는 태그 시점이라 다를 수 있다.
- 포함 판정: `open(t) || (t.parentTaskId && open(taskMap[t.parentTaskId]))` (`open = t => t?.status?.taskStatusType === 'OPEN'`)
- 사용자 이름: `POST /api/v1/getContactUsers` body `{"ids":[userId,...]}` → `[{userId,name}]` (담당자·처리자·생성자 ID를 한 번에 조회)
- 커스텀 필드 값 해석: `selectItemId`(SINGLE/STATUS_SELECT) 또는 `selectItemIds`(MULTI)를 해당 필드 `selectItems`에서 value로 변환, DATE는 `date.localDate`(null이면 빈 칸), MEMBER(처리자)는 `memberIds`. 필드명은 공백·`*` 제거 후 매칭.
- 수집 스크립트는 async IIFE로 백그라운드 실행 후 `window` 변수를 폴링한다. 결과는 약 800자 단위로 잘라 `browser_batch`로 여러 번 읽는다(긴 출력은 잘림). `|` 구분 한 줄 1업무 형식으로 압축하고, 프로젝트명·사용자명은 인덱스로 줄인다(여러 명은 `.` 구분 인덱스). 연속된 하위업무의 같은 상위 제목은 `^`로 압축한다. javascript_tool 결과에 쿠키/쿼리 문자열처럼 보이는 값이 섞이면 차단되므로 필요한 필드만 뽑아 출력한다.
- 수집 결과 행 포맷(참고): `[프로젝트idx, 유형, 어플리케이션, 상위제목(하위만, ^=직전과 동일), 자기제목, 요청기한, 기한, 담당자idx, 진행상태, 생성일, 생성자idx, 하위여부, 완료여부, 처리자idx, 완료일]`, 프로젝트는 `[이름, projectStatus, 기한, 생성일]`. 날짜는 `YY-MM-DD`.

## 여러 프로젝트에 속한 업무 (taggedProjectKeys 2개 이상)
- **프로젝트마다 각각 한 행**으로 추출하고, 같은 업무의 행들은 **연속된 위치**에 둔다(메인 프로젝트 먼저, 그다음 태그된 프로젝트 순).
- 각 행의 값은 **그 프로젝트에 매칭된 값**으로 표시한다. 유형·어플리케이션·진행상태·요청기한·처리자 같은 커스텀 필드는 해당 프로젝트의 `tasks?projectId=` 목록 항목의 `customFieldValues`를 **그 프로젝트의 customFields 정의**로 해석한다. 프로젝트마다 값이 다를 수 있고, 비어 있으면 빈 칸. 기한·담당자·생성일·생성자는 업무 공통 값.
- 상위업무에 하위업무가 있으면: 상위업무의 프로젝트별 행들 → 그 아래 하위업무의 프로젝트별 행들.

## 필드 매핑 (프로젝트마다 필드명이 다름)
| 컬럼 | 업무 행 소스 |
|---|---|
| 유형 | `유형` → 없으면 `카테고리` |
| 어플리케이션 | `어플리케이션` 또는 `애플리케이션` |
| 진행상태 | `진행상태` / `진행 상태` → 없으면 `상태` |
| 완료일 | [완료](CLOSE)된 업무만 `status.lastModified` → KST 날짜. 미완료 업무는 빈 칸 |
| 요청기한 | `요청기한` / `요청 기한` / `* 요청기한` (DATE) |
| 기한 | 업무 기본 due의 `end`(없으면 `start`) |
| 담당자 | 업무 기본 assignees → 이름, 여러 명은 ", "로 연결 |
| 처리자 | 커스텀 필드 `처리자`(MEMBER) `memberIds` → 이름, 여러 명은 ", "로 연결 |
| 생성일 | 업무 상세 `created` → KST 날짜 |
| 생성자 | `createdBy.userId` → 이름 |
필드가 없거나 값이 없는 경우 빈 칸.

## 출력 양식 (엑셀, 시트명 `미완료 업무`): 컬럼 순서 고정 (15개)

`프로젝트명 | 유형 | 업무구분 | 어플리케이션 | 업무명 | 업무구분\n: 하위업무 | (하위업무) 업무명 | 요청기한 | 기한 | 담당자 | 처리자 | 진행상태 | 완료일 | 생성일 | 생성자`

프로젝트명 칸은 하나만 둔다. 여러 프로젝트는 행을 나눠 표시하고, 한 칸에 이어 쓰거나 칸을 늘리지 않는다.

행 종류는 3가지: **프로젝트(A 모드만) / 상위업무 / 하위업무**

**프로젝트 행** (A 모드, 각 프로젝트 그룹의 첫 행)
- 프로젝트명 = 프로젝트명, 유형 = `프로젝트`, 업무구분 = `프로젝트`, 업무명 = 프로젝트명
- 기한 = `projectDuration.end`(없으면 `start`, 둘 다 없으면 빈 칸)
- 진행상태 = `projectStatus` 매핑: BEFORE_START→`시작 전`, IN_PROGRESS→`진행 중`, COMPLETED→`완료`, NONE→`설정 안 함`
- 생성일 = 프로젝트 `created` → KST 날짜
- 생성자·완료일 = 빈 칸 (API 미제공)
- 어플리케이션 / 하위업무 두 컬럼 / 요청기한 / 담당자 / 처리자 = 빈 칸

**상위업무 행**: 업무구분 `상위업무`, 업무명 = 자기 제목, 6·7열 빈 칸

**하위업무 행**: 업무구분 `하위업무`, 업무명 = **상위 업무 제목**(상위가 이미 완료돼도 표시), 업무구분: 하위업무 = `하위업무`, (하위업무) 업무명 = 자기 제목

- 진행상태(업무 행)는 필드 값 그대로. [완료]된 하위업무는 완료일 + 서식으로 구분.
- 정렬:
  - A 모드: 프로젝트(스페이스 트리 순) → 프로젝트 행 → 상위 업무 생성일 내림차순 → 상위 업무 행 바로 아래에 그 하위 업무들(생성일 오름차순)
  - B 모드: 상위 업무 생성일 내림차순(연결된 업무 포함) → 각 상위업무 아래 하위 업무들(생성일 오름차순). 여러 프로젝트 업무는 위 규칙대로 연속 행.

## 서식
- 헤더: 굵게, 흰 글씨, 배경 `#1F4E78`, 가운데 정렬, 줄바꿈 허용, 행 높이 32
- 모든 셀 얇은 회색 테두리(`#BFBFBF`), 세로 가운데 정렬
- 프로젝트 행: 배경 `#DDEBF7`, 굵게
- 하위업무 행 배경 `#F2F2F2`
- **프로젝트명 칸 색상은 프로젝트가 2개 이상인 업무의 행에만** 칠한다. 프로젝트명에 `BackLog`가 들어가면 회색 `#D9D9D9`, 그 외 프로젝트는 분홍색 `#F8D7E3`. 프로젝트가 1개인 업무는 색을 칠하지 않는다(하위업무 행이면 `#F2F2F2` 유지).
- [완료]된 하위업무 행(상위 미완료로 포함된 건)은 글자색 회색(`#808080`)
- 날짜(요청기한/기한/완료일/생성일)는 실제 날짜 값, `yyyy-mm-dd`, 가운데 정렬
- 기한이 오늘 이전이면 기한 셀 빨간 글씨(`#C00000`). [완료]된 하위업무와 완료(COMPLETED) 프로젝트는 제외
- 업무구분 두 컬럼 가운데 정렬, 프로젝트명/업무명/(하위업무) 업무명/담당자/처리자 줄바꿈
- 열 너비: 30,14,10,20,46,11,46,12,12,18,18,14,12,12,10
- 첫 행 고정(freeze A2) + 자동 필터
- **하위업무 행 그룹 설정(행 그룹화)**: 하위업무 행에 `outline_level=1`을 주어 바로 위 상위업무 행 아래로 묶는다. `ws.sheet_properties.outlinePr.summaryBelow = False`, `ws.sheet_format.outlineLevelRow = 1`. 기본은 펼친 상태(숨김 없음). [-]/[+]로 접고 펼 수 있고, 레벨 [1]이면 하위업무 전체가 접힌다.
- 파일명:
  - A 모드: `플랫폼_워크스페이스_미완료업무_YYYYMMDD.xlsx`
  - B 모드: `{프로젝트명 또는 업무명 요약}_미완료업무_YYYYMMDD.xlsx` (예: `타부서요청_BackLog_미완료업무_20260929.xlsx`)
  - `/mnt/user-data/outputs/`에 저장 후 SendUserFile

## 마무리 보고
짧게: 대상 범위, 업무 건수(상위/하위, 그중 상위 미완료로 포함된 [완료] 하위업무 건수), 전체 행 수(여러 프로젝트 업무 건수), 기한 경과 건수, 제외한 연결 업무([완료]/삭제), 조회 불가(404) 프로젝트 존재 여부, 이전 추출 대비 눈에 띄는 변화가 있으면 한 줄.