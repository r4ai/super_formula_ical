import argparse
import importlib.util
import io
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

SCRIPTS_PATH = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_PATH))
SCRIPT_PATH = SCRIPTS_PATH / "superformula_to_ics.py"
SPEC = importlib.util.spec_from_file_location("superformula_to_ics", SCRIPT_PATH)
assert SPEC and SPEC.loader
superformula_to_ics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(superformula_to_ics)

from sf_calendar.models import TimedEvent


class MainTests(unittest.TestCase):
    def test_normalizes_years_and_writes_escaped_ics(self) -> None:
        event = TimedEvent(
            summary=r"Race, Final; A\B",
            description="Line 1\nLine, 2",
            start=datetime(2026, 4, 5, 10, 0, tzinfo=UTC),
            end=datetime(2026, 4, 5, 11, 0, tzinfo=UTC),
            uid="event@example.com",
        )
        source = mock.Mock()
        stdout = io.StringIO()

        with (
            mock.patch.object(
                superformula_to_ics,
                "parse_args",
                return_value=argparse.Namespace(years=[2026, 2025, 2026]),
            ),
            mock.patch.object(
                superformula_to_ics, "collect_events_for_years", return_value=[event]
            ) as collect_events,
            mock.patch.object(
                superformula_to_ics, "SuperFormulaWebsite", return_value=source
            ),
            mock.patch("sys.stdout", stdout),
        ):
            exit_code = superformula_to_ics.main()

        self.assertEqual(exit_code, 0)
        collect_events.assert_called_once_with(source, [2025, 2026])
        self.assertIn(r"SUMMARY:Race\, Final\; A\\B", stdout.getvalue())


class ParseArgsTests(unittest.TestCase):
    def test_accepts_supported_years(self) -> None:
        with mock.patch.object(sys, "argv", ["superformula_to_ics.py", "2025", "2026"]):
            args = superformula_to_ics.parse_args()

        self.assertEqual(args.years, [2025, 2026])

    def test_rejects_unsupported_year(self) -> None:
        with (
            mock.patch.object(sys, "argv", ["superformula_to_ics.py", "2027"]),
            mock.patch("sys.stderr", new_callable=io.StringIO),
            self.assertRaisesRegex(SystemExit, "2"),
        ):
            superformula_to_ics.parse_args()


if __name__ == "__main__":
    unittest.main()
