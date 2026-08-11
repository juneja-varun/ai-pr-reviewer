"""Thin wrapper around the Anthropic Messages API."""
from __future__ import annotations

import requests

API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

SYSTEM_PROMPT = """You are a senior software engineer reviewing a pull request diff.

Review for: correctness bugs, security issues, obvious performance problems,
and missing test coverage. Ignore pure style nits a linter would already catch.

Respond in this exact markdown structure:

## Summary
One or two sentences on what the change does.

## Findings
A bullet list of concrete issues, each with a one-line "why it matters".
If there are no issues, write "No blocking issues found."

Keep the whole response under 400 words. Do not invent line numbers you
cannot see in the diff.
"""


class LLMReviewError(RuntimeError):
    pass


def review_diff(diff: str, api_key: str, model: str, max_diff_chars: int = 60_000) -> str:
    if len(diff) > max_diff_chars:
        diff = diff[:max_diff_chars] + "\n\n[diff truncated for length]"

    payload = {
        "model": model,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": f"Review this pull request diff:\n\n```diff\n{diff}\n```"}
        ],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    resp = requests.post(API_URL, json=payload, headers=headers, timeout=60)
    if resp.status_code != 200:
        raise LLMReviewError(f"Anthropic API error {resp.status_code}: {resp.text}")

    data = resp.json()
    blocks = data.get("content", [])
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    if not text:
        raise LLMReviewError(f"Unexpected Anthropic response shape: {data}")
    return text
