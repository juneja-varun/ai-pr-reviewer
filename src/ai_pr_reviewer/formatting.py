"""Renders PR comment/review-comment bodies from structured review results.

Pure functions - no HTTP, no LLM calls - kept separate from reviewer.py's
orchestration so the rendering logic is testable without mocking anything.
"""
from __future__ import annotations

from dataclasses import dataclass

SUMMARY_MARKER = "<!-- ai-pr-reviewer:summary -->"
FINDING_MARKER = "<!-- ai-pr-reviewer:finding -->"

SEVERITY_ORDER = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


@dataclass
class Finding:
    file: str
    line: int
    severity: str
    category: str
    summary: str
    end_line: int | None = None


def meets_threshold(severity: str, min_severity: str) -> bool:
    return SEVERITY_ORDER.index(severity) >= SEVERITY_ORDER.index(min_severity)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def render_empty_diff_body() -> str:
    return (
        f"{SUMMARY_MARKER}\n### 🤖 AI Review\n\n"
        "Nothing to review — the PR is empty, or only touches "
        "generated files (lockfiles, build output, etc)."
    )


def render_no_issues_body(min_severity: str) -> str:
    return (
        f"{SUMMARY_MARKER}\n### 🤖 AI Review\n\n"
        f"No issues at or above **{min_severity}** severity found."
    )


def render_summary_body(
    *,
    reviewed_files: list[str],
    skipped_files: list[str],
    all_findings: list[Finding],
    shown_findings: list[Finding],
    unanchored_findings: list[Finding],
    min_severity: str,
) -> str:
    lines = [SUMMARY_MARKER, "### 🤖 AI Review", ""]

    file_summary = f"Reviewed {_plural(len(reviewed_files), 'file')}"
    if skipped_files:
        file_summary += f" ({_plural(len(skipped_files), 'file')} skipped as too large to review)"
    lines.append(file_summary + ".")

    by_severity: dict[str, int] = {}
    for f in all_findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

    if shown_findings:
        breakdown = ", ".join(
            f"{by_severity.get(sev, 0)} {sev}"
            for sev in reversed(SEVERITY_ORDER)
            if by_severity.get(sev, 0) and meets_threshold(sev, min_severity)
        )
        lines.append(f"**{_plural(len(shown_findings), 'finding')} at or above {min_severity}**: {breakdown}.")

    suppressed = [f for f in all_findings if not meets_threshold(f.severity, min_severity)]
    if suppressed:
        lines.append(f"{_plural(len(suppressed), 'finding')} below {min_severity} severity suppressed.")

    if unanchored_findings:
        lines.append("")
        lines.append("Findings that couldn't be anchored to a specific diff line:")
        for f in unanchored_findings:
            lines.append(f"- **[{f.severity}] {f.category}** `{f.file}` — {f.summary}")

    if skipped_files:
        lines.append("")
        lines.append("Not reviewed (diff too large for this batch):")
        for name in skipped_files:
            lines.append(f"- `{name}`")

    return "\n".join(lines)


def render_inline_comment_body(finding: Finding) -> str:
    return f"**[{finding.severity}] {finding.category}** — {finding.summary}\n\n{FINDING_MARKER}"
