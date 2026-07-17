#!/usr/bin/env python3
import json
import os
from pathlib import Path
from typing import Any


REVIEW_PATH = Path("copilot-review.json")
FALLBACK_PAYLOAD = {
    "approved": False,
    "summary": "Copilot CLI returned invalid JSON.",
    "reason": "Failed to parse Copilot CLI output.",
    "issue_title": "Automatic SUPER FORMULA ICS update needs review",
    "issue_body": "Copilot CLI did not return valid JSON, so the automatic ICS update was blocked.",
}
REQUIRED_STRING_KEYS = ("summary", "reason", "issue_title", "issue_body")


def validate_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("review payload must be a JSON object")
    if type(payload.get("approved")) is not bool:
        raise ValueError("'approved' must be a boolean")
    for key in REQUIRED_STRING_KEYS:
        if not isinstance(payload.get(key), str):
            raise ValueError(f"'{key}' must be a string")
    return payload


def extract_payload(raw: str) -> dict[str, Any]:
    if not raw.strip():
        raise ValueError("Copilot CLI output was empty")

    decoder = json.JSONDecoder()
    errors: list[Exception] = []
    for index, character in enumerate(raw):
        if character != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(raw, index)
            return validate_payload(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(exc)

    if errors:
        raise ValueError(f"no valid review object found: {errors[-1]}")
    raise ValueError("Copilot CLI output did not contain a JSON object")


def main() -> int:
    raw = REVIEW_PATH.read_text(encoding="utf-8").strip()

    try:
        payload = extract_payload(raw)
        exit_code = 0
    except ValueError as exc:
        payload = dict(FALLBACK_PAYLOAD)
        payload["reason"] = f"{FALLBACK_PAYLOAD['reason']} {exc}"
        exit_code = 1

    REVIEW_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    approved = "true" if payload.get("approved") else "false"
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        fh.write(f"approved={approved}\n")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
