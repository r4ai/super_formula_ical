from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class Race:
    label: str
    start: date
    end: date
    detail_url: str | None


@dataclass(frozen=True, slots=True)
class Season:
    source_url: str
    races: tuple[Race, ...]


@dataclass(frozen=True, slots=True)
class ScheduleRow:
    time: str
    label: str
    month: int
    day: int


@dataclass(frozen=True, slots=True)
class RaceSchedule:
    title: str
    source_url: str
    rows: tuple[ScheduleRow, ...]


@dataclass(frozen=True, slots=True)
class TimedEvent:
    summary: str
    description: str
    start: datetime
    end: datetime
    uid: str


@dataclass(frozen=True, slots=True)
class AllDayEvent:
    summary: str
    description: str
    start: date
    end: date
    uid: str


type Event = TimedEvent | AllDayEvent
