import re
import unittest
from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).parents[1]
    / ".github"
    / "workflows"
    / "update-superformula-ics.yml"
)


class ScheduleTests(unittest.TestCase):
    def test_scheduled_runs_avoid_the_top_of_the_hour(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        cron_expressions = re.findall(r'cron:\s*"([^"]+)"', workflow)

        self.assertTrue(cron_expressions)
        for expression in cron_expressions:
            with self.subTest(expression=expression):
                minute = expression.split(maxsplit=1)[0]
                self.assertNotEqual(minute, "0")


if __name__ == "__main__":
    unittest.main()
