"""Thin wrapper around the Anthropic Messages API.

Uses a forced tool call (not freeform text) so review findings come back as
a typed list - {file, line, severity, category, summary} - instead of a
paragraph the caller has no reliable way to parse or anchor to a diff line.
"""
from __future__ import annotations

import time

import requests

from .formatting import SEVERITY_ORDER, Finding

API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
TOOL_NAME = "report_findings"
CATEGORIES = ("correctness", "security", "performance", "test_coverage")

SYSTEM_PROMPT = """You are a senior software engineer reviewing a pull request diff.

Review for: correctness bugs, security issues, obvious performance problems,
and missing test coverage. Ignore pure style nits a linter would already catch.

Report findings by calling the report_findings tool. For each finding:
- `line` must be a line number that actually appears in the diff you were
  given, counted in the NEW version of the file (the same numbering GitHub
  shows on the right-hand side of a diff). Do not invent a line number you
  cannot see.
- `severity` reflects real-world impact, not style preference.
- If you find nothing worth flagging, call the tool with an empty findings list.
"""

FINDINGS_TOOL = {
    "name": TOOL_NAME,
    "description": "Report the findings from reviewing a pull request diff.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {
                            "type": "string",
                            "description": "File path exactly as it appears in the diff",
                        },
                        "line": {
                            "type": "integer",
                            "description": "Line number in the new version of the file",
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "End of a multi-line range this finding covers, if any",
                        },
                        "severity": {"type": "string", "enum": list(SEVERITY_ORDER)},
                        "category": {"type": "string", "enum": list(CATEGORIES)},
                        "summary": {
                            "type": "string",
                            "description": "One or two sentences: what's wrong and why it matters",
                        },
                    },
                    "required": ["file", "line", "severity", "category", "summary"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["findings"],
        "additionalProperties": False,
    },
    "strict": True,
}


class LLMReviewError(RuntimeError):
    pass


def _post_with_retries(payload: dict, headers: dict, max_retries: int) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        except requests.RequestException as exc:
            last_exc = exc
        else:
            if resp.status_code not in (429, 500, 502, 503, 504):
                return resp
            last_exc = LLMReviewError(f"Anthropic API error {resp.status_code}: {resp.text}")
        if attempt < max_retries - 1:
            time.sleep(2**attempt)
    raise LLMReviewError(f"Anthropic API request failed after {max_retries} attempts: {last_exc}")


def review_diff(diff: str, api_key: str, model: str, max_retries: int = 3) -> list[Finding]:
    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "tools": [FINDINGS_TOOL],
        "tool_choice": {"type": "tool", "name": TOOL_NAME},
        "messages": [
            {"role": "user", "content": f"Review this pull request diff:\n\n```diff\n{diff}\n```"}
        ],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    resp = _post_with_retries(payload, headers, max_retries)
    if resp.status_code != 200:
        raise LLMReviewError(f"Anthropic API error {resp.status_code}: {resp.text}")

    data = resp.json()
    tool_use = next(
        (b for b in data.get("content", []) if b.get("type") == "tool_use" and b.get("name") == TOOL_NAME),
        None,
    )
    if tool_use is None:
        raise LLMReviewError(f"No {TOOL_NAME} tool_use block in Anthropic response: {data}")

    raw_findings = tool_use.get("input", {}).get("findings", [])
    findings: list[Finding] = []
    for raw in raw_findings:
        try:
            findings.append(
                Finding(
                    file=raw["file"],
                    line=raw["line"],
                    severity=raw["severity"],
                    category=raw["category"],
                    summary=raw["summary"],
                    end_line=raw.get("end_line"),
                )
            )
        except KeyError as exc:
            print(f"ai_pr_reviewer: dropping malformed finding (missing {exc}): {raw}")
    return findings
