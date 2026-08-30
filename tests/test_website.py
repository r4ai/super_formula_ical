import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from sf_calendar.models import Race, ScheduleRow
from sf_calendar.website import parse_race_schedule, parse_season

INDEX_URL = "https://superformula.net/sf3/race_taxonomy/2026/"
RACE_URL = "https://superformula.net/sf3/race/24431/"


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
        <li>Unrelated navigation item</li>
        """

        self.assertEqual(
            parse_season(html, 2026, INDEX_URL).races,
            (
                Race("Rd.9-10", date(2026, 10, 9), date(2026, 10, 12), RACE_URL),
                Race("Rd.11-12", date(2026, 11, 20), date(2026, 11, 23), None),
            ),
        )

    def test_normalizes_cross_month_race_period(self) -> None:
        html = """
        <li><a href="#">
          <p class="box_txt01">Rd.1</p>
          <p class="inner01_txt01">12月31日(木) ~ 01日(金)</p>
        </a></li>
        """

        race = parse_season(html, 2026, INDEX_URL).races[0]

        self.assertEqual(race.start, date(2026, 12, 31))
        self.assertEqual(race.end, date(2027, 1, 2))

    def test_recovers_race_from_varied_markup_with_omitted_closing_tags(
        self,
    ) -> None:
        html = """
        <li data-kind="race">
          <a class="race-card" data-id="24431"
             href="https://superformula.net/sf3/race/24431/">
            <p class="featured box_txt01"><span>Rd.9&amp;10</span>
            <p data-label="period" class="compact inner01_txt01">
              <span>10月09日(金)</span> ～ <strong>10月11日(日)</strong>
        """

        self.assertEqual(
            parse_season(html, 2026, INDEX_URL).races,
            (Race("Rd.9&10", date(2026, 10, 9), date(2026, 10, 12), RACE_URL),),
        )


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
            parse_race_schedule(html, RACE_URL).rows,
            (ScheduleRow("10:00 - 10:30", "Q1", 4, 5),),
        )

    def test_returns_no_rows_without_schedule_section(self) -> None:
        self.assertEqual(parse_race_schedule("<html></html>", RACE_URL).rows, ())

    def test_uses_dom_structure_and_stops_at_the_next_section(self) -> None:
        html = """
        <span id="schedule" class="target ank"></span>
        <section>
          <table class="schedule">
            <caption><span>4</span>.<strong>5</strong> SUN</caption>
            <thead><tr><th>Time</th><th>Session</th></tr></thead>
            <tbody>
              <tr data-session="qualifying">
                <th class="time"><strong>10:00</strong> - 10:30</th>
                <td class="name"><span>Q1</span> &amp; Q2</td>
              </tr>
            </tbody>
          </table>
        </section>
        <span id="entry" class="ank"></span>
        <table><caption>4.6</caption><tr><th>11:00</th><td>決勝</td></tr></table>
        """

        self.assertEqual(
            parse_race_schedule(html, RACE_URL).rows,
            (ScheduleRow("10:00 - 10:30", "Q1 & Q2", 4, 5),),
        )


if __name__ == "__main__":
    unittest.main()
