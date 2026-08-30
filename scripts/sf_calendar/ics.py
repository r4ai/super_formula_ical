from collections.abc import Iterable

from .models import AllDayEvent, Event, TimedEvent

TZID = "Asia/Tokyo"
PRODID = "-//r4ai//superformula-to-ics//JP"


def escape_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def event_time_lines(event: Event) -> tuple[str, str]:
    if isinstance(event, TimedEvent):
        return (
            f"DTSTART;TZID={TZID}:{event.start:%Y%m%dT%H%M%S}",
            f"DTEND;TZID={TZID}:{event.end:%Y%m%dT%H%M%S}",
        )

    assert isinstance(event, AllDayEvent)
    return (
        f"DTSTART;VALUE=DATE:{event.start:%Y%m%d}",
        f"DTEND;VALUE=DATE:{event.end:%Y%m%d}",
    )


def build_ics(events: Iterable[Event]) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}"]
    for event in events:
        start_line, end_line = event_time_lines(event)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"SUMMARY:{escape_text(event.summary)}",
                start_line,
                end_line,
                f"UID:{event.uid}",
                f"DESCRIPTION:{escape_text(event.description)}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"
