#!/usr/bin/env python3
import argparse
import hashlib
import re
import sys
from datetime import datetime, timedelta, timezone
import urllib.request


BASE_URL = "https://superformula.net/sf3"
TOKYO = timezone(timedelta(hours=9))
TZID = "Asia/Tokyo"
TITLE_FILTERS = ("予選", "決勝", "Q1", "Q2")
PRODID = "-//r4ai//superformula-to-ics//JP"
SUPPORTED_YEARS = {2025, 2026}


def fetch(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8", errors="ignore")


def extract_race_links(html: str) -> list[str]:
    return sorted(set(re.findall(r"https://superformula\.net/sf3/race/\d+/", html)))


def extract_schedule_section(html: str) -> str | None:
    patterns = (
        r'<span class="ank" id="schedule"></span>(.*?)<span class="ank" id="',
        r'<span class=\"ank\" id=\"schedule\"></span>(.*?)<span class=\\"ank\\" id=\\"',
    )
    for pattern in patterns:
        match = re.search(pattern, html, re.S)
        if match:
            return match.group(1)
    return None


def parse_schedule_rows(html: str) -> list[tuple[str, str, int, int]]:
    section = extract_schedule_section(html)
    if not section:
        return []

    rows: list[tuple[str, str, int, int]] = []
    for table_match in re.finditer(r"<table>(.*?)</table>", section, re.S):
        table_html = table_match.group(1)
        caption_match = re.search(r"<caption>\s*([0-9]{1,2})\.([0-9]{1,2})", table_html)
        if not caption_match:
            continue
        month = int(caption_match.group(1))
        day = int(caption_match.group(2))
        for row_match in re.finditer(r"<tr>\s*<th>(.*?)</th>\s*<td>(.*?)</td>\s*</tr>", table_html, re.S):
            time_cell = re.sub(r"<.*?>", "", row_match.group(1)).strip()
            label = re.sub(r"<.*?>", "", row_match.group(2)).strip()
            if time_cell:
                rows.append((time_cell, label, month, day))
    return rows


def normalize_time_range(year: int, month: int, day: int, time_cell: str, label: str) -> tuple[datetime, datetime] | tuple[None, None]:
    match = re.match(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", time_cell)
    if match:
        start_hour, start_minute, end_hour, end_minute = map(int, match.groups())
        start = datetime(year, month, day, start_hour, start_minute, tzinfo=TOKYO)
        end = datetime(year, month, day, end_hour, end_minute, tzinfo=TOKYO)
        if end <= start:
            end += timedelta(days=1)
        return start, end

    match = re.match(r"(\d{1,2}):(\d{2})\s*-\s*\[.*?最大(\d{1,3})分.*\]", time_cell)
    if match:
        start_hour, start_minute, max_minutes = map(int, match.groups())
        start = datetime(year, month, day, start_hour, start_minute, tzinfo=TOKYO)
        return start, start + timedelta(minutes=max_minutes)

    match = re.match(r"(\d{1,2}):(\d{2})", time_cell)
    if match:
        start_hour, start_minute = map(int, match.groups())
        start = datetime(year, month, day, start_hour, start_minute, tzinfo=TOKYO)
        default_duration = 75 if "決勝" in label else 30
        return start, start + timedelta(minutes=default_duration)

    return None, None


def ics_datetime(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def escape_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_uid(year: int, summary: str, start: datetime, source_url: str) -> str:
    seed = f"{year}|{summary}|{start.isoformat()}|{source_url}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return f"sf{year}-{digest}@superformula.net"


def collect_events(year: int) -> list[dict[str, str | datetime]]:
    index_url = f"{BASE_URL}/race_taxonomy/{year}/"
    print(f"Fetching {index_url}...", file=sys.stderr)
    index_html = fetch(index_url)
    events: list[dict[str, str | datetime]] = []

    for link in extract_race_links(index_html):
        print(f"Parsing {link}", file=sys.stderr)
        html = fetch(link)
        title_match = re.search(r"<title>(.*?)</title>", html, re.S)
        page_title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else link
        for time_cell, label, month, day in parse_schedule_rows(html):
            if not any(keyword in label for keyword in TITLE_FILTERS):
                continue
            start, end = normalize_time_range(year, month, day, time_cell, label)
            if not start or not end:
                continue
            summary = f"SUPER FORMULA {year} {label}"
            description = f"{page_title}\n{link}"
            events.append(
                {
                    "summary": summary,
                    "description": description,
                    "start": start,
                    "end": end,
                    "uid": build_uid(year, summary, start, link),
                }
            )

    return sorted(events, key=lambda event: (event["start"], event["summary"]))


def collect_events_for_years(years: list[int]) -> list[dict[str, str | datetime]]:
    events: list[dict[str, str | datetime]] = []
    for year in years:
        events.extend(collect_events(year))
    return sorted(events, key=lambda event: (event["start"], event["summary"]))


def build_ics(events: list[dict[str, str | datetime]], years: list[int]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
    ]
    for event in events:
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"SUMMARY:{escape_text(str(event['summary']))}",
                f"DTSTART;TZID={TZID}:{ics_datetime(event['start'])}",
                f"DTEND;TZID={TZID}:{ics_datetime(event['end'])}",
                f"UID:{event['uid']}",
                f"DESCRIPTION:{escape_text(str(event['description']))}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an ICS file from SUPER FORMULA race schedules.")
    parser.add_argument("years", type=int, nargs="+", help="Season years to generate, for example 2025 2026")
    args = parser.parse_args()

    unsupported_years = sorted(set(args.years) - SUPPORTED_YEARS)
    if unsupported_years:
        parser.error(
            f"unsupported year(s): {', '.join(map(str, unsupported_years))}. "
            "Supported years are 2025 and 2026."
        )

    return args


def main() -> int:
    args = parse_args()
    years = sorted(set(args.years))
    sys.stdout.write(build_ics(collect_events_for_years(years), years))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
