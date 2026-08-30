import hashlib
import re
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

from .models import (
    AllDayEvent,
    Event,
    Race,
    RaceSchedule,
    ScheduleRow,
    Season,
    TimedEvent,
)

TOKYO = timezone(timedelta(hours=9))
TITLE_FILTERS = ("予選", "決勝", "Q1", "Q2")

type TimeRange = tuple[datetime, datetime]


class ScheduleSource(Protocol):
    def season(self, year: int) -> Season: ...

    def race_schedule(self, url: str) -> RaceSchedule: ...


def parse_explicit_end(start: datetime, remainder: str) -> datetime | None:
    end_match = re.match(r"\s*-\s*(\d{1,2}):(\d{2})", remainder)
    if end_match is None:
        return None

    end_hour, end_minute = map(int, end_match.groups())
    end = start.replace(hour=end_hour, minute=end_minute)
    # An end at or before the start denotes a session crossing midnight
    return end + timedelta(days=end <= start)


def normalize_time_range(year: int, row: ScheduleRow) -> TimeRange | None:
    start_match = re.match(r"(\d{1,2}):(\d{2})", row.time)
    if start_match is None:
        return None

    start_hour, start_minute = map(int, start_match.groups())
    start = datetime(year, row.month, row.day, start_hour, start_minute, tzinfo=TOKYO)
    remainder = row.time[start_match.end() :]

    end = parse_explicit_end(start, remainder)
    if end is not None:
        return start, end

    duration_match = re.match(r"\s*-\s*\[.*?最大(\d{1,3})分.*\]", remainder)
    if duration_match is not None:
        duration = int(duration_match.group(1))
    else:
        # The source omits some end times; race sessions use the established
        # 75-minute window while qualifying sessions use 30 minutes
        duration = 75 if "決勝" in row.label else 30

    return start, start + timedelta(minutes=duration)


def build_uid(year: int, summary: str, start: date | datetime, source_url: str) -> str:
    # Deterministic UIDs prevent duplicate imports across identical regenerations
    seed = f"{year}|{summary}|{start.isoformat()}|{source_url}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return f"sf{year}-{digest}@superformula.net"


def timed_event(
    year: int, schedule: RaceSchedule, row: ScheduleRow
) -> TimedEvent | None:
    if not any(keyword in row.label for keyword in TITLE_FILTERS):
        return None

    time_range = normalize_time_range(year, row)
    if time_range is None:
        return None

    start, end = time_range
    summary = f"SUPER FORMULA {year} {row.label}"
    return TimedEvent(
        summary=summary,
        description=f"{schedule.title}\n{schedule.source_url}",
        start=start,
        end=end,
        uid=build_uid(year, summary, start, schedule.source_url),
    )


def race_events(year: int, schedule: RaceSchedule) -> list[TimedEvent]:
    return [
        event
        for row in schedule.rows
        if (event := timed_event(year, schedule, row)) is not None
    ]


def provisional_event(year: int, race: Race, source_url: str) -> AllDayEvent:
    summary = f"SUPER FORMULA {year} {race.label}（開催期間・時刻未定）"
    return AllDayEvent(
        summary=summary,
        description=f"詳細日程公開後に自動更新されます。\n{source_url}",
        start=race.start,
        end=race.end,
        uid=build_uid(year, summary, race.start, source_url),
    )


def event_sort_key(event: Event) -> tuple[str, str]:
    return event.start.isoformat(), event.summary


def collect_events(source: ScheduleSource, year: int) -> list[Event]:
    season = source.season(year)
    events: list[Event] = []
    for race in season.races:
        detailed_events = (
            race_events(year, source.race_schedule(race.detail_url))
            if race.detail_url is not None
            else []
        )
        # Keep the race weekend visible until its detailed schedule is parseable
        events.extend(
            detailed_events
            or [provisional_event(year, race, race.detail_url or season.source_url)]
        )
    return sorted(events, key=event_sort_key)


def collect_events_for_years(source: ScheduleSource, years: list[int]) -> list[Event]:
    events = [event for year in years for event in collect_events(source, year)]
    return sorted(events, key=event_sort_key)
