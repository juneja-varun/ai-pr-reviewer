"""Minimal GitHub REST client for the pieces this action needs."""
from __future__ import annotations

import requests

API_ROOT = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str, repo: str, timeout: int = 30):
        self.repo = repo
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def _get_all_pages(self, url: str, params: dict | None = None) -> list[dict]:
        """GETs url with per_page=100, following the Link header's `rel="next"`
        entry until there are no more pages. get_pr_files previously used a
        single .get() call, which silently caps at 100 items on any PR with
        more changed files than that.
        """
        results: list[dict] = []
        params = {**(params or {}), "per_page": 100}
        next_url: str | None = url
        while next_url:
            resp = self.session.get(next_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            results.extend(resp.json())
            next_url = resp.links.get("next", {}).get("url")
            params = None  # the next_url already carries its own query string
        return results

    def get_pr_diff(self, pr_number: int) -> str:
        url = f"{API_ROOT}/repos/{self.repo}/pulls/{pr_number}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
        resp = self.session.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def get_pr_files(self, pr_number: int) -> list[dict]:
        url = f"{API_ROOT}/repos/{self.repo}/pulls/{pr_number}/files"
        return self._get_all_pages(url)

    def post_comment(self, pr_number: int, body: str) -> dict:
        url = f"{API_ROOT}/repos/{self.repo}/issues/{pr_number}/comments"
        resp = self.session.post(url, json={"body": body}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def list_issue_comments(self, pr_number: int) -> list[dict]:
        url = f"{API_ROOT}/repos/{self.repo}/issues/{pr_number}/comments"
        return self._get_all_pages(url)

    def update_comment(self, comment_id: int, body: str) -> dict:
        url = f"{API_ROOT}/repos/{self.repo}/issues/comments/{comment_id}"
        resp = self.session.patch(url, json={"body": body}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def list_review_comments(self, pr_number: int) -> list[dict]:
        url = f"{API_ROOT}/repos/{self.repo}/pulls/{pr_number}/comments"
        return self._get_all_pages(url)

    def delete_review_comment(self, comment_id: int) -> None:
        url = f"{API_ROOT}/repos/{self.repo}/pulls/comments/{comment_id}"
        resp = self.session.delete(url, timeout=self.timeout)
        resp.raise_for_status()

    def create_review(self, pr_number: int, event: str, body: str, comments: list[dict]) -> dict:
        url = f"{API_ROOT}/repos/{self.repo}/pulls/{pr_number}/reviews"
        payload = {"event": event, "body": body, "comments": comments}
        resp = self.session.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()
