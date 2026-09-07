from unittest.mock import MagicMock, patch

from ai_pr_reviewer.formatting import FINDING_MARKER, SUMMARY_MARKER, Finding
from ai_pr_reviewer.reviewer import run_review

# A file whose patch adds a line at new-file line 1 - commentable_lines()
# (the real, unmocked function) will say line 1 is a valid inline-comment
# target for this file.
SIMPLE_FILE = {"filename": "x.py", "patch": "@@ -0,0 +1 @@\n+pass"}


def _make_mock_gh(files, issue_comments=None, review_comments=None):
    mock_gh = MagicMock()
    mock_gh.get_pr_files.return_value = files
    mock_gh.list_issue_comments.return_value = issue_comments or []
    mock_gh.list_review_comments.return_value = review_comments or []
    return mock_gh


@patch("ai_pr_reviewer.reviewer.review_diff")
@patch("ai_pr_reviewer.reviewer.GitHubClient")
def test_run_review_posts_new_summary_when_none_exists(mock_gh_cls, mock_review):
    mock_gh = _make_mock_gh([SIMPLE_FILE])
    mock_gh_cls.return_value = mock_gh
    mock_review.return_value = []

    body = run_review(github_token="t", anthropic_api_key="k", repo="octocat/hello-world", pr_number=7)

    assert SUMMARY_MARKER in body
    mock_gh.post_comment.assert_called_once()
    mock_gh.update_comment.assert_not_called()


@patch("ai_pr_reviewer.reviewer.review_diff")
@patch("ai_pr_reviewer.reviewer.GitHubClient")
def test_run_review_updates_existing_summary_comment_instead_of_duplicating(mock_gh_cls, mock_review):
    # Load-bearing regression test for the dead MARKER bug: a prior summary
    # comment already exists, tagged with the marker - the new run must find
    # and PATCH it, never POST a second one.
    existing_summary = {"id": 111, "body": f"{SUMMARY_MARKER}\nold review"}
    mock_gh = _make_mock_gh([SIMPLE_FILE], issue_comments=[existing_summary])
    mock_gh_cls.return_value = mock_gh
    mock_review.return_value = []

    run_review(github_token="t", anthropic_api_key="k", repo="octocat/hello-world", pr_number=7)

    mock_gh.post_comment.assert_not_called()
    mock_gh.update_comment.assert_called_once()
    updated_id, _ = mock_gh.update_comment.call_args[0]
    assert updated_id == 111


@patch("ai_pr_reviewer.reviewer.review_diff")
@patch("ai_pr_reviewer.reviewer.GitHubClient")
def test_run_review_posts_inline_comments_for_anchorable_findings(mock_gh_cls, mock_review):
    mock_gh = _make_mock_gh([SIMPLE_FILE])
    mock_gh_cls.return_value = mock_gh
    mock_review.return_value = [
        Finding(file="x.py", line=1, severity="HIGH", category="correctness", summary="bug"),
    ]

    run_review(github_token="t", anthropic_api_key="k", repo="octocat/hello-world", pr_number=7)

    mock_gh.create_review.assert_called_once()
    _, kwargs = mock_gh.create_review.call_args
    assert kwargs["comments"] == [
        {"path": "x.py", "line": 1, "side": "RIGHT", "body": mock_gh.create_review.call_args[1]["comments"][0]["body"]}
    ]
    assert FINDING_MARKER in kwargs["comments"][0]["body"]


@patch("ai_pr_reviewer.reviewer.review_diff")
@patch("ai_pr_reviewer.reviewer.GitHubClient")
def test_run_review_falls_back_unanchored_findings_to_summary(mock_gh_cls, mock_review):
    mock_gh = _make_mock_gh([SIMPLE_FILE])
    mock_gh_cls.return_value = mock_gh
    # line 999 is nowhere in SIMPLE_FILE's one-line patch - can't be anchored.
    mock_review.return_value = [
        Finding(file="x.py", line=999, severity="HIGH", category="correctness", summary="drifted"),
    ]

    body = run_review(github_token="t", anthropic_api_key="k", repo="octocat/hello-world", pr_number=7)

    mock_gh.create_review.assert_not_called()
    assert "drifted" in body
    assert "couldn't be anchored" in body


@patch("ai_pr_reviewer.reviewer.review_diff")
@patch("ai_pr_reviewer.reviewer.GitHubClient")
def test_run_review_filters_findings_below_min_severity(mock_gh_cls, mock_review):
    mock_gh = _make_mock_gh([SIMPLE_FILE])
    mock_gh_cls.return_value = mock_gh
    mock_review.return_value = [
        Finding(file="x.py", line=1, severity="LOW", category="test_coverage", summary="nit"),
        Finding(file="x.py", line=1, severity="HIGH", category="correctness", summary="real bug"),
    ]

    body = run_review(
        github_token="t", anthropic_api_key="k", repo="octocat/hello-world", pr_number=7, min_severity="MEDIUM"
    )

    assert "1 finding at or above MEDIUM" in body
    assert "1 finding below MEDIUM severity suppressed" in body
    mock_gh.create_review.assert_called_once()
    assert len(mock_gh.create_review.call_args[1]["comments"]) == 1


@patch("ai_pr_reviewer.reviewer.review_diff")
@patch("ai_pr_reviewer.reviewer.GitHubClient")
def test_run_review_posts_no_issues_body_when_nothing_meets_threshold(mock_gh_cls, mock_review):
    mock_gh = _make_mock_gh([SIMPLE_FILE])
    mock_gh_cls.return_value = mock_gh
    mock_review.return_value = [
        Finding(file="x.py", line=1, severity="LOW", category="test_coverage", summary="nit"),
    ]

    body = run_review(github_token="t", anthropic_api_key="k", repo="octocat/hello-world", pr_number=7)

    assert "No issues at or above" in body
    mock_gh.create_review.assert_not_called()


@patch("ai_pr_reviewer.reviewer.review_diff")
@patch("ai_pr_reviewer.reviewer.GitHubClient")
def test_run_review_deletes_stale_bot_comments_without_replies_but_keeps_ones_with_replies(
    mock_gh_cls, mock_review
):
    # Load-bearing regression test: three review comments already exist -
    # one of ours with no reply (must be deleted), one of ours with a reply
    # (must survive), one from a human (never touched regardless).
    unreplied_bot_comment = {"id": 1, "body": f"old finding\n\n{FINDING_MARKER}"}
    replied_bot_comment = {"id": 2, "body": f"old finding\n\n{FINDING_MARKER}"}
    reply_to_it = {"id": 3, "body": "thanks, will fix", "in_reply_to_id": 2}
    human_comment = {"id": 4, "body": "looks fine to me"}

    mock_gh = _make_mock_gh(
        [SIMPLE_FILE],
        review_comments=[unreplied_bot_comment, replied_bot_comment, reply_to_it, human_comment],
    )
    mock_gh_cls.return_value = mock_gh
    mock_review.return_value = [
        Finding(file="x.py", line=1, severity="HIGH", category="correctness", summary="new finding"),
    ]

    run_review(github_token="t", anthropic_api_key="k", repo="octocat/hello-world", pr_number=7)

    mock_gh.create_review.assert_called_once()
    deleted_ids = [call.args[0] for call in mock_gh.delete_review_comment.call_args_list]
    assert deleted_ids == [1]


@patch("ai_pr_reviewer.reviewer.GitHubClient")
def test_run_review_skips_empty_diff(mock_gh_cls):
    mock_gh = _make_mock_gh([])
    mock_gh_cls.return_value = mock_gh

    body = run_review(github_token="t", anthropic_api_key="k", repo="octocat/hello-world", pr_number=7)

    assert "Nothing to review" in body
    mock_gh.post_comment.assert_called_once()


@patch("ai_pr_reviewer.reviewer.GitHubClient")
def test_run_review_skips_when_only_lockfiles_changed(mock_gh_cls):
    mock_gh = _make_mock_gh(
        [{"filename": "package-lock.json", "patch": "@@ -1,2 +1,2 @@\n-a\n+b"}]
    )
    mock_gh_cls.return_value = mock_gh

    body = run_review(github_token="t", anthropic_api_key="k", repo="octocat/hello-world", pr_number=7)

    assert "Nothing to review" in body
    mock_gh.post_comment.assert_called_once()
