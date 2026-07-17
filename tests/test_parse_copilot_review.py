import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = (
    Path(__file__).parents[1] / ".github" / "scripts" / "parse_copilot_review.py"
)
SPEC = importlib.util.spec_from_file_location("parse_copilot_review", SCRIPT_PATH)
assert SPEC and SPEC.loader
parse_copilot_review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parse_copilot_review)


VALID_PAYLOAD = {
    "approved": True,
    "summary": "A routine schedule update.",
    "reason": "The calendar remains valid.",
    "issue_title": "",
    "issue_body": "",
}


class ExtractPayloadTests(unittest.TestCase):
    def test_extracts_plain_json(self) -> None:
        self.assertEqual(
            parse_copilot_review.extract_payload(json.dumps(VALID_PAYLOAD)),
            VALID_PAYLOAD,
        )

    def test_extracts_json_from_markdown_fence(self) -> None:
        raw = f"```json\n{json.dumps(VALID_PAYLOAD)}\n```"

        self.assertEqual(parse_copilot_review.extract_payload(raw), VALID_PAYLOAD)

    def test_extracts_json_surrounded_by_prose(self) -> None:
        raw = f"Here is the verdict:\n{json.dumps(VALID_PAYLOAD)}\nDone."

        self.assertEqual(parse_copilot_review.extract_payload(raw), VALID_PAYLOAD)

    def test_rejects_payload_with_missing_required_key(self) -> None:
        payload = dict(VALID_PAYLOAD)
        del payload["reason"]

        with self.assertRaises(ValueError):
            parse_copilot_review.extract_payload(json.dumps(payload))

    def test_rejects_non_boolean_approved_value(self) -> None:
        payload = dict(VALID_PAYLOAD)
        payload["approved"] = "true"

        with self.assertRaises(ValueError):
            parse_copilot_review.extract_payload(json.dumps(payload))


class MainTests(unittest.TestCase):
    def test_invalid_output_writes_fallback_and_requests_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "copilot-review.json"
            output_path = Path(directory) / "github-output"
            review_path.write_text("", encoding="utf-8")

            with (
                mock.patch.object(parse_copilot_review, "REVIEW_PATH", review_path),
                mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_path)}),
            ):
                exit_code = parse_copilot_review.main()

            self.assertEqual(exit_code, 1)
            fallback = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertFalse(fallback["approved"])
            self.assertIn("empty", fallback["reason"].lower())
            self.assertEqual(output_path.read_text(encoding="utf-8"), "approved=false\n")

    def test_valid_fenced_output_is_normalized_and_approved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "copilot-review.json"
            output_path = Path(directory) / "github-output"
            review_path.write_text(
                f"```json\n{json.dumps(VALID_PAYLOAD)}\n```\n",
                encoding="utf-8",
            )

            with (
                mock.patch.object(parse_copilot_review, "REVIEW_PATH", review_path),
                mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_path)}),
            ):
                exit_code = parse_copilot_review.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                json.loads(review_path.read_text(encoding="utf-8")),
                VALID_PAYLOAD,
            )
            self.assertEqual(output_path.read_text(encoding="utf-8"), "approved=true\n")


if __name__ == "__main__":
    unittest.main()
