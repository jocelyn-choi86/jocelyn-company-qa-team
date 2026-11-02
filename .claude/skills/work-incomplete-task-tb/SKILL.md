---
name: "work-incomplete-task-tb"
description: "LINE Works Project의 '타부서 요청 프로젝트_BackLog' 프로젝트와 '운영_이슈_작업[플랫폼본부_이용_타부서_이용금지]' 폴더 하위 프로젝트에서 커스텀필드 어플리케이션이 'TB/WL'(또는 'TB / WL')이고 [완료]되지 않은(open) 업무(유형 '디자인업무요청' 제외)를 12개 컬럼 엑셀(프로젝트명↓ → 진행상태↓ → 기한 종료일↓ 정렬)로 추출한다. 'TB 미완료 업무 추출', 'TB/WL 미완료 정리' 요청 시 사용."
---

# LINE Works Project TB/WL 미완료 업무 엑셀 추출

사용자가 LINE Works Project 링크를 주고 "TB(TB/WL) 미완료 업무 추출/정리"를 요청하면 이 절차와 양식을 그대로 따른다.

## 범위 (고정)
- 추출 대상은 아래 두 곳의 프로젝트**만**이다. 그 외 프로젝트는 링크로 주어져도 제외한다.
  1. 프로젝트 `타부서 요청 프로젝트_BackLog`
  2. 폴더 `운영_이슈_작업[플랫폼본부_이용_타부서_이용금지]` 하위의 모든 프로젝트(하위 폴더 포함, 재귀)
- 스페이스 폴더 트리(`rootFolder.children` 재귀)에서 위 프로젝트명/폴더명을 찾는다. 이름 비교는 앞뒤 공백을 제거하고, 못 찾으면 공백을 모두 제거해 다시 비교한다. 그래도 없으면 작업을 멈추고 사용자에게 알린다.
- 대상 프로젝트의 업무 전체(상위·하위업무 모두)를 조회한다.
- 링크 없이 요청해도 위 범위로 바로 추출한다. 링크를 주면 그 링크 범위와 위 대상 프로젝트가 겹치는 부분만 추출한다(works.do 단축링크는 새 탭에서 열어 `location.pathname`으로 실제 주소 확인).

## 대상 조건 (모두 만족하는 업무 행만)
1. **어플리케이션 = TB/WL**: 커스텀 필드 `어플리케이션`(또는 `애플리케이션`)의 선택 값이 `TB/WL` 또는 `TB / WL`.
   - 비교 시 값의 공백을 모두 제거해 `TB/WL`과 같은지 본다(대소문자 무시). MULTI 선택이면 선택값 중 하나라도 일치하면 포함.
   - 조건은 **행(업무/하위업무)마다 그 업무 자신의 값**으로 판정한다. 상위업무의 어플리케이션을 하위업무에 상속하지 않는다.
2. **미완료**: `status.taskStatusType`이 `OPEN`(대소문자 무시, open). 진행상태 커스텀 필드 값과 무관.
3. **유형 제외**: 유형(`유형` → 없으면 `카테고리`) 값이 `디자인업무요청`인 업무는 제외한다. 비교 시 공백을 모두 제거한다(`디자인 업무 요청`도 제외). 유형도 행마다 그 업무 자신의 값으로 판정한다.
4. `deleted` / `binned` 업무, 404(TASK/PROJECT does not exist) 항목은 제외.
- 프로젝트 자체 행은 만들지 않는다(업무 행만).

## 데이터 수집 (Claude in Chrome, 로그인된 탭에서 fetch)
- tenant/domain: `300018117`, 스페이스 ID: `s-300018117-b0ce5784-0782-46a2-b336-c5a0d79c8b32`
- 스페이스(폴더 트리): `GET /rd/300018117/api/v1/spaces/{spaceId}` → `rootFolder.children` 재귀 (Folder / FolderChildProject)
- 프로젝트: `GET /rd/300018117/api/v1/projects/{projectId}` → `.project` (projectName, customFields[fieldId, fieldName, fieldDataType, selectItems[id,value]])
- 업무 목록: `GET /rd/300018117/api/v1/tasks?projectId={projectId}` → `.projectTasks` (title, status{taskStatusType}, parentTaskId, due{start,end}, assignees[{assigneeId}], createdBy.userId, created, customFieldValues)
- 업무 상세(업무 링크일 때, 생성일 확인용): `GET /rd/300018117/api/v1/tasks/{taskId}` → `.task` (mainProjectId, subTaskIds, parentTaskId, status, due, assignees, createdBy, created, deleted, binned). 커스텀 필드 값은 상세에 없으니 해당 프로젝트 업무 목록에서 가져온다.
- 사용자 이름: `POST /api/v1/getContactUsers` body `{"ids":[userId,...]}` → `[{userId,name}]` (담당자·처리자·생성자 ID를 한 번에 조회)
- 커스텀 필드 값 해석: `selectItemId`(SINGLE/STATUS_SELECT) 또는 `selectItemIds`(MULTI)를 해당 프로젝트 필드의 `selectItems`에서 value로 변환, DATE는 `date.localDate`(null이면 빈 칸), MEMBER(처리자)는 `memberIds`. 필드명은 공백·`*` 제거 후 매칭. 필드 정의는 **그 업무가 속한 프로젝트의 customFields**를 쓴다.
- 수집 스크립트는 async IIFE로 백그라운드 실행 후 `window` 변수를 폴링한다. 결과는 약 800자 단위로 잘라 여러 번 읽는다. `|` 구분 한 줄 1업무 형식으로 압축하고 프로젝트명·사용자명은 인덱스로 줄인다. 필요한 필드만 뽑아 출력한다(쿠키/쿼리 문자열처럼 보이는 값이 섞이면 차단됨).
- 필터(대상 프로젝트·어플리케이션·open·유형 제외)는 수집 스크립트 안에서 먼저 적용해 출력량을 줄인다.

## 필드 매핑 (프로젝트마다 필드명이 다름)
| 컬럼 | 소스 |
|---|---|
| 프로젝트명 | 업무 목록을 조회한 프로젝트의 `projectName` |
| 유형 | 커스텀 필드 `유형` → 없으면 `카테고리` |
| 사업영향 | 커스텀 필드 `사업영향` |
| 업무구분 | `parentTaskId` 없으면 `상위 업무`, 있으면 `하위 업무` |
| 업무명 | 업무 자신의 `title` |
| 요청 기한 | 커스텀 필드 `요청기한` / `요청 기한` / `* 요청기한` (DATE) |
| 기한 | 업무 기본 due의 `end`(없으면 `start`) |
| 담당자 | 업무 기본 assignees → 이름, 여러 명은 ", " |
| 처리자 | 커스텀 필드 `처리자`(MEMBER) `memberIds` → 이름, 여러 명은 ", " |
| 진행상태 | 커스텀 필드 `진행상태` / `진행 상태` → 없으면 `상태` |
| 생성일 | `created` → KST 날짜 |
| 생성자 | `createdBy.userId` → 이름 |
필드가 없거나 값이 없으면 빈 칸.

## 출력 양식 (엑셀, 시트명 `TB 미완료 업무`): 컬럼 순서 고정 (12개)

`프로젝트명 | 유형 | 사업영향 | 업무구분 | 업무명 | 요청 기한 | 기한 | 담당자 | 처리자 | 진행상태 | 생성일 | 생성자`

- 업무구분 값: `상위 업무` / `하위 업무`
- 여러 프로젝트에 태그된 업무(taggedProjectKeys 2개 이상)는 **대상 프로젝트에 해당하는** 프로젝트마다 한 행씩, 각 행의 커스텀 필드 값은 그 프로젝트 기준으로 해석한다(어플리케이션 조건도 행마다 판정).

## 정렬 (우선순위 순, 모두 내림차순)
1. **프로젝트명** 내림차순 (문자열, 한글 로캘 비교)
2. **진행상태** 내림차순 (문자열 값 기준)
3. **기한 종료일**(due.end, 없으면 start) 내림차순 — 늦은 날짜가 위
- 빈 값(진행상태·기한 없음)은 각 단계에서 맨 아래로 보낸다.
- 위 키가 모두 같으면 생성일 내림차순.

## 서식
- 헤더: 굵게, 흰 글씨, 배경 `#1F4E78`, 가운데 정렬, 줄바꿈 허용, 행 높이 32
- 모든 셀 얇은 회색 테두리(`#BFBFBF`), 세로 가운데 정렬
- 하위 업무 행 배경 `#F2F2F2`
- 날짜(요청 기한/기한/생성일)는 실제 날짜 값, `yyyy-mm-dd`, 가운데 정렬
- 기한이 오늘 이전이면 기한 셀 빨간 글씨(`#C00000`)
- 유형/사업영향/업무구분/진행상태 가운데 정렬, 프로젝트명/업무명/담당자/처리자 줄바꿈
- 열 너비: 30,14,12,10,50,12,12,18,18,12,12,10
- 첫 행 고정(freeze A2) + 자동 필터
- 파일명: `TB미완료업무_YYYYMMDD.xlsx`, `/mnt/user-data/outputs/`에 저장 후 SendUserFile

## 마무리 보고
짧게: 조회한 프로젝트 목록(BackLog + 운영_이슈_작업 폴더 하위), 제외한 디자인업무요청 건수, 추출 건수(상위/하위), 프로젝트별 건수, 기한 경과 건수, 조회 불가(404) 항목 존재 여부.
