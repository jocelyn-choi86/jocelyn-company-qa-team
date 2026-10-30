---
name: "works-resource-gantt-2"
description: "LINE Works Project(works.do) 링크 하위 미완료 상위/하위업무를 [처리자] 기준 인력 투입 현황표(이름×날짜 간트) 엑셀로 만든다. '인력 투입 현황', '처리자 기준 일정 표시' 요청 시 사용. (배포리스트관리 프로젝트 제외)"
---

# LINE Works 처리자 기준 인력 투입 현황표 (간트 엑셀)

사용자가 works.do / project.worksmobile.com 링크와 함께 "이름별로 업무 기간 표시", "인력 투입 현황", "처리자 기준 일정표"를 요청하면 이 절차를 그대로 따른다. 결과물은 엑셀(.xlsx) 1개.

## 기본 규칙 (사용자 확정 사항)
- **검색 범위**: 링크 하위의 모든 **상위업무 + 하위업무**. 링크가 스페이스(`/space/300018117/s-...`)면 스페이스 폴더 트리의 모든 프로젝트, 프로젝트 링크면 그 프로젝트.
- **이름 기준(기본)**: 일정은 항상 커스텀 필드 **[처리자]**(MEMBER, `memberIds`) 기준으로 그 사람 행에 표시한다. 기본 담당자(assignees)는 기준이 아니며 대체로도 쓰지 않는다(참고용으로만 메모/목록에 표시).
- **기간 표시**: 업무 기본 기간 `due.start ~ due.end`(한쪽만 있으면 그 날짜 하루).
- **대상 기간**: 미완료 업무는 기준일(예: 10/5) **이후 날짜를 하루라도 포함**하는 업무 = `종료일 >= 기준일`. 기준일은 요청에서 받는다. 없으면 이번 주 월요일.
- **표시 범위**: 기준일이 속한 주의 **전 주 월요일**(표시 시작일)부터 7주 뒤 일요일(표시 종료일)까지.
- **제외 프로젝트**: 프로젝트명(공백 제거 후)에 `배포리스트관리`가 포함된 프로젝트는 추출 대상에서 제외한다. 그 프로젝트의 업무는 수집하지 않고, 다른 프로젝트에 함께 연결된 업무라도 `mainProjectId`가 제외 프로젝트면 뺀다. 세 시트(현황표·대상 업무 목록·기간 미설정)와 범례 모두에 나오지 않는다.
- **완료 판정**: 업무의 **[완료] 체크** 기준 = `status.taskStatusType === 'CLOSE'`. 그 외(`OPEN` 등)는 모두 미완료. 커스텀 필드 진행상태/상태 값(예: "배포완료")으로 완료를 판정하지 않는다.
- **완료 업무 포함**: [완료](`CLOSE`) 업무도 기간이 **표시 범위와 하루라도 겹치면**(`종료일 >= 표시 시작일` 그리고 `시작일 <= 표시 종료일`) 사람 행에 넣는다. 업무 텍스트 앞에 `[완료] `를 붙이고 회색 글씨, 막대는 빗금. 기간 미설정 영역과 처리자 미지정 영역에는 미완료(OPEN) 업무만 넣는다. `deleted`/`binned` 제외. 프로젝트 조회 404는 삭제된 프로젝트로 건너뜀.
- **상태 표시**: `완료(진행 상태)` / `진행중(진행 상태)` 형식. 앞부분 완료/진행중은 **오직 `status.taskStatusType === 'CLOSE'`([완료] 체크)** 로 정한다(CLOSE면 `완료`, 그 외 `진행중`). 괄호 안은 커스텀 필드 **진행 상태** 값: 프로젝트 customFields 중 `fieldName`에서 공백·`*`를 뺀 이름이 `진행상태`인 필드("진행 상태"/"진행상태"), 없으면 `상태`인 필드의 선택값 라벨. 이름은 정확히 일치로 비교한다(부분일치 금지). 필드 정의는 `customFields[].fieldId`로 값(`customFieldValues[].fieldId`)과 매칭하고 `selectItems`의 `id → value`로 라벨을 얻는다. 커스텀 필드가 없거나 값이 비어 있으면 괄호 없이 `완료` / `진행중`만. 예: `완료(배포완료)`, `진행중(개발중)`, `진행중(배포완료)`(필드는 완료인데 [완료] 체크 안 됨), `진행중`.
- **정렬**: 사람별로 **시작일 → 종료일 빠른 순**, 같으면 미완료 먼저.
- **행 배치**: 시작일 기준 정렬 순서대로 넣되 **업무(항목)마다 행을 하나씩 각각 사용**한다. 기간이 겹치지 않아도 같은 행에 이어 붙이지 않는다(사람별 일정 행 수 = 그 사람의 일정 있는 업무 수).
- **이름 병합**: 한 사람의 여러 행은 부서명/주 업무/이름 칸을 세로 병합. 부서명은 부서 전체 행 병합.
- **업무 표기에 프로젝트명 포함**: 현황표에 나오는 모든 업무 텍스트(E열 할당 업무, 기간 미설정, 처리자 미지정 목록)는 앞에 `[프로젝트명]`을 붙인다 → `[프로젝트명] 상위 > 업무명`(하위업무) / `[프로젝트명] 업무명`(상위업무). 프로젝트명은 `mainProjectId` 기준.
- **유형(상위/하위)**: 할당 업무 바로 앞 D열에 `상위`(parentTaskId 없음) 또는 `하위`(parentTaskId 있음)를 표시한다. 일정 행·기간 미설정 행·처리자 미지정 영역 모두 같다.
- **기간 미설정 업무**(미완료, 처리자 있음, due 없음): E열 할당 업무에 한 줄에 하나씩, F열 기간은 `기간 미설정`. **일정 있는 행과 분리**하여 그 사람의 일정 행들 아래 별도 행으로 추가(일정 행이 없으면 기간 미설정 행만). 일정 행과 기간 미설정 행 사이 진한 구분선.
- **처리자 미지정 업무**: 대상 기간에 해당하지만 [처리자]가 비어 있는 업무는 사람 행에 넣지 않고(담당자가 있어도 마찬가지) 표 **최상단**(헤더 바로 아래, 첫 부서 행 위)에 '처리자 미지정 (N건)' 영역으로 별도 표시. E열에 `[프로젝트명] 상위 > 업무명`, F열에 `M/D ~ M/D` 목록을 **가나다 순**으로 정렬(표시 텍스트 기준 = 프로젝트명 → 상위업무명 → 업무명 순으로 비교; Python `sorted(key=텍스트)`의 유니코드 순서가 한글 가나다 순과 같음. 텍스트가 같으면 종료일→시작일 순). 처리자·기간 둘 다 없는 업무는 대상 아님.
- 양식 명단에 없는 처리자(예: 김남혁, 용아준)는 표에 넣지 않고 보고 시 알린다.

## 인원 명단 (양식)
사용자가 새 양식 이미지/파일을 주면 그것을 따른다. 기본값:
| 부서명 | 주 업무 | 이름 |
|---|---|---|
| GDS | BE | 김대수 |
| GDS | BE | 김성훈 |
| GDS | FE | 이민오 |
| GDS | FE | 채승원 |
| GDS | DB | 강성민 |
| GDS | API | 정명훈 |
| TB | FE | 정세련 |
| TB | FE/BE | 서영수 |
| TB | FE/BE | 박시환 |
| TB | APP | 김지운 |
| TB | FE | 이지민 |
| ADMIN | FE/BE | 현민원 |
| PP | TB | 한윤선 |
| PP | GDS | 박현수 |
| PP | ADMIN | 전희연 |
| PP | 디자인 | 이설 |
| PP | PM | 최윤정 |

## 데이터 수집 (Claude in Chrome, 로그인된 project.worksmobile.com 탭에서 fetch)
- tenant `300018117`, 기본 스페이스 `s-300018117-b0ce5784-0782-46a2-b336-c5a0d79c8b32` (https://works.do/GdVpYnD = 이 스페이스 루트).
- 단축링크는 탭에서 열어 `location.pathname`으로 실제 주소 확인. 사용자가 이미 해당 도메인 탭을 열어 두었으면 그 탭에서 fetch만 하고 페이지 이동은 하지 않는다.
- API: `GET /rd/300018117/api/v1/spaces/{spaceId}` → `rootFolder.children` 재귀(`projectId` 있는 노드) / `GET .../projects/{id}` → `.project.customFields` / `GET .../tasks?projectId={id}` → `.projectTasks` (title, status, parentTaskId, due{start,end}, assignees, customFieldValues, mainProjectId, deleted, binned) / `POST /api/v1/getContactUsers` body `{"ids":[...]}` → `[{userId,name}]`.
- 처리자 필드: 프로젝트 customFields 중 `fieldName`에서 공백·`*` 제거 후 `처리자`인 MEMBER 필드. 값은 `customFieldValues[fieldId].memberIds`. 여러 프로젝트에 속한 업무는 프로젝트별 값을 합집합.
- 수집 스크립트(백그라운드 실행 후 `window.__k.done` 폴링):
```js
window.__k={done:false};(async()=>{const g=window.__k;try{
const SPACE_ID='s-300018117-b0ce5784-0782-46a2-b336-c5a0d79c8b32'; // 링크가 가리키는 스페이스 ID로 바꾼다
const BASE='2026-10-19'; // 기준일(YYYY-MM-DD)로 바꾼다
const B='/rd/300018117/api/v1';const d10=s=>s?String(s).slice(0,10):null;const iso=d=>d.toISOString().slice(0,10);
const b0=new Date(BASE+'T00:00:00Z');const ds=new Date(b0);ds.setUTCDate(b0.getUTCDate()-((b0.getUTCDay()+6)%7)-7);const de=new Date(ds);de.setUTCDate(ds.getUTCDate()+48);
const DS=iso(ds),DE=iso(de); // 표시 범위: 전 주 월요일 ~ 7주 뒤 일요일
const sp=await (await fetch(`${B}/spaces/${SPACE_ID}`)).json();
const projs=[];const walk=n=>(n.children||[]).forEach(c=>{if(c.projectId)projs.push(c.projectId);walk(c);});walk(sp.rootFolder||sp.space?.rootFolder||{});
const EXCL=['배포리스트관리']; // 제외 프로젝트(이름에 포함되면 제외)
const P={},T={},X=new Set();let n404=0;
for(const id of projs){const r=await fetch(`${B}/projects/${id}`);if(!r.ok){n404++;continue;}
 const pj=(await r.json()).project;if(EXCL.some(x=>String(pj.projectName||'').replace(/\s/g,'').includes(x))){X.add(id);continue;}P[id]={name:pj.projectName,cf:pj.customFields};
 const tj=await (await fetch(`${B}/tasks?projectId=${id}`)).json();
 (tj.projectTasks||[]).forEach(t=>{const k=t.taskId;(T[k]=T[k]||{t,in:[]}).in.push({p:id,cfv:t.customFieldValues});});}
const fid={},sid={};Object.entries(P).forEach(([pid,p])=>{const cf=p.cf||[];const nz=f=>String(f.fieldName||'').replace(/[\s*]/g,'');
 const f=cf.find(f=>nz(f)==='처리자');if(f)fid[pid]=f.fieldId;
 const st=cf.find(f=>nz(f)==='진행상태')||cf.find(f=>nz(f)==='상태');if(st)sid[pid]={id:st.fieldId,it:Object.fromEntries((st.selectItems||[]).map(i=>[i.id,i.value]))};});
const proc=e=>{const s=new Set();e.in.forEach(x=>{const v=(x.cfv||[]).find(c=>c.fieldId===fid[x.p]);(v?.memberIds||[]).forEach(m=>s.add(m));});return [...s];};
const stv=e=>{for(const x of e.in){const s=sid[x.p];if(!s)continue;const v=(x.cfv||[]).find(c=>c.fieldId===s.id);if(!v)continue;
 const l=(v.selectItemIds||(v.selectItemId?[v.selectItemId]:[])).map(i=>s.it[i]).filter(Boolean);if(l.length)return l.join(', ');if(v.value||v.text)return String(v.value||v.text);}return '';};
const live=Object.values(T).filter(e=>!e.t.deleted&&!e.t.binned&&!X.has(e.t.mainProjectId));
const rows=[],nod=[];
live.forEach(e=>{const t=e.t;const done=t.status?.taskStatusType==='CLOSE'; /* [완료] 체크 */const s=d10(t.due?.start)||d10(t.due?.end),en=d10(t.due?.end)||d10(t.due?.start);const pr=proc(e);
 const base={lv:t.parentTaskId?'하위':'상위',p:P[t.mainProjectId]?.name||P[e.in[0].p]?.name,par:t.parentTaskId?(T[t.parentTaskId]?.t.title||''):'',ti:t.title.trim(),pr,as:(t.assignees||[]).map(a=>a.assigneeId),st:(v=>(done?'완료':'진행중')+(v?`(${v})`:''))(stv(e)),done};
 if(!en){if(!done&&pr.length)nod.push(base);return;}
 if(done?(en<DS||s>DE):en<BASE)return; rows.push({...base,s,en});});
const ids=new Set();[...rows,...nod].forEach(r=>[...r.pr,...r.as].forEach(i=>ids.add(i)));
const us=await (await fetch('/api/v1/getContactUsers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids:[...ids]})})).json();
const U={};(Array.isArray(us)?us:(us.users||[])).forEach(u=>U[u.userId]=u.name);const nm=a=>a.map(i=>U[i]||'?').join('.');
g.out=rows.map(r=>[r.p,r.lv,r.par,r.ti,r.s.slice(2),r.en.slice(2),nm(r.pr),nm(r.as),r.st,r.done?'Y':'N'].join('|')).sort().join('\n').replace(/[0-9]{7,}/g,'#');
g.o3=nod.map(r=>[r.p,r.lv,r.par,r.ti,nm(r.pr),r.st].join('|')).sort().join('\n').replace(/[0-9]{7,}/g,'#');
g.stat=`range=${DS}~${DE} np=${projs.length} n404=${n404} excl=${X.size} rows=${rows.length} done=${rows.filter(r=>r.done).length} withProc=${rows.filter(r=>r.pr.length).length} nod=${nod.length} statusField=${Object.keys(sid).length}/${Object.keys(P).length} len=${g.out.length}/${g.o3.length}`;
}catch(e){g.stat='ERR '+e}g.done=true;})();'go'
```
- 실행 전에 스크립트 맨 위 `SPACE_ID`(링크가 가리키는 스페이스)와 `BASE`(기준일)를 바꾼다.
- 상태 필드: 프로젝트 customFields 중 `fieldName`에서 공백·`*` 제거 후 `진행상태`, 없으면 `상태`인 필드. 값은 `customFieldValues[fieldId].selectItemId(s)` → `selectItems`의 `id → value`.
- 결과 행 포맷: `프로젝트|유형(상위/하위)|상위업무제목(하위만)|업무명|YY-MM-DD 시작|YY-MM-DD 종료|처리자(.구분)|담당자(.구분)|상태|완료(Y/N)`, 기간 미설정: `프로젝트|유형|상위|업무명|처리자|상태`.
- 읽기: `g.out.slice(a,b)`를 **약 600자 단위**로 나눠 읽는다(겹치게 10자). 7자리 이상 숫자(사용자 ID)는 반드시 `#`로 치환해 출력(그대로 두면 도구 출력이 차단됨).
- 확장 프로그램이 간헐적으로 "failed in the extension" / "not in Claude's tab group"을 낸다: `tabs_context_mcp(createIfEmpty:true)`로 그룹을 다시 확인하고 같은 호출을 재시도한다. 스크립트 상태는 탭의 `window` 변수에 남아 있으니 재수집하지 않는다.
- 이전 결과와 비교가 필요하면 줄 단위 해시(`h=(h*31+codePoint)%99991`)를 브라우저와 로컬에서 각각 계산해 바뀐 줄만 확인한다.

## 엑셀 생성 (openpyxl, 시트 3개)
### 시트1 `인력 투입 현황`
- 열: A 부서명 / B 주 업무 / C 이름 / D 유형(너비 6) / E 할당 업무(너비 58) / F 기간(너비 13) / G 상태(너비 16) / H~ 날짜(너비 6.5). 1~2행 헤더(A~G는 세로 병합, 회색 `EDEDED`).
- 날짜 범위: 표시 범위(기준일이 속한 주의 **전 주 월요일**부터 7주, 일요일까지). 1행 주차 라벨(월~일 병합, `D9F2D0`), 2행 `M/D`. 주말·공휴일 헤더는 `F8CBAD`, 본문은 `FBEDEE`.
- 주차 라벨은 사용자 양식 관례를 따른다(예: 9/28주=`9M 5W`, 10/5=`10M 1W` … 10/26=`10M 4W`, 11/2=`11M 1W`). 양식에 오타(중복 라벨)가 있으면 바로잡고 보고.
- 기준일 열 왼쪽에 빨간 굵은 세로선(`FF0000`, medium).
- 최상단 '처리자 미지정 (N건)'(헤더 2행 바로 아래 3행부터): A~C 병합 라벨, D열 유형, E열 `[프로젝트명] 상위 > 업무명` 가나다 순, F열 `M/D ~ M/D`, G열 상태(회색 `EDEDED` 바탕, `595959` 글씨), 날짜 영역에 막대(`000066` 단색). 메모에 프로젝트·기간·담당자. 영역 아래(첫 부서 행 위) 진한 구분선(`7F7F7F` medium). 0건이면 영역을 만들지 않는다.
- 일정 행(업무 1건당 1행):
  - D열 유형: `상위`/`하위`(가운데 정렬, 9pt). 글씨색은 같은 행 할당 업무와 같다(완료면 회색).
  - E열 할당 업무: `[프로젝트명] 상위 > 업무명`(하위업무) 또는 `[프로젝트명] 업무명`(상위업무). 완료 업무는 앞에 `[완료] `. 9pt 맑은 고딕, 줄바꿈(wrap_text) 허용, 두 줄이 되면 행 높이 30.
  - F열 기간: `M/D ~ M/D`(가운데 정렬). G열 상태: 위 '상태 표시' 규칙 값(가운데 정렬).
  - 미완료 업무 D~F 글씨는 검정, 완료 업무는 회색 `808080`.
  - 셀 메모(E열): `[프로젝트]\n업무명\n시작 ~ 종료\n상태: ..\n처리자: ..\n담당자: ..`.
- 업무 막대: 시작~종료 날짜 셀을 색으로만 채운다(셀 병합·텍스트 없음). 색은 **프로젝트와 관계없이 한 가지 `000066`**. 미완료는 단색 `PatternFill('solid', fgColor='000066')`, 완료는 빗금 `PatternFill('lightUp', fgColor='000066', bgColor='FFFFFF')`. 주말·공휴일 칸도 막대 채우기가 우선. 범위 밖은 표시 범위로 잘라 그림.
- 사람별 행 = 일정 행(업무 1건당 1행, 최소 1; 단 기간 미설정만 있으면 0) + 기간 미설정 행 수. 기간 미설정 행은 D열 유형과 E열(`[프로젝트명] 상위 > 업무명`) `FFF2CC` 바탕/`7F6000` 글씨, F열 `기간 미설정`, G열 상태(같은 바탕), 날짜 영역은 회색 `F2F2F2`, 첫 기간 미설정 행 위쪽에 진한 구분선(`7F7F7F` medium).
- 업무 없는 사람도 1행 유지.
- 틀 고정 `H3`(처리자 미지정 영역은 고정하지 않고 함께 스크롤). 표 아래 범례 2개: `진행중`(단색 `000066`), `완료`(빗금 `000066`).

### 시트2 `대상 업무 목록`
대상 기간 업무 전체(처리자 유무 무관, 표시 범위에 걸친 완료 업무 포함), 종료일→시작일 순. 열: 프로젝트명 | 유형(상위/하위) | 상위 업무(하위업무인 경우) | 업무명 | 시작일 | 종료일 | 상태 | 처리자 | 담당자 | 현황표 반영(O/X) | 비고(처리자 없음 / 양식에 없는 처리자: ..). 헤더 `1F4E78` 흰 굵은 글씨, 날짜 `yyyy-mm-dd`, 반영 X 행은 회색 글씨, 자동 필터·A2 고정.

### 시트3 `기간 미설정(처리자 있음)`
프로젝트명 | 유형(상위/하위) | 상위 업무 | 업무명 | 상태 | 처리자.

### 파일
`/mnt/user-data/outputs/플랫폼_워크스페이스_인력투입현황_처리자기준_YYYYMMDD.xlsx` (프로젝트 링크면 프로젝트명으로) → SendUserFile. 저장 후 LibreOffice로 PDF→PNG 렌더해 레이아웃 확인.

## 마무리 보고 (짧게)
- 대상 범위(링크가 가리키는 위치), 조회 불가(삭제) 프로젝트 수, 제외한 프로젝트(배포리스트관리) 수
- 대상 업무 N건(미완료/완료) 중 처리자 있는 건수, 현황표에 그린 막대 수, 업무가 많은 사람(행 수 상위)
- 기간 미설정(처리자 있음) 건수, 처리자 미지정 건수
- 양식에 없는 처리자 이름, 상태 필드(진행상태/상태)가 없는 프로젝트
- 이전 추출 대비 변화가 있으면 한 줄
- 끝에 `Sources: [플랫폼_워크스페이스](링크)`