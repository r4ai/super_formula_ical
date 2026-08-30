import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from sf_calendar.generator import collect_events_for_years
from sf_calendar.models import Race, RaceSchedule, Season


class StubScheduleSource:
    def season(self, year: int) -> Season:
        return Season(
            source_url=f"https://example.test/{year}/",
            races=(
                Race(
                    label="Rd.1",
                    start=date(year, 4, 5),
                    end=date(year, 4, 6),
                    detail_url="https://example.test/race/1/",
                ),
            ),
        )

    def race_schedule(self, url: str) -> RaceSchedule:
        return RaceSchedule(title="Rd.1", source_url=url, rows=())


class GeneratorArchitectureTests(unittest.TestCase):
    def test_uses_source_contract_and_combines_seasons_chronologically(self) -> None:
        events = collect_events_for_years(StubScheduleSource(), [2026, 2025])

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].start.year, 2025)
        self.assertEqual(events[1].start.year, 2026)
        self.assertIn("開催期間・時刻未定", events[0].summary)
        self.assertIn("開催期間・時刻未定", events[1].summary)


if __name__ == "__main__":
    unittest.main()
