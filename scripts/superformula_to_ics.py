#!/usr/bin/env python3
import argparse
import hashlib
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import TypedDict


BASE_URL = "https://superformula.net/sf3"
TOKYO = timezone(timedelta(hours=9))
TZID = "Asia/Tokyo"
TITLE_FILTERS = ("予選", "決勝", "Q1", "Q2")
PRODID = "-//r4ai//superformula-to-ics//JP"
SUPPORTED_YEARS = {2025, 2026}
RACE_CARD_PATTERN = re.compile(
    r'<li>\s*<a href="(?P<url>[^"]+)"[^>]*>.*?'
    r'<p class="box_txt01">(?P<label>Rd\.[^<]+)</p>.*?'
    r'<p class="inner01_txt01">\s*'
    r"(?P<start_month>\d{1,2})月(?P<start_day>\d{1,2})日.*?~\s*"
    r"(?:(?P<end_month>\d{1,2})月)?(?P<end_day>\d{1,2})日",
    re.S,
)
RACE_URL_PATTERN = re.compile(r"https://superformula\.net/sf3/race/\d+/")


type ScheduleRow = tuple[str, str, int, int]
type TimeRange = tuple[datetime, datetime]


class Race(TypedDict):
    label: str
    start: date
    end: date
    url: str | None


class Event(TypedDict):
    summary: str
    description: str
    start: date | datetime
    end: date | datetime
    uid: str


def fetch(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def extract_race_links(html: str) -> list[str]:
    return sorted(set(re.findall(r"https://superformula\.net/sf3/race/\d+/", html)))


def extract_races(html: str, year: int) -> list[Race]:
    races: list[Race] = []
    for match in RACE_CARD_PATTERN.finditer(html):
        start_month = int(match.group("start_month"))
        start_day = int(match.group("start_day"))
        end_day = int(match.group("end_day"))
        end_month_text = match.group("end_month")
        end_month = (
            int(end_month_text)
            if end_month_text
            else start_month + (end_day < start_day)
        )
        end_year = year + (end_month < start_month or end_month > 12)
        end_month = (end_month - 1) % 12 + 1
        url = match.group("url")
        races.append(
            {
                "label": match.group("label").strip(),
                "start": date(year, start_month, start_day),
                "end": date(end_year, end_month, end_day) + timedelta(days=1),
                "url": url if RACE_URL_PATTERN.fullmatch(url) else None,
            }
        )
    return races


def extract_schedule_section(html: str) -> str | None:
    match = re.search(
        r'<span class="ank" id="schedule"></span>'
        r'(.*?)<span class=\\?"ank\\?" id=\\?"',
        html,
        re.S,
    )
    return match.group(1) if match else None


def parse_schedule_rows(html: str) -> list[ScheduleRow]:
    section = extract_schedule_section(html)
    if section is None:
        return []

    rows: list[ScheduleRow] = []
    for table_match in re.finditer(r"<table>(.*?)</table>", section, re.S):
        table_html = table_match.group(1)
        caption_match = re.search(r"<caption>\s*([0-9]{1,2})\.([0-9]{1,2})", table_html)
        if not caption_match:
            continue
        month = int(caption_match.group(1))
        day = int(caption_match.group(2))
        for row_match in re.finditer(
            r"<tr>\s*<th>(.*?)</th>\s*<td>(.*?)</td>\s*</tr>",
            table_html,
            re.S,
        ):
            time_cell = re.sub(r"<.*?>", "", row_match.group(1)).strip()
            label = re.sub(r"<.*?>", "", row_match.group(2)).strip()
            if time_cell:
                rows.append((time_cell, label, month, day))
    return rows


def normalize_time_range(
    year: int,
    month: int,
    day: int,
    time_cell: str,
    label: str,
) -> TimeRange | None:
    start_match = re.match(r"(\d{1,2}):(\d{2})", time_cell)
    if start_match is None:
        return None

    start_hour, start_minute = map(int, start_match.groups())
    start = datetime(year, month, day, start_hour, start_minute, tzinfo=TOKYO)
    remainder = time_cell[start_match.end() :]

    if end_match := re.match(r"\s*-\s*(\d{1,2}):(\d{2})", remainder):
        end_hour, end_minute = map(int, end_match.groups())
        end = datetime(year, month, day, end_hour, end_minute, tzinfo=TOKYO)
        if end <= start:
            end += timedelta(days=1)
        return start, end

    if duration_match := re.match(r"\s*-\s*\[.*?最大(\d{1,3})分.*\]", remainder):
        duration = int(duration_match.group(1))
    else:
        duration = 75 if "決勝" in label else 30

    return start, start + timedelta(minutes=duration)


def ics_datetime(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def escape_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_uid(year: int, summary: str, start: date | datetime, source_url: str) -> str:
    seed = f"{year}|{summary}|{start.isoformat()}|{source_url}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return f"sf{year}-{digest}@superformula.net"


def collect_race_events(year: int, source_url: str) -> list[Event]:
    events: list[Event] = []

    print(f"Parsing {source_url}", file=sys.stderr)
    html = fetch(source_url)
    title_match = re.search(r"<title>(.*?)</title>", html, re.S)
    page_title = (
        re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else source_url
    )
    for time_cell, label, month, day in parse_schedule_rows(html):
        if not any(keyword in label for keyword in TITLE_FILTERS):
            continue
        time_range = normalize_time_range(year, month, day, time_cell, label)
        if time_range is None:
            continue
        start, end = time_range
        summary = f"SUPER FORMULA {year} {label}"
        description = f"{page_title}\n{source_url}"
        events.append(
            {
                "summary": summary,
                "description": description,
                "start": start,
                "end": end,
                "uid": build_uid(year, summary, start, source_url),
            }
        )

    return events


def build_provisional_event(year: int, race: Race, index_url: str) -> Event:
    source_url = race["url"] or index_url

    summary = f"SUPER FORMULA {year} {race['label']}（開催期間・時刻未定）"
    return {
        "summary": summary,
        "description": f"詳細日程公開後に自動更新されます。\n{source_url}",
        "start": race["start"],
        "end": race["end"],
        "uid": build_uid(year, summary, race["start"], source_url),
    }


def event_sort_key(event: Event) -> tuple[str, str]:
    return event["start"].isoformat(), event["summary"]


def collect_events(year: int) -> list[Event]:
    index_url = f"{BASE_URL}/race_taxonomy/{year}/"
    print(f"Fetching {index_url}...", file=sys.stderr)
    index_html = fetch(index_url)
    events = [
        event
        for source_url in extract_race_links(index_html)
        for event in collect_race_events(year, source_url)
    ]
    descriptions = "\n".join(event["description"] for event in events)
    events.extend(
        build_provisional_event(year, race, index_url)
        for race in extract_races(index_html, year)
        if not re.search(rf"{re.escape(race['label'])}(?!\d)", descriptions)
    )
    return sorted(events, key=event_sort_key)


def collect_events_for_years(years: list[int]) -> list[Event]:
    events = [event for year in years for event in collect_events(year)]
    return sorted(events, key=event_sort_key)


def build_ics(events: list[Event]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
    ]
    for event in events:
        if isinstance(event["start"], datetime):
            assert isinstance(event["end"], datetime)
            start_line = f"DTSTART;TZID={TZID}:{ics_datetime(event['start'])}"
            end_line = f"DTEND;TZID={TZID}:{ics_datetime(event['end'])}"
        else:
            assert not isinstance(event["end"], datetime)
            start_line = f"DTSTART;VALUE=DATE:{event['start']:%Y%m%d}"
            end_line = f"DTEND;VALUE=DATE:{event['end']:%Y%m%d}"
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"SUMMARY:{escape_text(event['summary'])}",
                start_line,
                end_line,
                f"UID:{event['uid']}",
                f"DESCRIPTION:{escape_text(event['description'])}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an ICS file from SUPER FORMULA race schedules."
    )
    parser.add_argument(
        "years",
        type=int,
        nargs="+",
        help="Season years to generate, for example 2025 2026",
    )
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
    sys.stdout.write(build_ics(collect_events_for_years(years)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
