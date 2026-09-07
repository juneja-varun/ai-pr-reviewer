from unittest.mock import patch

import pytest
import responses

from ai_pr_reviewer.formatting import Finding
from ai_pr_reviewer.llm_client import LLMReviewError, review_diff


def _tool_use_response(findings: list[dict]):
    return {
        "id": "msg_01abc",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_01xyz",
                "name": "report_findings",
                "input": {"findings": findings},
            }
        ],
        "stop_reason": "tool_use",
    }


@responses.activate
def test_review_diff_parses_tool_use_findings():
    responses.add(
        responses.POST,
        "https://api.anthropic.com/v1/messages",
        json=_tool_use_response(
            [
                {
                    "file": "a.py",
                    "line": 10,
                    "severity": "HIGH",
                    "category": "correctness",
                    "summary": "off by one",
                },
                {
                    "file": "b.py",
                    "line": 20,
                    "severity": "LOW",
                    "category": "test_coverage",
                    "summary": "no test",
                },
            ]
        ),
        status=200,
    )
    result = review_diff("diff --git a/a.py b/a.py", api_key="fake", model="claude-sonnet-5")
    assert result == [
        Finding(file="a.py", line=10, severity="HIGH", category="correctness", summary="off by one"),
        Finding(file="b.py", line=20, severity="LOW", category="test_coverage", summary="no test"),
    ]


@responses.activate
def test_review_diff_sends_forced_tool_choice_and_schema():
    captured = {}

    def callback(request):
        import json

        captured["body"] = json.loads(request.body)
        return (200, {}, __import__("json").dumps(_tool_use_response([])))

    responses.add_callback(responses.POST, "https://api.anthropic.com/v1/messages", callback=callback)
    review_diff("diff", api_key="fake", model="claude-sonnet-5")

    body = captured["body"]
    assert body["tools"][0]["name"] == "report_findings"
    assert body["tools"][0]["strict"] is True
    assert body["tools"][0]["input_schema"]["additionalProperties"] is False
    assert body["tool_choice"] == {"type": "tool", "name": "report_findings"}


@responses.activate
def test_review_diff_raises_on_api_error():
    responses.add(
        responses.POST,
        "https://api.anthropic.com/v1/messages",
        json={"error": "bad request"},
        status=400,
    )
    with pytest.raises(LLMReviewError):
        review_diff("diff", api_key="fake", model="claude-sonnet-5")


@responses.activate
def test_review_diff_raises_when_no_tool_use_block_present():
    # e.g. a user overrides `model` to something that ignores the forced tool.
    responses.add(
        responses.POST,
        "https://api.anthropic.com/v1/messages",
        json={"content": [{"type": "text", "text": "I reviewed it, looks fine."}]},
        status=200,
    )
    with pytest.raises(LLMReviewError, match="No report_findings tool_use block"):
        review_diff("diff", api_key="fake", model="claude-sonnet-5")


@responses.activate
def test_review_diff_drops_a_malformed_finding_but_keeps_the_rest(capsys):
    responses.add(
        responses.POST,
        "https://api.anthropic.com/v1/messages",
        json=_tool_use_response(
            [
                {"file": "a.py", "line": 1, "category": "correctness", "summary": "missing severity key"},
                {
                    "file": "b.py",
                    "line": 2,
                    "severity": "HIGH",
                    "category": "correctness",
                    "summary": "well formed",
                },
            ]
        ),
        status=200,
    )
    result = review_diff("diff", api_key="fake", model="claude-sonnet-5")
    assert len(result) == 1
    assert result[0].file == "b.py"
    assert "dropping malformed finding" in capsys.readouterr().out


@responses.activate
@patch("ai_pr_reviewer.llm_client.time.sleep")
def test_review_diff_retries_on_5xx_then_succeeds(mock_sleep):
    responses.add(responses.POST, "https://api.anthropic.com/v1/messages", status=503)
    responses.add(responses.POST, "https://api.anthropic.com/v1/messages", status=503)
    responses.add(
        responses.POST,
        "https://api.anthropic.com/v1/messages",
        json=_tool_use_response(
            [{"file": "a.py", "line": 1, "severity": "LOW", "category": "correctness", "summary": "ok"}]
        ),
        status=200,
    )
    result = review_diff("diff", api_key="fake", model="claude-sonnet-5", max_retries=3)
    assert len(result) == 1
    assert len(responses.calls) == 3
    assert mock_sleep.call_count == 2
