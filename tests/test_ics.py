import sys
import unittest
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from sf_calendar.ics import build_ics
from sf_calendar.models import AllDayEvent, TimedEvent


class IcsGenerationTests(unittest.TestCase):
    def test_escapes_text_and_builds_timed_event(self) -> None:
        event = TimedEvent(
            summary=r"Race, Final; A\B",
            description="Line 1\nLine, 2",
            start=datetime(2026, 4, 5, 10, 0, tzinfo=UTC),
            end=datetime(2026, 4, 5, 11, 0, tzinfo=UTC),
            uid="event@example.com",
        )

        self.assertEqual(
            build_ics([event]),
            r"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//r4ai//superformula-to-ics//JP
BEGIN:VEVENT
SUMMARY:Race\, Final\; A\\B
DTSTART;TZID=Asia/Tokyo:20260405T100000
DTEND;TZID=Asia/Tokyo:20260405T110000
UID:event@example.com
DESCRIPTION:Line 1\nLine\, 2
END:VEVENT
END:VCALENDAR
""",
        )

    def test_builds_all_day_ics_for_provisional_event(self) -> None:
        event = AllDayEvent(
            summary="SUPER FORMULA 2026 Rd.9-10（開催期間・時刻未定）",
            description="詳細日程公開後に自動更新されます。",
            start=date(2026, 10, 9),
            end=date(2026, 10, 12),
            uid="provisional@example.com",
        )

        ics = build_ics([event])

        self.assertIn("DTSTART;VALUE=DATE:20261009\n", ics)
        self.assertIn("DTEND;VALUE=DATE:20261012\n", ics)
        self.assertNotIn("DTSTART;TZID=", ics)


if __name__ == "__main__":
    unittest.main()
