#!/usr/bin/env python3
import argparse
import hashlib
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import TypedDict

from selectolax.lexbor import LexborHTMLParser, LexborNode

BASE_URL = "https://superformula.net/sf3"
TOKYO = timezone(timedelta(hours=9))
TZID = "Asia/Tokyo"
TITLE_FILTERS = ("予選", "決勝", "Q1", "Q2")
PRODID = "-//r4ai//superformula-to-ics//JP"
SUPPORTED_YEARS = {2025, 2026}
RACE_PERIOD_PATTERN = re.compile(
    r"(?P<start_month>\d{1,2})月\s*(?P<start_day>\d{1,2})日"
    r".*?[~～]\s*(?:(?P<end_month>\d{1,2})月\s*)?"
    r"(?P<end_day>\d{1,2})日"
)
CAPTION_DATE_PATTERN = re.compile(r"(?P<month>\d{1,2})\s*\.\s*(?P<day>\d{1,2})")
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


def parse_html(html: str) -> LexborHTMLParser:
    return LexborHTMLParser(html)


def node_text(node: LexborNode) -> str:
    return " ".join(node.text().split())


def race_dates(period: re.Match[str], year: int) -> tuple[date, date]:
    start_month = int(period.group("start_month"))
    start_day = int(period.group("start_day"))
    end_day = int(period.group("end_day"))
    end_month_text = period.group("end_month")
    end_month = (
        int(end_month_text) if end_month_text else start_month + (end_day < start_day)
    )
    end_year = year + (end_month < start_month or end_month > 12)
    end_month = (end_month - 1) % 12 + 1
    return date(year, start_month, start_day), date(
        end_year, end_month, end_day
    ) + timedelta(days=1)


def race_card_nodes(
    card: LexborNode,
) -> tuple[LexborNode, LexborNode, LexborNode] | None:
    link = card.css_first("a[href]")
    label = card.css_first(".box_txt01")
    period = card.css_first(".inner01_txt01")
    if link is None or label is None or period is None:
        return None
    return link, label, period


def parse_race_card(card: LexborNode, year: int) -> Race | None:
    nodes = race_card_nodes(card)
    if nodes is None:
        return None

    link, label_node, period_node = nodes
    label = node_text(label_node)
    period = RACE_PERIOD_PATTERN.search(node_text(period_node))
    if not label.startswith("Rd.") or period is None:
        return None

    start, end = race_dates(period, year)
    href = link.attributes.get("href") or ""
    return {
        "label": label,
        "start": start,
        "end": end,
        "url": href if RACE_URL_PATTERN.fullmatch(href) else None,
    }


def extract_races(document: LexborHTMLParser, year: int) -> list[Race]:
    return [
        race
        for card in document.css("li")
        if (race := parse_race_card(card, year)) is not None
    ]


def is_section_anchor(node: LexborNode) -> bool:
    return node.tag == "span" and "ank" in (node.attributes.get("class") or "").split()


def descendant_tables(node: LexborNode) -> list[LexborNode]:
    return [node] if node.tag == "table" else node.css("table")


def schedule_tables(document: LexborHTMLParser) -> list[LexborNode]:
    schedule_anchor = document.css_first("#schedule")
    if schedule_anchor is None:
        return []

    tables: list[LexborNode] = []
    sibling = schedule_anchor.next
    while sibling is not None and not is_section_anchor(sibling):
        tables.extend(descendant_tables(sibling))
        sibling = sibling.next
    return tables


def parse_schedule_row(row: LexborNode, month: int, day: int) -> ScheduleRow | None:
    time_node = row.css_first("th")
    label_node = row.css_first("td")
    if time_node is None or label_node is None:
        return None
    time_cell = node_text(time_node)
    return (time_cell, node_text(label_node), month, day) if time_cell else None


def parse_schedule_table(table: LexborNode) -> list[ScheduleRow]:
    caption = table.css_first("caption")
    caption_date = (
        CAPTION_DATE_PATTERN.search(node_text(caption)) if caption is not None else None
    )
    if caption_date is None:
        return []

    month = int(caption_date.group("month"))
    day = int(caption_date.group("day"))
    return [
        schedule_row
        for row in table.css("tr")
        if (schedule_row := parse_schedule_row(row, month, day)) is not None
    ]


def parse_schedule_rows(document: LexborHTMLParser) -> list[ScheduleRow]:
    return [
        row
        for table in schedule_tables(document)
        for row in parse_schedule_table(table)
    ]


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
    document = parse_html(fetch(source_url))
    title = document.css_first("title")
    page_title = node_text(title) if title is not None else source_url
    for time_cell, label, month, day in parse_schedule_rows(document):
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
    races = extract_races(parse_html(fetch(index_url)), year)
    events: list[Event] = []
    for race in races:
        race_events = (
            collect_race_events(year, race["url"]) if race["url"] is not None else []
        )
        events.extend(race_events or [build_provisional_event(year, race, index_url)])
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
