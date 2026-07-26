import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = (
    Path(__file__).parents[1]
    / ".github"
    / "scripts"
    / "create_rejection_issue_files.py"
)
SPEC = importlib.util.spec_from_file_location(
    "create_rejection_issue_files",
    SCRIPT_PATH,
)
assert SPEC and SPEC.loader
create_rejection_issue_files = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(create_rejection_issue_files)


class MainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.review_file = self.root / "copilot-review.json"
        self.title_file = self.root / "issue-title.txt"
        self.body_file = self.root / "issue-body.md"

        for attribute, path in (
            ("REVIEW_FILE", self.review_file),
            ("TITLE_FILE", self.title_file),
            ("BODY_FILE", self.body_file),
        ):
            self.enterContext(
                mock.patch.object(
                    create_rejection_issue_files,
                    attribute,
                    path,
                )
            )
        self.enterContext(
            mock.patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "owner/repository",
                    "GITHUB_RUN_ID": "123",
                },
            )
        )

    def test_rejects_incomplete_review_payload(self) -> None:
        self.review_file.write_text(
            json.dumps(
                {
                    "issue_title": " ",
                    "issue_body": "The generated calendar lost an event.",
                    "summary": "One event was removed.",
                    "reason": "The removal was not explained.",
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            create_rejection_issue_files.load_payload()

    def test_writes_review_issue_files(self) -> None:
        payload = {
            "issue_title": "Schedule update needs review",
            "issue_body": "The generated calendar lost an event.",
            "summary": "One event was removed.",
            "reason": "The removal was not explained.",
        }
        self.review_file.write_text(json.dumps(payload), encoding="utf-8")

        exit_code = create_rejection_issue_files.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            self.title_file.read_text(encoding="utf-8"),
            payload["issue_title"],
        )
        self.assertEqual(
            self.body_file.read_text(encoding="utf-8"),
            "\n\n".join(
                [
                    payload["issue_body"],
                    "Workflow run: https://github.com/owner/repository/actions/runs/123",
                    "Copilot review summary:",
                    payload["summary"],
                    "Copilot review reason:",
                    payload["reason"],
                ]
            )
            + "\n",
        )

    def test_uses_failure_payload_when_review_file_is_missing(self) -> None:
        exit_code = create_rejection_issue_files.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            self.title_file.read_text(encoding="utf-8"),
            create_rejection_issue_files.FALLBACK_PAYLOAD["issue_title"],
        )
        self.assertIn(
            create_rejection_issue_files.FALLBACK_PAYLOAD["reason"],
            self.body_file.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
