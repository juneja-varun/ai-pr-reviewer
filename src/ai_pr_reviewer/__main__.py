"""CLI entrypoint used by the GitHub Action."""
from __future__ import annotations

import json
import os
import sys

from .formatting import SEVERITY_ORDER
from .reviewer import run_review


def _pr_number_from_event() -> int:
    pr_number = os.environ.get("PR_NUMBER")
    if pr_number:
        return int(pr_number)

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        raise SystemExit("PR_NUMBER not set and no GITHUB_EVENT_PATH found")

    with open(event_path, encoding="utf-8") as f:
        event = json.load(f)

    pr = event.get("pull_request", {})
    if "number" not in pr:
        raise SystemExit("Could not determine PR number from event payload")
    return int(pr["number"])


def main() -> int:
    github_token = os.environ.get("GITHUB_TOKEN")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    repo = os.environ.get("GITHUB_REPOSITORY")
    model = os.environ.get("AI_REVIEW_MODEL", "claude-sonnet-5")
    min_severity = os.environ.get("AI_REVIEW_MIN_SEVERITY", "MEDIUM").upper()

    if min_severity not in SEVERITY_ORDER:
        print(
            f"AI_REVIEW_MIN_SEVERITY must be one of {SEVERITY_ORDER}, got {min_severity!r}",
            file=sys.stderr,
        )
        return 1

    missing = [
        name
        for name, val in [
            ("GITHUB_TOKEN", github_token),
            ("ANTHROPIC_API_KEY", anthropic_api_key),
            ("GITHUB_REPOSITORY", repo),
        ]
        if not val
    ]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        return 1

    pr_number = _pr_number_from_event()

    body = run_review(
        github_token=github_token,
        anthropic_api_key=anthropic_api_key,
        repo=repo,
        pr_number=pr_number,
        model=model,
        min_severity=min_severity,
    )
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
