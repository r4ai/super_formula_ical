import argparse
import importlib.util
import io
import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "superformula_to_ics.py"
SPEC = importlib.util.spec_from_file_location("superformula_to_ics", SCRIPT_PATH)
assert SPEC and SPEC.loader
superformula_to_ics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(superformula_to_ics)


class RaceParsingTests(unittest.TestCase):
    def test_extracts_linked_and_unlinked_races_but_not_tests(self) -> None:
        html = """
        <li><a href="https://superformula.net/sf3/race/24431/">
          <p class="box_txt01">Rd.9-10</p>
          <p class="inner01_txt01">10月09日(金) ~ 11日(日)</p>
        </a></li>
        <li><a href="#" style="pointer-events: none;">
          <p class="box_txt01">Rd.11-12</p>
          <p class="inner01_txt01">11月20日(金) ~ 22日(日)</p>
        </a></li>
        <li><a href="https://superformula.net/sf3/race/24443/">
          <p class="box_txt01">Test.2</p>
          <p class="inner01_txt01">6月30日(火) ~ 01日(水)</p>
        </a></li>
        """

        self.assertEqual(
            superformula_to_ics.extract_races(html, 2026),
            [
                {
                    "label": "Rd.9-10",
                    "start": date(2026, 10, 9),
                    "end": date(2026, 10, 12),
                    "url": "https://superformula.net/sf3/race/24431/",
                },
                {
                    "label": "Rd.11-12",
                    "start": date(2026, 11, 20),
                    "end": date(2026, 11, 23),
                    "url": None,
                },
            ],
        )

    def test_normalizes_cross_month_race_period(self) -> None:
        html = """
        <li><a href="#">
          <p class="box_txt01">Rd.1</p>
          <p class="inner01_txt01">12月31日(木) ~ 01日(金)</p>
        </a></li>
        """

        race = superformula_to_ics.extract_races(html, 2026)[0]

        self.assertEqual(race["start"], date(2026, 12, 31))
        self.assertEqual(race["end"], date(2027, 1, 2))


class ScheduleParsingTests(unittest.TestCase):
    def test_extracts_rows_from_schedule_tables(self) -> None:
        html = """
        <span class="ank" id="schedule"></span>
        <table>
          <caption>4.5 SUN</caption>
          <tr><th><strong>10:00 - 10:30</strong></th><td>Q1</td></tr>
          <tr><th>  </th><td>Empty time</td></tr>
        </table>
        <table>
          <caption>Missing date</caption>
          <tr><th>11:00 - 12:00</th><td>決勝</td></tr>
        </table>
        <span class="ank" id="entry"></span>
        """

        self.assertEqual(
            superformula_to_ics.parse_schedule_rows(html),
            [("10:00 - 10:30", "Q1", 4, 5)],
        )

    def test_returns_no_rows_without_schedule_section(self) -> None:
        self.assertEqual(superformula_to_ics.parse_schedule_rows("<html></html>"), [])

    def test_extracts_section_before_escaped_anchor(self) -> None:
        html = (
            '<span class="ank" id="schedule"></span>'
            "schedule"
            r"<span class=\"ank\" id=\"entry\">"
        )

        self.assertEqual(
            superformula_to_ics.extract_schedule_section(html),
            "schedule",
        )


class NormalizeTimeRangeTests(unittest.TestCase):
    def test_normalizes_supported_time_formats(self) -> None:
        cases = [
            (
                "10:15 - 11:30",
                "Q1",
                datetime(2026, 4, 5, 10, 15, tzinfo=superformula_to_ics.TOKYO),
                datetime(2026, 4, 5, 11, 30, tzinfo=superformula_to_ics.TOKYO),
            ),
            (
                "23:30 - 00:15",
                "決勝",
                datetime(2026, 4, 5, 23, 30, tzinfo=superformula_to_ics.TOKYO),
                datetime(2026, 4, 6, 0, 15, tzinfo=superformula_to_ics.TOKYO),
            ),
            (
                "09:00 - [最大90分]",
                "決勝",
                datetime(2026, 4, 5, 9, 0, tzinfo=superformula_to_ics.TOKYO),
                datetime(2026, 4, 5, 10, 30, tzinfo=superformula_to_ics.TOKYO),
            ),
            (
                "08:00",
                "Q2",
                datetime(2026, 4, 5, 8, 0, tzinfo=superformula_to_ics.TOKYO),
                datetime(2026, 4, 5, 8, 30, tzinfo=superformula_to_ics.TOKYO),
            ),
            (
                "14:00",
                "決勝",
                datetime(2026, 4, 5, 14, 0, tzinfo=superformula_to_ics.TOKYO),
                datetime(2026, 4, 5, 15, 15, tzinfo=superformula_to_ics.TOKYO),
            ),
        ]

        for time_cell, label, expected_start, expected_end in cases:
            with self.subTest(time_cell=time_cell, label=label):
                self.assertEqual(
                    superformula_to_ics.normalize_time_range(
                        2026,
                        4,
                        5,
                        time_cell,
                        label,
                    ),
                    (expected_start, expected_end),
                )

    def test_rejects_time_cell_without_a_start_time(self) -> None:
        self.assertIsNone(
            superformula_to_ics.normalize_time_range(
                2026,
                4,
                5,
                "To be announced",
                "決勝",
            )
        )


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
        <title>  SUPER FORMULA Rd.1\nRace  </title>
        <span class="ank" id="schedule"></span>
        <table>
          <caption>4.5 SUN</caption>
          <tr><th>12:00</th><td>フリー走行</td></tr>
          <tr><th>10:00 - 10:30</th><td>Q1</td></tr>
          <tr><th>TBA</th><td>決勝</td></tr>
        </table>
        <span class="ank" id="entry"></span>
        """

        with (
            mock.patch.object(
                superformula_to_ics,
                "fetch",
                side_effect=[index_html, race_html],
            ),
            mock.patch("sys.stderr", new_callable=io.StringIO),
        ):
            events = superformula_to_ics.collect_events(2026)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["summary"], "SUPER FORMULA 2026 Q1")
        self.assertEqual(
            events[0]["description"],
            f"SUPER FORMULA Rd.1 Race\n{race_url}",
        )
        self.assertEqual(
            events[0]["start"],
            datetime(2026, 4, 5, 10, 0, tzinfo=superformula_to_ics.TOKYO),
        )

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

        with mock.patch.object(
            superformula_to_ics,
            "fetch",
            side_effect=[index_html, "<title>2026 Rd.9-10 FUJI</title>"],
        ):
            events = superformula_to_ics.collect_events(2026)

        self.assertEqual(
            events,
            [
                {
                    "summary": "SUPER FORMULA 2026 Rd.9-10（開催期間・時刻未定）",
                    "description": f"詳細日程公開後に自動更新されます。\n{race_url}",
                    "start": date(2026, 10, 9),
                    "end": date(2026, 10, 12),
                    "uid": superformula_to_ics.build_uid(
                        2026,
                        "SUPER FORMULA 2026 Rd.9-10（開催期間・時刻未定）",
                        date(2026, 10, 9),
                        race_url,
                    ),
                }
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

        with mock.patch.object(
            superformula_to_ics,
            "fetch",
            return_value=index_html,
        ) as fetch:
            events = superformula_to_ics.collect_events(2026)

        self.assertEqual(
            events[0]["description"], f"詳細日程公開後に自動更新されます。\n{index_url}"
        )
        self.assertEqual(events[0]["start"], date(2026, 11, 20))
        self.assertEqual(events[0]["end"], date(2026, 11, 23))
        fetch.assert_called_once_with(index_url)

    def test_main_normalizes_years_and_writes_escaped_ics(self) -> None:
        event = {
            "summary": r"Race, Final; A\B",
            "description": "Line 1\nLine, 2",
            "start": datetime(2026, 4, 5, 10, 0, tzinfo=superformula_to_ics.TOKYO),
            "end": datetime(2026, 4, 5, 11, 0, tzinfo=superformula_to_ics.TOKYO),
            "uid": "event@example.com",
        }
        stdout = io.StringIO()

        with (
            mock.patch.object(
                superformula_to_ics,
                "parse_args",
                return_value=argparse.Namespace(years=[2026, 2025, 2026]),
            ),
            mock.patch.object(
                superformula_to_ics,
                "collect_events_for_years",
                return_value=[event],
            ) as collect_events,
            mock.patch("sys.stdout", stdout),
        ):
            exit_code = superformula_to_ics.main()

        self.assertEqual(exit_code, 0)
        collect_events.assert_called_once_with([2025, 2026])
        self.assertEqual(
            stdout.getvalue(),
            "\n".join(
                [
                    "BEGIN:VCALENDAR",
                    "VERSION:2.0",
                    f"PRODID:{superformula_to_ics.PRODID}",
                    "BEGIN:VEVENT",
                    r"SUMMARY:Race\, Final\; A\\B",
                    "DTSTART;TZID=Asia/Tokyo:20260405T100000",
                    "DTEND;TZID=Asia/Tokyo:20260405T110000",
                    "UID:event@example.com",
                    r"DESCRIPTION:Line 1\nLine\, 2",
                    "END:VEVENT",
                    "END:VCALENDAR",
                    "",
                ]
            ),
        )

    def test_builds_all_day_ics_for_provisional_event(self) -> None:
        event = {
            "summary": "SUPER FORMULA 2026 Rd.9-10（開催期間・時刻未定）",
            "description": "詳細日程公開後に自動更新されます。",
            "start": date(2026, 10, 9),
            "end": date(2026, 10, 12),
            "uid": "provisional@example.com",
        }

        ics = superformula_to_ics.build_ics([event])

        self.assertIn("DTSTART;VALUE=DATE:20261009\n", ics)
        self.assertIn("DTEND;VALUE=DATE:20261012\n", ics)
        self.assertNotIn("DTSTART;TZID=", ics)


class ParseArgsTests(unittest.TestCase):
    def test_accepts_supported_years(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            ["superformula_to_ics.py", "2025", "2026"],
        ):
            args = superformula_to_ics.parse_args()

        self.assertEqual(args.years, [2025, 2026])

    def test_rejects_unsupported_year(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                ["superformula_to_ics.py", "2027"],
            ),
            mock.patch("sys.stderr", new_callable=io.StringIO),
        ):
            with self.assertRaisesRegex(SystemExit, "2"):
                superformula_to_ics.parse_args()


if __name__ == "__main__":
    unittest.main()
