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


@responses.activate
def test_get_pr_files_follows_pagination_link_header():
    # Link header shape verified against a real GitHub response (curl -I on a
    # real paginated endpoint), not invented: comma-separated `<url>; rel="x"`.
    page1_url = "https://api.github.com/repos/octocat/hello-world/pulls/42/files"
    page2_url = "https://api.github.com/repositories/1/pulls/42/files?per_page=100&page=2"
    responses.add(
        responses.GET,
        page1_url,
        json=[{"filename": "a.py"}],
        status=200,
        headers={"Link": f'<{page2_url}>; rel="next"'},
    )
    responses.add(
        responses.GET,
        page2_url,
        json=[{"filename": "b.py"}],
        status=200,
    )
    client = GitHubClient(token="fake-token", repo="octocat/hello-world")
    files = client.get_pr_files(42)
    assert [f["filename"] for f in files] == ["a.py", "b.py"]


@responses.activate
def test_list_issue_comments():
    responses.add(
        responses.GET,
        "https://api.github.com/repos/octocat/hello-world/issues/42/comments",
        json=[{"id": 1, "body": "hi"}],
        status=200,
    )
    client = GitHubClient(token="fake-token", repo="octocat/hello-world")
    assert client.list_issue_comments(42) == [{"id": 1, "body": "hi"}]


@responses.activate
def test_update_comment():
    responses.add(
        responses.PATCH,
        "https://api.github.com/repos/octocat/hello-world/issues/comments/99",
        json={"id": 99, "body": "updated"},
        status=200,
    )
    client = GitHubClient(token="fake-token", repo="octocat/hello-world")
    result = client.update_comment(99, "updated")
    assert result["body"] == "updated"
    assert responses.calls[0].request.body == b'{"body": "updated"}'


@responses.activate
def test_list_review_comments():
    responses.add(
        responses.GET,
        "https://api.github.com/repos/octocat/hello-world/pulls/42/comments",
        json=[{"id": 5, "path": "a.py", "line": 10}],
        status=200,
    )
    client = GitHubClient(token="fake-token", repo="octocat/hello-world")
    assert client.list_review_comments(42) == [{"id": 5, "path": "a.py", "line": 10}]


@responses.activate
def test_delete_review_comment():
    responses.add(
        responses.DELETE,
        "https://api.github.com/repos/octocat/hello-world/pulls/comments/5",
        status=204,
    )
    client = GitHubClient(token="fake-token", repo="octocat/hello-world")
    client.delete_review_comment(5)  # no return value, just shouldn't raise


@responses.activate
def test_create_review():
    captured = {}

    def callback(request):
        import json

        captured["body"] = json.loads(request.body)
        return (200, {}, json.dumps({"id": 1, "state": "COMMENTED"}))

    responses.add_callback(
        responses.POST,
        "https://api.github.com/repos/octocat/hello-world/pulls/42/reviews",
        callback=callback,
    )
    client = GitHubClient(token="fake-token", repo="octocat/hello-world")
    comments = [{"path": "a.py", "line": 1, "side": "RIGHT", "body": "issue here"}]
    result = client.create_review(42, event="COMMENT", body="review body", comments=comments)

    assert result["state"] == "COMMENTED"
    assert captured["body"] == {"event": "COMMENT", "body": "review body", "comments": comments}


@responses.activate
def test_create_review_raises_on_422():
    responses.add(
        responses.POST,
        "https://api.github.com/repos/octocat/hello-world/pulls/42/reviews",
        status=422,
    )
    client = GitHubClient(token="fake-token", repo="octocat/hello-world")
    with pytest.raises(requests.HTTPError):
        client.create_review(42, event="COMMENT", body="x", comments=[])
