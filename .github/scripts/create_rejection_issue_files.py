#!/usr/bin/env python3
import json
import os
from pathlib import Path


REVIEW_FILE = Path("copilot-review.json")
TITLE_FILE = Path("issue-title.txt")
BODY_FILE = Path("issue-body.md")
FALLBACK_PAYLOAD = {
    "issue_title": "Automatic SUPER FORMULA ICS update failed review",
    "issue_body": "Copilot CLI did not complete successfully, so the automatic ICS update was blocked.",
    "summary": "Copilot CLI execution failed.",
    "reason": "The review step failed before a verdict was produced.",
}


def load_payload() -> dict[str, str]:
    if not REVIEW_FILE.exists():
        return FALLBACK_PAYLOAD

    payload = json.loads(REVIEW_FILE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or any(
        not isinstance(payload.get(key), str) or not payload[key].strip()
        for key in FALLBACK_PAYLOAD
    ):
        raise ValueError("review payload must contain non-empty issue details")
    return {key: payload[key] for key in FALLBACK_PAYLOAD}


def main() -> int:
    payload = load_payload()

    body = "\n\n".join(
        [
            payload["issue_body"],
            f"Workflow run: https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
            "Copilot review summary:",
            payload["summary"],
            "Copilot review reason:",
            payload["reason"],
        ]
    ).strip()

    TITLE_FILE.write_text(
        payload["issue_title"],
        encoding="utf-8",
    )
    BODY_FILE.write_text(body + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
