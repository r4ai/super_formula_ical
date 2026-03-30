#!/usr/bin/env python3
import json
import os
from pathlib import Path


REVIEW_PATH = Path("copilot-review.json")
FALLBACK_PAYLOAD = {
    "approved": False,
    "summary": "Copilot CLI returned invalid JSON.",
    "reason": "Failed to parse Copilot CLI output.",
    "issue_title": "Automatic SUPER FORMULA ICS update needs review",
    "issue_body": "Copilot CLI did not return valid JSON, so the automatic ICS update was blocked.",
}


def main() -> int:
    raw = REVIEW_PATH.read_text(encoding="utf-8").strip()

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        payload = dict(FALLBACK_PAYLOAD)
        payload["reason"] = f"{FALLBACK_PAYLOAD['reason']} {exc}"
        REVIEW_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    approved = "true" if payload.get("approved") else "false"
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        fh.write(f"approved={approved}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
