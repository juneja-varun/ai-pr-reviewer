"""Orchestrates fetching a PR diff, reviewing it, and posting/updating the result."""
from __future__ import annotations

from .diff_batching import select_and_batch
from .diff_filter import commentable_lines
from .formatting import (
    FINDING_MARKER,
    SUMMARY_MARKER,
    Finding,
    meets_threshold,
    render_empty_diff_body,
    render_inline_comment_body,
    render_no_issues_body,
    render_summary_body,
)
from .github_client import GitHubClient
from .llm_client import review_diff


def run_review(
    *,
    github_token: str,
    anthropic_api_key: str,
    repo: str,
    pr_number: int,
    model: str = "claude-sonnet-5",
    min_severity: str = "MEDIUM",
) -> str:
    gh = GitHubClient(token=github_token, repo=repo)
    files = gh.get_pr_files(pr_number)

    diff_files = [f for f in files if f.get("patch")]
    if not diff_files:
        body = render_empty_diff_body()
        _upsert_summary_comment(gh, pr_number, body)
        return body

    batches, skipped_files = select_and_batch(diff_files)
    if not batches and not skipped_files:
        # every file was excluded (lockfiles/generated only) - same "nothing
        # to review" outcome as an empty diff, from the caller's perspective.
        body = render_empty_diff_body()
        _upsert_summary_comment(gh, pr_number, body)
        return body

    all_findings: list[Finding] = []
    for batch in batches:
        all_findings.extend(review_diff(batch.diff_text, api_key=anthropic_api_key, model=model))

    shown_findings = [f for f in all_findings if meets_threshold(f.severity, min_severity)]

    commentable_by_file = {f["filename"]: commentable_lines(f["patch"]) for f in diff_files}
    inline_findings, unanchored_findings = _split_anchorable(shown_findings, commentable_by_file)

    reviewed_files = [name for batch in batches for name in batch.filenames]

    if not shown_findings:
        body = render_no_issues_body(min_severity)
    else:
        body = render_summary_body(
            reviewed_files=reviewed_files,
            skipped_files=skipped_files,
            all_findings=all_findings,
            shown_findings=shown_findings,
            unanchored_findings=unanchored_findings,
            min_severity=min_severity,
        )
    _upsert_summary_comment(gh, pr_number, body)

    if inline_findings:
        _replace_inline_comments(gh, pr_number, inline_findings)

    return body


def _split_anchorable(
    findings: list[Finding], commentable_by_file: dict[str, set[int]]
) -> tuple[list[Finding], list[Finding]]:
    inline, unanchored = [], []
    for finding in findings:
        if finding.line in commentable_by_file.get(finding.file, set()):
            inline.append(finding)
        else:
            unanchored.append(finding)
    return inline, unanchored


def _upsert_summary_comment(gh: GitHubClient, pr_number: int, body: str) -> None:
    for comment in gh.list_issue_comments(pr_number):
        if SUMMARY_MARKER in comment["body"]:
            gh.update_comment(comment["id"], body)
            return
    gh.post_comment(pr_number, body)


def _replace_inline_comments(gh: GitHubClient, pr_number: int, findings: list[Finding]) -> None:
    # Snapshot the comments that existed *before* this run, so the cleanup
    # pass below can never touch what we're about to create - create_review's
    # response doesn't hand back the new comments' ids, so "existed before"
    # is the only reliable way to tell old from new once they're both fetched
    # from the same list-comments call afterward.
    pre_existing_ids = {c["id"] for c in gh.list_review_comments(pr_number)}

    comments_payload = []
    for finding in findings:
        comment: dict = {
            "path": finding.file,
            "line": finding.end_line or finding.line,
            "side": "RIGHT",
            "body": render_inline_comment_body(finding),
        }
        if finding.end_line:
            comment["start_line"] = finding.line
            comment["start_side"] = "RIGHT"
        comments_payload.append(comment)

    # Create the new review FIRST. If this raises (e.g. a bad file/line pair),
    # nothing below has run yet, so no prior comments have been touched - a
    # failed review leaves the previous one in place instead of leaving the
    # PR with no comments at all until the next push.
    gh.create_review(
        pr_number,
        event="COMMENT",
        body="🤖 AI Review — see inline comments below.",
        comments=comments_payload,
    )

    after = gh.list_review_comments(pr_number)
    replied_to = {c["in_reply_to_id"] for c in after if c.get("in_reply_to_id")}
    for comment in after:
        is_from_a_prior_run = comment["id"] in pre_existing_ids
        is_ours = FINDING_MARKER in comment.get("body", "")
        has_reply = comment["id"] in replied_to
        if is_from_a_prior_run and is_ours and not has_reply:
            gh.delete_review_comment(comment["id"])
