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


def main() -> int:
    if REVIEW_FILE.exists():
        payload = json.loads(REVIEW_FILE.read_text(encoding="utf-8"))
    else:
        payload = FALLBACK_PAYLOAD

    body = "\n\n".join(
        [
            payload.get("issue_body", "The automatic ICS update was blocked."),
            f"Workflow run: https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
            "Copilot review summary:",
            payload.get("summary", ""),
            "Copilot review reason:",
            payload.get("reason", ""),
        ]
    ).strip()

    TITLE_FILE.write_text(
        payload.get("issue_title", "Automatic SUPER FORMULA ICS update needs review"),
        encoding="utf-8",
    )
    BODY_FILE.write_text(body + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
