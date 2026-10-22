"""aifit(com.icare.iweight) 기록 화면을 스크롤하며 데이터를 수집해 엑셀로 저장한다.

화면에 보이는 텍스트를 UI Automator로 읽고, 날짜가 적힌 줄을 기준으로
그 아래 텍스트들을 한 행으로 묶는다. 시작일보다 오래된 날짜가 나오거나
더 이상 스크롤되지 않으면 멈춘다.

사용법 (PowerShell):
    pip install uiautomator2 openpyxl
    # 1) 이미 뽑아둔 screen.xml로 파싱 결과만 확인
    python aifit_collect.py --test-xml $HOME\\Desktop\\screen.xml
    # 2) 폰에서 aifit 기록 목록 화면을 띄운 뒤 수집 실행
    python aifit_collect.py --start 2026-09-01 --end 2026-10-22
"""

import argparse
import datetime as dt
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

DATE_PATTERNS = [
    # 2026-09-01, 2026.09.01, 2026/9/1
    re.compile(r"(?P<y>20\d{2})\s*[-./]\s*(?P<m>\d{1,2})\s*[-./]\s*(?P<d>\d{1,2})"),
    # 2026년 9월 1일
    re.compile(r"(?P<y>20\d{2})\s*년\s*(?P<m>\d{1,2})\s*월\s*(?P<d>\d{1,2})\s*일"),
    # 9월 1일
    re.compile(r"(?<!\d)(?P<m>\d{1,2})\s*월\s*(?P<d>\d{1,2})\s*일"),
    # 09/01, 9.1 (시간 12:30, 소수 65.3과 구분하기 위해 텍스트 전체가 날짜일 때만)
    re.compile(r"^\s*(?P<m>\d{1,2})\s*[/.]\s*(?P<d>\d{1,2})\s*$"),
]
BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def parse_date(text, default_year):
    for pat in DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        g = m.groupdict()
        try:
            return dt.date(int(g.get("y") or default_year), int(g["m"]), int(g["d"]))
        except ValueError:
            continue
    return None


def extract_texts(xml_str):
    """UI 계층 XML에서 (top, left, text) 목록을 화면 위→아래, 왼쪽→오른쪽 순으로 반환."""
    root = ET.fromstring(xml_str)
    items = []
    for node in root.iter("node"):
        text = (node.get("text") or node.get("content-desc") or "").strip()
        if not text:
            continue
        b = BOUNDS_RE.match(node.get("bounds", ""))
        if not b:
            continue
        left, top = int(b.group(1)), int(b.group(2))
        items.append((top, left, text))
    items.sort()
    return items


def group_by_date(items, default_year):
    """날짜 텍스트를 만날 때마다 새 행을 시작한다. 첫 날짜 이전 텍스트는 버린다."""
    rows = []
    current = None
    for _, _, text in items:
        d = parse_date(text, default_year)
        if d:
            current = {"date": d, "date_text": text, "values": []}
            rows.append(current)
        elif current is not None:
            current["values"].append(text)
    return rows


def save_excel(path, rows, raw):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "데이터"
    width = max((len(r["values"]) for r in rows), default=0)
    ws.append(["날짜", "날짜(원문)"] + [f"항목{i + 1}" for i in range(width)])
    for r in rows:
        ws.append([r["date"], r["date_text"]] + r["values"])
    for row in ws.iter_rows(min_row=2, max_col=1):
        row[0].number_format = "yyyy-mm-dd"
    ws.freeze_panes = "A2"

    ws_raw = wb.create_sheet("원본")
    ws_raw.append(["페이지", "y", "x", "텍스트"])
    for rec in raw:
        ws_raw.append(list(rec))

    for sheet in (ws, ws_raw):
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width = 14
    wb.save(path)


def test_xml(path, default_year):
    items = extract_texts(Path(path).read_text(encoding="utf-8"))
    print(f"텍스트 {len(items)}개")
    for top, left, text in items:
        mark = "  <- 날짜" if parse_date(text, default_year) else ""
        print(f"  y={top:5d} x={left:5d}  {text}{mark}")
    rows = group_by_date(items, default_year)
    print(f"\n날짜 기준 행 {len(rows)}개")
    for r in rows:
        print(f"  {r['date']}  {r['values']}")


def collect(start, end, out_dir, max_pages, swipe_pause):
    import uiautomator2 as u2

    d = u2.connect()
    w, h = d.window_size()
    shot_dir = out_dir / "screens"
    shot_dir.mkdir(parents=True, exist_ok=True)

    rows, raw, seen = [], [], set()
    prev_page = None
    for page in range(1, max_pages + 1):
        items = extract_texts(d.dump_hierarchy())
        d.screenshot(str(shot_dir / f"page_{page:03d}.png"))
        raw.extend((page, top, left, text) for top, left, text in items)

        page_key = tuple(t for _, _, t in items)
        if page_key == prev_page:
            print("화면이 더 이상 바뀌지 않아 종료합니다.")
            break
        prev_page = page_key

        page_rows = group_by_date(items, start.year)
        oldest = None
        for r in page_rows:
            key = (r["date"], r["date_text"], tuple(r["values"]))
            oldest = r["date"] if oldest is None else min(oldest, r["date"])
            if key in seen or not (start <= r["date"] <= end):
                continue
            seen.add(key)
            rows.append(r)
        print(f"[{page}] 행 {len(page_rows)}개 읽음, 누적 {len(rows)}개, 가장 오래된 날짜 {oldest}")

        if oldest and oldest < start:
            print(f"{start} 이전 날짜에 도달해 종료합니다.")
            break
        # 화면 70% 지점에서 30% 지점으로 밀어 다음 목록을 불러온다
        d.swipe(w // 2, int(h * 0.7), w // 2, int(h * 0.3), 0.3)
        time.sleep(swipe_pause)

    # 스크롤 경계에서 같은 날짜가 잘려 두 번 읽히면 값이 더 많은 쪽만 남긴다
    best = {}
    for r in rows:
        k = (r["date"], r["date_text"])
        if k not in best or len(r["values"]) > len(best[k]["values"]):
            best[k] = r
    rows = sorted(best.values(), key=lambda r: r["date"])

    out = out_dir / f"aifit_{start:%Y%m%d}_{end:%Y%m%d}.xlsx"
    save_excel(out, rows, raw)
    print(f"\n저장: {out} (행 {len(rows)}개, 스크린샷 {shot_dir})")


def main():
    p = argparse.ArgumentParser(description="aifit 기록 화면 데이터를 엑셀로 수집")
    p.add_argument("--start", default="2026-09-01", type=dt.date.fromisoformat)
    p.add_argument("--end", default="2026-10-22", type=dt.date.fromisoformat)
    p.add_argument("--out", default=str(Path.home() / "Desktop" / "aifit"), help="저장 폴더")
    p.add_argument("--max-pages", type=int, default=200)
    p.add_argument("--pause", type=float, default=1.0, help="스크롤 후 대기 초")
    p.add_argument("--test-xml", help="수집 대신 저장된 screen.xml 파싱 결과만 출력")
    args = p.parse_args()

    if args.test_xml:
        test_xml(args.test_xml, args.start.year)
        return
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    collect(args.start, args.end, out_dir, args.max_pages, args.pause)


if __name__ == "__main__":
    sys.exit(main())
