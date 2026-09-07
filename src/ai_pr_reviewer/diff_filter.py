"""Excludes lockfiles and other generated files from what gets sent to the LLM.

These files are large, machine-generated, and never what a reviewer actually
wants commented on - including them just burns diff budget (see
llm_client.review_diff's truncation) and adds noise the model might latch
onto instead of the actual code change.
"""
from __future__ import annotations

import fnmatch
import posixpath
import re

EXCLUDED_PATTERNS = [
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "go.sum",
    "composer.lock",
    "*.min.js",
    "*.min.css",
    "*.generated.*",
    "*dist/*",
    "*build/*",
    "*vendor/*",
]


def is_excluded(path: str) -> bool:
    basename = posixpath.basename(path)
    return any(
        fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(basename, pattern)
        for pattern in EXCLUDED_PATTERNS
    )


_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def is_pure_deletion(patch: str) -> bool:
    """True if a patch only removes lines - nothing was added for a reviewer to comment on."""
    return not any(
        line.startswith("+") and not line.startswith("+++") for line in patch.splitlines()
    )


def commentable_lines(patch: str) -> set[int]:
    """New-file line numbers this patch touches - the only lines GitHub will accept
    an inline review comment on. Parses the `@@ -a,b +c,d @@` hunk headers and walks
    each hunk's body, tracking the new-file line counter: '+' and context lines occupy
    a new-file line and advance the counter, '-' lines don't (they only existed in the
    old file).
    """
    lines: set[int] = set()
    new_line = None
    for row in patch.splitlines():
        header = _HUNK_HEADER_RE.match(row)
        if header:
            new_line = int(header.group(1))
            continue
        if new_line is None:
            continue
        if row.startswith("-"):
            continue
        lines.add(new_line)
        new_line += 1
    return lines


def build_filtered_diff(files: list[dict]) -> str:
    """Reconstructs a unified-diff-like text from the PR files API response,
    skipping excluded paths and files with no textual patch (binary/too large).
    """
    chunks = []
    for f in files:
        filename = f.get("filename", "")
        patch = f.get("patch")
        if not patch or is_excluded(filename):
            continue
        chunks.append(f"--- a/{filename}\n+++ b/{filename}\n{patch}")
    return "\n".join(chunks)
