from unittest.mock import MagicMock, patch

from ai_pr_reviewer.reviewer import MARKER, run_review


@patch("ai_pr_reviewer.reviewer.review_diff")
@patch("ai_pr_reviewer.reviewer.GitHubClient")
def test_run_review_posts_comment(mock_gh_cls, mock_review):
    mock_gh = MagicMock()
    mock_gh.get_pr_diff.return_value = "diff --git a/x.py b/x.py\n+pass\n"
    mock_gh_cls.return_value = mock_gh
    mock_review.return_value = "## Summary\nfine"

    body = run_review(
        github_token="t",
        anthropic_api_key="k",
        repo="octocat/hello-world",
        pr_number=7,
    )

    assert MARKER in body
    assert "fine" in body
    mock_gh.post_comment.assert_called_once()
    posted_pr, posted_body = mock_gh.post_comment.call_args[0]
    assert posted_pr == 7
    assert body == posted_body


@patch("ai_pr_reviewer.reviewer.GitHubClient")
def test_run_review_skips_empty_diff(mock_gh_cls):
    mock_gh = MagicMock()
    mock_gh.get_pr_diff.return_value = "   "
    mock_gh_cls.return_value = mock_gh

    body = run_review(
        github_token="t",
        anthropic_api_key="k",
        repo="octocat/hello-world",
        pr_number=7,
    )

    assert "empty PR" in body
    mock_gh.post_comment.assert_called_once()
