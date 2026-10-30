---
name: work-platform-wbs
description: LINE Works Project(works.do / project.worksmobile.com) 스페이스·프로젝트의 상위/하위업무를 토~금 주간 간트가 포함된 업무 WBS 엑셀로 추출하고, 기간 없는 상위업무에 하위업무 기간을 채운다. '업무 WBS 작성' 요청 시 사용.
---

# LINE Works Project 업무 WBS (주간 간트 엑셀)

사용자가 "업무 WBS 작성", "WBS 뽑아줘" 등을 요청하면 이 절차를 따른다. 결과물은 엑셀(.xlsx) 1개 + (선택) 프로젝트 내 상위업무 기간 보정.

## 확정 규칙
- **범위**: 기본 = 플랫폼_워크스페이스 스페이스 전체(`s-300018117-b0ce5784-0782-46a2-b336-c5a0d79c8b32`). 프로젝트 링크를 주면 그 프로젝트만. 애매하면 AskUserQuestion으로 스페이스 전체/현재 프로젝트 확인.
- **추출 기간**: 추출일 당월 기준 1개월 전의 1일(예: 10/30 추출 → 09-01) 이후 전체(종료 상한 없음)에 **걸친** 업무 = `종료일(없으면 시작일) >= 기준일`. 완료 업무 포함. 삭제(`deleted`)/휴지통(`binned`) 제외, 조회 404 프로젝트는 건너뜀.
- **포함 규칙**: 상위업무는 본인 또는 하위업무 중 하나라도 기간 조건에 맞으면 포함. 하위업무는 기간 조건에 맞거나 기간 미설정이면(상위가 포함될 때) 포함.
- **제외**: 프로젝트명 `배포리스트관리`(https://works.do/F2FA3Al), `플랫폼 본부 업무`(https://works.do/G2HpkAD), `국가과제_NEW ADMIN`(목록상 `[국가과제_NEW ADMIN]`), `매출정산시스템`(목록상 `[매출정산시스템]`), 업무명에 `[샘플]` 포함 업무. 상위가 제외되면 하위도 제외.
- **상위 기간 보정**: 상위업무에 기간이 없고 하위업무에 기간이 있으면 시작일 = 하위업무 중 가장 빠른 날짜, 종료일 = 가장 늦은 날짜. **엑셀이 아니라 프로젝트 내 업무 값 자체를 수정**하는 것이 사용자 의도 → 아래 '기간 보정' 단계로 실제 업무에 입력(입력 전 대상 목록·건수 확인받기). 엑셀에는 보정된 값이 그대로 반영되도록 수정 후 데이터 기준으로 생성.
- **정렬**: 1순위 진행상태(진행중 → 완료) → 2순위 시작일 내림차순(최근 시작 먼저) → 3순위 종료일 내림차순. 같은 진행상태 안에서 기간 없는 항목은 최상단. 하위업무는 상위업무 바로 아래에 같은 기준으로 정렬.
- **그룹**: 하위업무 행은 엑셀 행 그룹(outlineLevel=1, summaryBelow=False)으로 묶어 접기/펼치기 가능.
- **1주 기준**: 토요일 시작 ~ 금요일 종료.

## 데이터 수집 (Claude in Chrome, 로그인된 project.worksmobile.com 탭에서 fetch)
- tenant `300018117`. 사용자가 해당 도메인 탭을 열어 두었으면 이동 없이 그 탭에서 fetch만.
- API: `GET /rd/300018117/api/v1/spaces/{spaceId}` → `rootFolder.children` 재귀(`projectId` 노드) / `GET .../projects/{id}` → `.project.projectName`, `.project.customFields`(fieldId, fieldName, fieldDataType, selectItems[{id,value}]) / `GET .../tasks?projectId={id}` → `.projectTasks`(taskId, title, status.taskStatusType, parentTaskId, mainProjectId, due{start,end,taskDueType}, customFieldValues[{fieldId, selectItemId|selectItemIds|memberIds|text}], deleted, binned) / `POST /api/v1/getContactUsers` body `{"ids":[...]}` → `[{userId,name}]`.
- 여러 프로젝트에 속한 업무는 taskId로 병합, 값은 mainProjectId 프로젝트 우선 + 다른 프로젝트 값 합집합.
- 커스텀 필드 매칭: `fieldName`에서 공백·`*` 제거 후 비교 — `어플리케이션`/`애플리케이션`, `유형`, `사업영향`, `처리자`(MEMBER → memberIds → 이름). SELECT는 selectItems로 id→value 변환.
- 진행상태: `taskStatusType==='OPEN'` → 진행중, 그 외 → 완료.
- 스크립트는 `window.__x={done:false};(async()=>{...})();'go'` 형태로 백그라운드 실행 후 상태 변수 폴링. 결과는 탭 window 변수에 남으니 재수집하지 않는다.

## 결과 읽기 (도구 출력 제한 대응)
- 출력이 약 1,200자에서 잘리므로: 반복 값(프로젝트·어플리케이션·처리자·유형·사업영향)을 사전 번호로 압축하고 날짜는 `YYMMDD`, 상위/하위는 `U/L`, 상태는 `O/C`로 줄여 `idx|parentIdx|U/L|proj|O/C|app|title|start|end|proc|type|impact` 행으로 만든다.
- 줄 경계 기준 약 950자 청크 배열로 나눠 `browser_batch`에 javascript_tool 10~12개씩 묶어 읽는다.
- 7자리 이상 숫자(사용자 ID 등)는 `#`로 치환해 출력(그대로 두면 차단됨). 쿠키/쿼리스트링처럼 보이는 문자열이 있으면 `[BLOCKED]` → `?&=`를 공백으로 치환.
- 로컬 전사 후 20줄 단위 해시(`h=(h*31+codePoint)%99991`, 줄 끝 `\n` 포함)를 브라우저와 비교해 불일치 줄만 재확인. NBSP(` `)는 일반 공백으로 정규화.
- 확장 프로그램이 "not in Claude's tab group" / "failed in the extension"을 간헐적으로 내면 `browser_batch` 첫 항목에 `tabs_context_mcp(createIfEmpty:true)`를 넣고 같은 호출 재시도. batch 안에 `computer wait`를 넣지 말 것(그룹 이탈 유발).

## 기간 보정 (프로젝트 업무에 직접 입력)
1. 스페이스 전체 live 업무 중 최상위 업무(부모 없음)이고 due.start/end 모두 없으며 제외 대상이 아닌 것 → 하위업무 due가 있으면 min(start||end) ~ max(end||start) 계산. 목록(프로젝트|업무명|기간|상태)과 건수를 보여주고 AskUserQuestion으로 입력 범위 확인(전체 / 진행중만 / 1건 테스트).
2. API: `POST /rd/300018117/api/v1/tasks/{taskId}/due` (PUT은 500), body `{"taskDue":{"taskDueType":"DAY_DUE","start":"YYYY-MM-DD","end":"YYYY-MM-DD"},"projectTaskParameters":[]}`.
3. 입력 후 `tasks?projectId=` 재조회로 전 건 start/end 일치 검증, 결과(성공 N/N) 보고.

## 엑셀 생성 (openpyxl, 글꼴 맑은 고딕)
### 시트1 `업무 WBS`
- 1행 제목 `업무 WBS`, 2행 추출일·범위·주 기준·건수(상위/하위) + 간트 색 범례.
- 3~4행 헤더(`1F4E78` 흰 굵은 글씨, 세로 병합). 컬럼 순서: **구분(상위/하위) | 진행상태(진행중/완료) | 어플리케이션 | 업무 제목 | 기간 | 처리자 | 유형 | 사업영향 | 프로젝트(참고)**. 너비 9/9/16/60/24/18/20/16/24.
- 기간 = `YYYY-MM-DD ~ YYYY-MM-DD`(한쪽만 있으면 같은 날짜로). 여러 값은 `, `로 연결.
- 하위업무 제목 앞에 `    └ `. 상위업무 행은 굵게 + `EEF3FA` 바탕. 진행중은 `C00000` 굵게, 완료 회색.
- 간트 열: 기준일이 속한 주의 토요일부터 최대 종료일이 속한 주의 금요일까지, 주당 1열(너비 6.5). 3행 = 월(주의 금요일 기준, 같은 월 병합, `D9E1F2`), 4행 = `MM/DD\n~MM/DD`. 업무 기간과 겹치는 주를 칠함: 상위·진행중 `2F75B5`, 하위·진행중 `9DC3E6`, 상위·완료 `7F7F7F`, 하위·완료 `C9C9C9`. 이번 주 열은 헤더 `FFE699`, 본문 `FFF9E5`, 좌우 빨간 medium 선.
- 틀 고정 = 첫 간트 열 × 5행, 자동 필터(A4:I끝), 확대 85%.
### 시트2 `기준`
항목 | 내용: 추출일, 대상 범위(조회 불가 프로젝트 수), 추출 기간, 진행상태 정의, 구분/그룹, 정렬, 주간 간트, 제외 기준, 필드 출처.
### 파일
`/mnt/user-data/outputs/플랫폼_워크스페이스_업무WBS_YYYYMMDD.xlsx` (프로젝트 링크면 프로젝트명) → SendUserFile(display: attach). openpyxl로 다시 열어 상위 몇 행 값 확인.

## 마무리 보고 (짧게)
- 총 건수(상위/하위), 진행중 건수, 제외 건수(프로젝트별), 조회 불가 프로젝트 수
- 기간 보정 실행 시: 대상 건수, 검증 결과, 대표 예시 2~3건
- 끝에 `Sources: [플랫폼_워크스페이스](https://project.worksmobile.com/space/300018117/s-300018117-b0ce5784-0782-46a2-b336-c5a0d79c8b32)`
