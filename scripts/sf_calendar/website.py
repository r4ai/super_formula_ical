import re
import sys
import urllib.request
from collections.abc import Callable
from datetime import date, timedelta

from selectolax.lexbor import LexborHTMLParser, LexborNode

from .models import Race, RaceSchedule, ScheduleRow, Season

BASE_URL = "https://superformula.net/sf3"
RACE_PERIOD_PATTERN = re.compile(
    r"(?P<start_month>\d{1,2})月\s*(?P<start_day>\d{1,2})日"
    r".*?[~～]\s*(?:(?P<end_month>\d{1,2})月\s*)?"
    r"(?P<end_day>\d{1,2})日"
)
CAPTION_DATE_PATTERN = re.compile(r"(?P<month>\d{1,2})\s*\.\s*(?P<day>\d{1,2})")
RACE_URL_PATTERN = re.compile(r"https://superformula\.net/sf3/race/\d+/")

type Fetcher = Callable[[str], str]


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

    # An omitted end month means the next month only when the day wraps backwards
    end_month = (
        int(end_month_text) if end_month_text else start_month + (end_day < start_day)
    )
    end_year = year + (end_month < start_month or end_month > 12)
    end_month = (end_month - 1) % 12 + 1

    # RFC 5545 defines an all-day DTEND as the first non-event day
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
    return Race(
        label=label,
        start=start,
        end=end,
        detail_url=href if RACE_URL_PATTERN.fullmatch(href) else None,
    )


def parse_season(html: str, year: int, source_url: str) -> Season:
    document = parse_html(html)
    races = tuple(
        race
        for card in document.css("li")
        if (race := parse_race_card(card, year)) is not None
    )
    return Season(source_url=source_url, races=races)


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
    # Race pages group sections by sibling anchors rather than a shared container
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
    return (
        ScheduleRow(time_cell, node_text(label_node), month, day) if time_cell else None
    )


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


def parse_race_schedule(html: str, source_url: str) -> RaceSchedule:
    document = parse_html(html)
    title = document.css_first("title")
    page_title = node_text(title) if title is not None else source_url
    rows = tuple(
        row
        for table in schedule_tables(document)
        for row in parse_schedule_table(table)
    )
    return RaceSchedule(title=page_title, source_url=source_url, rows=rows)


class SuperFormulaWebsite:
    def __init__(self, fetcher: Fetcher = fetch) -> None:
        self._fetch = fetcher

    def season(self, year: int) -> Season:
        source_url = f"{BASE_URL}/race_taxonomy/{year}/"
        print(f"Fetching {source_url}...", file=sys.stderr)
        return parse_season(self._fetch(source_url), year, source_url)

    def race_schedule(self, url: str) -> RaceSchedule:
        print(f"Parsing {url}", file=sys.stderr)
        return parse_race_schedule(self._fetch(url), url)
