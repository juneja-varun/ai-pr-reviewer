from unittest.mock import patch

from ai_pr_reviewer.__main__ import main

BASE_ENV = {
    "GITHUB_TOKEN": "t",
    "ANTHROPIC_API_KEY": "k",
    "GITHUB_REPOSITORY": "octocat/hello-world",
    "PR_NUMBER": "7",
}


@patch("ai_pr_reviewer.__main__.run_review")
def test_main_defaults_min_severity_to_medium(mock_run_review):
    mock_run_review.return_value = "body"
    with patch.dict("os.environ", BASE_ENV, clear=True):
        assert main() == 0
    assert mock_run_review.call_args.kwargs["min_severity"] == "MEDIUM"


@patch("ai_pr_reviewer.__main__.run_review")
def test_main_passes_through_a_valid_min_severity(mock_run_review):
    mock_run_review.return_value = "body"
    env = {**BASE_ENV, "AI_REVIEW_MIN_SEVERITY": "high"}
    with patch.dict("os.environ", env, clear=True):
        assert main() == 0
    assert mock_run_review.call_args.kwargs["min_severity"] == "HIGH"


@patch("ai_pr_reviewer.__main__.run_review")
def test_main_rejects_an_invalid_min_severity(mock_run_review, capsys):
    env = {**BASE_ENV, "AI_REVIEW_MIN_SEVERITY": "SUPER_URGENT"}
    with patch.dict("os.environ", env, clear=True):
        assert main() == 1
    mock_run_review.assert_not_called()
    assert "AI_REVIEW_MIN_SEVERITY" in capsys.readouterr().err
