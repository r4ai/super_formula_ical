#!/usr/bin/env python3
import argparse
import sys

from sf_calendar.generator import ScheduleSource, collect_events_for_years
from sf_calendar.ics import build_ics
from sf_calendar.website import SuperFormulaWebsite

SUPPORTED_YEARS = {2025, 2026}


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


def main(source: ScheduleSource | None = None) -> int:
    args = parse_args()
    years = sorted(set(args.years))
    schedule_source = source if source is not None else SuperFormulaWebsite()
    sys.stdout.write(build_ics(collect_events_for_years(schedule_source, years)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
