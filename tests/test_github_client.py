import pytest
import requests
import responses

from ai_pr_reviewer.github_client import GitHubClient


@responses.activate
def test_get_pr_diff():
    responses.add(
        responses.GET,
        "https://api.github.com/repos/octocat/hello-world/pulls/42",
        body="diff --git a/foo.py b/foo.py\n+print('hi')\n",
        status=200,
    )
    client = GitHubClient(token="fake-token", repo="octocat/hello-world")
    diff = client.get_pr_diff(42)
    assert "print('hi')" in diff


@responses.activate
def test_post_comment():
    responses.add(
        responses.POST,
        "https://api.github.com/repos/octocat/hello-world/issues/42/comments",
        json={"id": 1, "body": "hello"},
        status=201,
    )
    client = GitHubClient(token="fake-token", repo="octocat/hello-world")
    result = client.post_comment(42, "hello")
    assert result["id"] == 1


@responses.activate
def test_get_pr_diff_raises_on_error():
    responses.add(
        responses.GET,
        "https://api.github.com/repos/octocat/hello-world/pulls/42",
        status=404,
    )
    client = GitHubClient(token="fake-token", repo="octocat/hello-world")
    with pytest.raises(requests.HTTPError):
        client.get_pr_diff(42)
