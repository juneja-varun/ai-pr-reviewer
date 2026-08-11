"""Excludes lockfiles and other generated files from what gets sent to the LLM.

These files are large, machine-generated, and never what a reviewer actually
wants commented on - including them just burns diff budget (see
llm_client.review_diff's truncation) and adds noise the model might latch
onto instead of the actual code change.
"""
from __future__ import annotations

import fnmatch
import posixpath

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
