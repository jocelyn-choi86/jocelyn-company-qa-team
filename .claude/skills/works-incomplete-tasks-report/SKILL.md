---
name: works-incomplete-tasks-report
description: Pull incomplete-task lists from LINE Works Project (플랫폼_워크스페이스) — full workspace or filtered to specific project name(s) — and build the 15-column hierarchical Excel report Jocelyn uses, including the weekly automated version.
---

# LINE Works Project — 미완료 업무 리스트 (Incomplete Tasks Report)

Use this skill whenever Jocelyn asks for an incomplete-task list / report from LINE Works Project (project.worksmobile.com) — either the full weekly workspace report, or an ad-hoc extract filtered to one or more named projects (e.g. "26년도_9월_운영이슈 프로젝트만 목록 추출해줘"). A project-name filter request is a one-off extraction, not a change to the scheduled weekly report — just produce and deliver the filtered file.

## Access

project.worksmobile.com requires an authenticated session; WebFetch is blocked by the login redirect. Always access it through the existing authenticated browser tab via Claude-in-Chrome tools (`tabs_context_mcp`, `javascript_tool`/`javascript_exec`, `navigate`, `computer`). Do not attempt WebFetch on this domain.

Known constants for Jocelyn's workspace:
- `domainId`: `300018117`
- 플랫폼_워크스페이스 space slug: `s-300018117-b0ce5784-0782-46a2-b336-c5a0d79c8b32`

## API endpoints (call via `javascript_tool` fetch from the authenticated tab)

- `GET /rd/{domainId}/api/v1/spaces/{spaceSlug}` → `{ rootFolder: {...} }`. Walk `rootFolder.children[]` recursively: an item with `jsonTypeHint: "FolderChildProject"` is a leaf project (has `projectId`); an item with `jsonTypeHint: "Folder"` has its own `.children` to recurse into. Collect all leaf `projectId`s this way (33 projects in 플랫폼_워크스페이스 as of last run).
- `GET /rd/{domainId}/api/v1/projects/{projectId}` → `{ project: {...} }`, including `project.customFields` (field definitions).
- `GET /rd/{domainId}/api/v1/tasks?projectId={projectId}` → `{ projectTasks: [...] }`, each task carrying `customFieldValues` inline.
- `POST /api/v1/getContactUsers` with body `{"ids": [...]}` → resolves user IDs to display names. Collect every unique assignee/creator ID across the pulled tasks and resolve in one batch call.

When filtering to specific project name(s): walk the folder tree, match `project` objects by exact name, and only fetch tasks for the matched project ID(s) rather than all 33.

## Field mapping — do it robustly

- Field definitions use `fieldId` (not `customFieldId`); a field's `selectItems` array items use `id` (not `selectItemId`).
- Custom field *type* names vary even for equivalent fields (e.g. a "진행 상태" field can be `jsonTypeHint: "SingleSelectCustomField"` on one project and `"StatusSelectCustomField"` on another, with the same underlying shape). **Never branch label-resolution logic on the `jsonTypeHint` string.** Instead branch on which property exists on the custom-field *value* object: `selectItemId` (single-select → look up label in the field's `selectItems`), `selectItemIds` (multi-select), `date`, `memberIds`. This is the only way to avoid raw GUIDs leaking into output — after building a row set, sanity-check with a regex like `/^[0-9a-f]{8}-[0-9a-f]{4}-/` to confirm no unresolved GUIDs remain in any column.

## Completion rule

Use `status.taskStatusType` as the sole source of truth for incomplete/complete: `"OPEN"` = incomplete (include), `"CLOSE"` = complete (exclude). Do not filter on the custom "진행 상태" field — it can diverge or lag behind the system status; it is still shown in the output as a display-only column, just not used as the completion filter.

## Hierarchy

`parentTaskId === null` → top-level task (업무). `parentTaskId` set → subtask (하위업무), grouped under that parent. Always include subtasks in the output (never top-level-only). If a subtask's parent isn't present in the incomplete set (e.g. parent already closed), treat it as an orphan and still include it (check for this case, but no special row treatment is needed if none occur).

## Scope

Default scope is 플랫폼_워크스페이스 only — never other spaces unless asked. Default is all projects in that space; when Jocelyn names one or more specific projects, restrict to only those.

## Sort order

1. 프로젝트명 (project name)
2. 어플리케이션 (app)
3. 업무 그룹: top-level tasks sorted by 어플리케이션 asc then 업무명 asc (tiebreak); each top-level task's own subtasks (sorted by 업무명 asc) are placed immediately below it, before moving to the next top-level task.

Do **not** sort by 기한 (due date) at all, ascending or descending — that criterion was explicitly removed and should not reappear even as a tiebreaker.

## Output format — 15 columns, in this exact order

프로젝트명 / 유형 / 업무구분 / 어플리케이션 / 업무명 / 업무구분 : 하위업무 / (하위업무) 업무명 / 기한 / 시작일 / 마감일 / 담당자 / 진행상태 / 생성일 / 생성자 / 요청기한

Subtask display rule (this is the current, final format — supersedes any older flag-based single-column 업무구분 layout):

- **Top-level (최상위) task row**: fill 유형 / 업무구분(값: "업무") / 어플리케이션 / 업무명. Leave "업무구분 : 하위업무" and "(하위업무) 업무명" blank.
- **Subtask row**: leave 유형 / 업무구분 / 어플리케이션 / 업무명 blank. Fill "업무구분 : 하위업무" with the subtask's *own* 어플리케이션 값 (it can differ from the parent's), and "(하위업무) 업무명" with the subtask's title.
- 담당자 / 진행상태 / 생성일 / 생성자 / 기한 / 시작일 / 마감일 / 요청기한: filled per-row for both top-level and subtask rows, each using its own values.
- 기한 / 시작일 / 마감일 are three independent fields — pull each from its own custom field/value and never derive or copy one from another, even when a task's underlying data happens to make two of them equal.
- Empty/missing values render as `-`.

## Reliable bulk extraction out of the browser tab

`get_page_text` is highly unreliable for pulling large generated text back out of a live tab this session (works on `text/html`+`<pre>` blobs, essentially never on `text/plain` blobs or injected DOM text). Use this instead:

1. Build the full pipe-delimited output text in-page as a `window.__pipeText` (or similarly named) variable, escaping any literal `|` and newlines inside field values first.
2. Read it back via `javascript_tool` in small fixed-size slices (300 chars is a safe size for Korean-heavy text) using an expression like:
   `(function(){const s=<start>,e=<end>;const c=window.__pipeText.slice(s,e);return c+'<<<END'+c.length+'>>>';})()`
3. **Every chunk must be verified**: confirm the number after `<<<END` matches the actual chunk length before trusting it. Silent truncation (missing trailing content with no `[TRUNCATED]` indicator) has occurred with naive slicing — the marker catches this.
4. Batch multiple slice-read calls together via `browser_batch` in one round trip when there are several chunks.
5. Reconstruct the full text by concatenating verified chunks in order (a small Python script that strips tool-output prefixes and `<<<ENDnnn>>>` markers works well for this), then verify: total reconstructed length matches the sum of chunk marker lengths, line count matches expected row count + 1 header, and every data line has exactly 14 `|` separators (15 columns).

### Tab-group instability workaround

`javascript_tool` / `get_page_text` / `computer` / `tabs_close_mcp` calls frequently report `"Tab X is not in Claude's tab group for this session"` even when the script actually executed successfully server-side. Never trust a reported failure at face value: check the relevant `window.*` state with a cheap follow-up call before assuming an operation didn't happen, and simply retry the identical call (often succeeds immediately) or call `tabs_context_mcp` first to refresh tab-group awareness. Design extraction scripts to be idempotent/resumable so a retry is always safe.

## Building the Excel file

Follow `/mnt/skills/public/xlsx/SKILL.md` conventions (openpyxl, no hardcoded formula results — not applicable here since there are no formulas). Match these established styling conventions:

- Font: Arial, size 10 for data, bold white on header.
- Header row fill: solid `4472C4` (blue), header font white bold, centered, thin light-gray (`D9D9D9`) borders on every cell.
- Title row: merged across all columns, left-aligned, size 12 bold, text like `"AGL {scope} - 완료되지 않은 업무 리스트 (생성일: {오늘 날짜 YYYY-MM-DD})"` where `{scope}` is `"플랫폼_워크스페이스"` for the full report or the specific project name for a filtered extract.
- Freeze panes below the header row; autofilter on the header row.
- Center-align columns: 유형, 업무구분, 업무구분 : 하위업무, 기한, 시작일, 마감일, 진행상태, 생성일, 요청기한. Left-align + wrap columns: 어플리케이션, 업무명, (하위업무) 업무명, 담당자, 생성자.
- Merge consecutive cells in the 프로젝트명 column that share the same value (group visually rather than repeating the project name every row).
- Tune column widths per column (프로젝트명 ~26, 유형 ~14, 업무구분 ~10, 어플리케이션 ~16, 업무명 ~40, 업무구분 : 하위업무 ~14, (하위업무) 업무명 ~40, 기한 ~11, 시작일 ~11, 마감일 ~11, 담당자 ~16, 진행상태 ~12, 생성일 ~11, 생성자 ~10, 요청기한 ~11).

## Filenames and delivery

- Full workspace weekly report: `/mnt/user-data/outputs/미완료_업무_리스트.xlsx`.
- Filtered to a specific project: `/mnt/user-data/outputs/{프로젝트명}_미완료업무.xlsx`.

Deliver via `SendUserFile`. Do not touch the scheduled weekly task when the request is a one-off project-filtered extract — only update it when Jocelyn explicitly asks to change the recurring report itself.

## Scheduling (recurring weekly report only)

The full-workspace report runs weekly, Wednesday 10:00 AM KST, via a scheduled task (managed with `mcp__claude-code-remote__update_trigger` / `create_trigger` — never local cron tools, since those don't survive session end). KST is UTC+9, so 10:00 AM KST = 01:00 UTC → cron `0 1 * * 3`. The scheduled task's prompt should always be kept in sync with the exact column order, hierarchy display rule, and sort order documented above whenever Jocelyn asks to change the format or sort — update the trigger's prompt via `update_trigger`, and only regenerate/send an actual Excel file if she separately asks for one (a request like "프롬프트만 업데이트해줘" means trigger-prompt-only, no file output).
