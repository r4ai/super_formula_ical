import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from sf_calendar.generator import TOKYO, build_uid, collect_events, normalize_time_range
from sf_calendar.models import AllDayEvent, ScheduleRow
from sf_calendar.website import SuperFormulaWebsite


class NormalizeTimeRangeTests(unittest.TestCase):
    def test_normalizes_supported_time_formats(self) -> None:
        cases = [
            (
                "10:15 - 11:30",
                "Q1",
                datetime(2026, 4, 5, 10, 15, tzinfo=TOKYO),
                datetime(2026, 4, 5, 11, 30, tzinfo=TOKYO),
            ),
            (
                "23:30 - 00:15",
                "決勝",
                datetime(2026, 4, 5, 23, 30, tzinfo=TOKYO),
                datetime(2026, 4, 6, 0, 15, tzinfo=TOKYO),
            ),
            (
                "09:00 - [最大90分]",
                "決勝",
                datetime(2026, 4, 5, 9, 0, tzinfo=TOKYO),
                datetime(2026, 4, 5, 10, 30, tzinfo=TOKYO),
            ),
            (
                "08:00",
                "Q2",
                datetime(2026, 4, 5, 8, 0, tzinfo=TOKYO),
                datetime(2026, 4, 5, 8, 30, tzinfo=TOKYO),
            ),
            (
                "14:00",
                "決勝",
                datetime(2026, 4, 5, 14, 0, tzinfo=TOKYO),
                datetime(2026, 4, 5, 15, 15, tzinfo=TOKYO),
            ),
        ]

        for time_cell, label, expected_start, expected_end in cases:
            with self.subTest(time_cell=time_cell, label=label):
                row = ScheduleRow(time_cell, label, 4, 5)
                self.assertEqual(
                    normalize_time_range(2026, row), (expected_start, expected_end)
                )

    def test_rejects_time_cell_without_a_start_time(self) -> None:
        self.assertIsNone(normalize_time_range(2026, ScheduleRow("TBA", "決勝", 4, 5)))


class CalendarGenerationTests(unittest.TestCase):
    def test_collects_only_calendar_events_in_chronological_order(self) -> None:
        race_url = "https://superformula.net/sf3/race/2026/"
        index_html = f"""
        <li><a href="{race_url}">
          <p class="box_txt01">Rd.1</p>
          <p class="inner01_txt01">4月5日(日) ~ 5日(日)</p>
        </a></li>
        """
        race_html = """
        <title>  SUPER FORMULA Rd.1 &amp;\nRace  </title>
        <span class="ank" id="schedule"></span>
        <table>
          <caption>4.5 SUN</caption>
          <tr><th>12:00</th><td>フリー走行</td></tr>
          <tr><th>10:00 - 10:30</th><td>Q1</td></tr>
          <tr><th>TBA</th><td>決勝</td></tr>
        </table>
        <span class="ank" id="entry"></span>
        """
        source = SuperFormulaWebsite(mock.Mock(side_effect=[index_html, race_html]))

        events = collect_events(source, 2026)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].summary, "SUPER FORMULA 2026 Q1")
        self.assertEqual(
            events[0].description, f"SUPER FORMULA Rd.1 & Race\n{race_url}"
        )
        self.assertEqual(events[0].start, datetime(2026, 4, 5, 10, 0, tzinfo=TOKYO))

    def test_uses_provisional_event_until_linked_race_schedule_is_published(
        self,
    ) -> None:
        race_url = "https://superformula.net/sf3/race/24431/"
        index_html = f"""
        <li><a href="{race_url}">
          <p class="box_txt01">Rd.9-10</p>
          <p class="inner01_txt01">10月09日(金) ~ 11日(日)</p>
        </a></li>
        """
        source = SuperFormulaWebsite(
            mock.Mock(side_effect=[index_html, "<title>2026 Rd.9-10 FUJI</title>"])
        )
        summary = "SUPER FORMULA 2026 Rd.9-10（開催期間・時刻未定）"

        self.assertEqual(
            collect_events(source, 2026),
            [
                AllDayEvent(
                    summary,
                    f"詳細日程公開後に自動更新されます。\n{race_url}",
                    date(2026, 10, 9),
                    date(2026, 10, 12),
                    build_uid(2026, summary, date(2026, 10, 9), race_url),
                )
            ],
        )

    def test_uses_index_as_source_when_race_detail_link_is_unavailable(self) -> None:
        index_url = "https://superformula.net/sf3/race_taxonomy/2026/"
        index_html = """
        <li><a href="#" style="pointer-events: none;">
          <p class="box_txt01">Rd.11-12</p>
          <p class="inner01_txt01">11月20日(金) ~ 22日(日)</p>
        </a></li>
        """
        fetcher = mock.Mock(return_value=index_html)

        events = collect_events(SuperFormulaWebsite(fetcher), 2026)

        self.assertEqual(
            events[0].description, f"詳細日程公開後に自動更新されます。\n{index_url}"
        )
        self.assertEqual(events[0].start, date(2026, 11, 20))
        self.assertEqual(events[0].end, date(2026, 11, 23))
        fetcher.assert_called_once_with(index_url)


if __name__ == "__main__":
    unittest.main()
