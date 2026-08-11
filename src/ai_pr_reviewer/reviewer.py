"""Orchestrates fetching a PR diff, reviewing it, and posting the result."""
from __future__ import annotations

from .diff_filter import build_filtered_diff
from .github_client import GitHubClient
from .llm_client import review_diff

MARKER = "<!-- ai-pr-reviewer -->"


def run_review(
    *,
    github_token: str,
    anthropic_api_key: str,
    repo: str,
    pr_number: int,
    model: str = "claude-sonnet-5",
) -> str:
    gh = GitHubClient(token=github_token, repo=repo)
    files = gh.get_pr_files(pr_number)
    diff = build_filtered_diff(files)

    if not diff.strip():
        body = (
            f"{MARKER}\n### 🤖 AI Review\n\n"
            "Nothing to review — the PR is empty, or only touches "
            "generated files (lockfiles, build output, etc)."
        )
        gh.post_comment(pr_number, body)
        return body

    review_text = review_diff(diff, api_key=anthropic_api_key, model=model)
    body = f"{MARKER}\n### 🤖 AI Review\n\n{review_text}"
    gh.post_comment(pr_number, body)
    return body
