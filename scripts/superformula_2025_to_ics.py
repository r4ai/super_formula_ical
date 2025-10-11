#!/usr/bin/env python3
import re
import sys
from datetime import datetime, timedelta, timezone
import urllib.request


BASE = "https://superformula.net/sf3"
YEAR = 2025


def fetch(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def extract_race_links(html: str):
    # Find race detail pages under /race/NNNNN/
    links = sorted(set(re.findall(r"https://superformula\.net/sf3/race/\d+/", html)))
    return links


def parse_schedule_tables(html: str):
    # Extract blocks for レーススケジュール tables
    # Each table has <caption> like '7.19<span class="get_day">(Sat)</span>'
    tables = []
    # Narrow to schedule section to avoid capturing event schedule
    # Get section starting at id="schedule" up to next section id or end
    m = re.search(r'<span class=\"ank\" id=\"schedule\"></span>(.*?)<span class=\\"ank\\" id=\\"', html, re.S)
    section = None
    if m:
        section = m.group(1)
    else:
        # fallback: use whole HTML
        section = html

    # Find each table
    for tmatch in re.finditer(r"<table>(.*?)</table>", section, re.S):
        thtml = tmatch.group(1)
        # caption date
        cm = re.search(r"<caption>\s*([0-9]{1,2})\.([0-9]{1,2})", thtml)
        if not cm:
            continue
        month = int(cm.group(1))
        day = int(cm.group(2))
        rows = []
        for r in re.finditer(r"<tr>\s*<th>(.*?)</th>\s*<td>(.*?)</td>\s*</tr>", thtml, re.S):
            time_cell = re.sub(r"<.*?>", "", r.group(1)).strip()
            label = re.sub(r"<.*?>", "", r.group(2)).strip()
            if not time_cell:
                continue
            rows.append((time_cell, label, month, day))
        if rows:
            tables.append(rows)
    return tables


def normalize_time_range(time_cell: str, label: str, month: int, day: int):
    # Examples: "09:10-09:20", "15:15-[36周/最大75分]", "10:25-10:35"
    start = None
    end = None
    m = re.match(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", time_cell)
    if m:
        sh, sm, eh, em = map(int, m.groups())
        start = datetime(YEAR, month, day, sh, sm, tzinfo=timezone(timedelta(hours=9)))
        end = datetime(YEAR, month, day, eh, em, tzinfo=timezone(timedelta(hours=9)))
        if end <= start:
            # Cross midnight (unlikely); add a day
            end = end + timedelta(days=1)
        return start, end
    # Start only with maximum duration info: e.g., 15:15-[..最大75分]
    m2 = re.match(r"(\d{1,2}):(\d{2})\s*-\s*\[.*?最大(\d{1,3})分.*\]", time_cell)
    if m2:
        sh, sm, maxmin = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        start = datetime(YEAR, month, day, sh, sm, tzinfo=timezone(timedelta(hours=9)))
        end = start + timedelta(minutes=maxmin)
        return start, end
    # If only start provided like "15:15-" or "15:15- [..]"
    m3 = re.match(r"(\d{1,2}):(\d{2})", time_cell)
    if m3:
        sh, sm = int(m3.group(1)), int(m3.group(2))
        start = datetime(YEAR, month, day, sh, sm, tzinfo=timezone(timedelta(hours=9)))
        # Default duration: 30 minutes for qualifying sessions; 75 minutes for races
        dur = 30
        if '決勝' in label:
            dur = 75
        end = start + timedelta(minutes=dur)
        return start, end
    return None, None


def ics_datetime(dt: datetime) -> str:
    # Use local time with TZID
    return dt.strftime('%Y%m%dT%H%M%S')


def escape_text(s: str) -> str:
    # Keep backslashes as-is so that inserted \n stays a single backslash+n for Google Calendar
    return s.replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def main():
    index_url = f"{BASE}/race_taxonomy/{YEAR}/"
    print(f"Fetching {index_url}...", file=sys.stderr)
    idx = fetch(index_url)
    links = extract_race_links(idx)
    # Filter out official tests (use title on page?) Keep all races with 'Rd' or that contain schedule tables with qualifying/race
    events = []
    for link in links:
        sys.stderr.write(f"Parsing {link}\n")
        html = fetch(link)
        # Title for context
        title_m = re.search(r"<title>(.*?)</title>", html, re.S)
        page_title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else link
        tables = parse_schedule_tables(html)
        # Collect only qualifying and race entries
        for rows in tables:
            for time_cell, label, month, day in rows:
                if not any(key in label for key in ["予選", "決勝", "Q1", "Q2"]):
                    continue
                start, end = normalize_time_range(time_cell, label, month, day)
                if not start or not end:
                    continue
                # Build summary
                summary = f"SUPER FORMULA {YEAR} {label}"
                # Description include page title and source link
                desc = f"{page_title}\\n{link}"
                events.append({
                    'summary': summary,
                    'description': desc,
                    'start': start,
                    'end': end,
                })

    # Build ICS
    lines = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//r4ai//superformula-2025//JP")
    tzid = "Asia/Tokyo"
    for ev in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"SUMMARY:{escape_text(ev['summary'])}")
        lines.append(f"DTSTART;TZID={tzid}:{ics_datetime(ev['start'])}")
        lines.append(f"DTEND;TZID={tzid}:{ics_datetime(ev['end'])}")
        uid = f"sf2025-{int(ev['start'].timestamp())}-{abs(hash(ev['summary']))}@superformula.net"
        lines.append(f"UID:{uid}")
        lines.append(f"DESCRIPTION:{escape_text(ev['description'])}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")

    ics = "\n".join(lines) + "\n"
    sys.stdout.write(ics)


if __name__ == "__main__":
    main()
