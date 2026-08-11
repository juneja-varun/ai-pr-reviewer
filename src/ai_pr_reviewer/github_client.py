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

    def get_pr_diff(self, pr_number: int) -> str:
        url = f"{API_ROOT}/repos/{self.repo}/pulls/{pr_number}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
        resp = self.session.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def get_pr_files(self, pr_number: int) -> list[dict]:
        url = f"{API_ROOT}/repos/{self.repo}/pulls/{pr_number}/files"
        resp = self.session.get(url, params={"per_page": 100}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def post_comment(self, pr_number: int, body: str) -> dict:
        url = f"{API_ROOT}/repos/{self.repo}/issues/{pr_number}/comments"
        resp = self.session.post(url, json={"body": body}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()
