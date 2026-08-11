import pytest
import responses

from ai_pr_reviewer.llm_client import LLMReviewError, review_diff


@responses.activate
def test_review_diff_returns_text():
    responses.add(
        responses.POST,
        "https://api.anthropic.com/v1/messages",
        json={"content": [{"type": "text", "text": "## Summary\nLooks fine."}]},
        status=200,
    )
    result = review_diff("diff --git a/x.py b/x.py", api_key="fake", model="claude-sonnet-5")
    assert "Looks fine" in result


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
def test_review_diff_truncates_large_diffs():
    captured = {}

    def callback(request):
        import json

        captured["body"] = json.loads(request.body)
        return (200, {}, '{"content": [{"type": "text", "text": "ok"}]}')

    responses.add_callback(
        responses.POST, "https://api.anthropic.com/v1/messages", callback=callback
    )
    huge_diff = "x" * 100_000
    review_diff(huge_diff, api_key="fake", model="claude-sonnet-5", max_diff_chars=100)
    sent_content = captured["body"]["messages"][0]["content"]
    assert "[diff truncated for length]" in sent_content
