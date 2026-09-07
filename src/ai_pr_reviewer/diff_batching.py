"""Selects and batches changed files for LLM review when the full diff won't
fit in one request, instead of blindly truncating a single giant string
(which can cut a file's patch off mid-hunk and hand the model corrupted
context - see llm_client.review_diff's old max_diff_chars slice).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .diff_filter import is_excluded, is_pure_deletion


@dataclass
class ReviewBatch:
    diff_text: str
    filenames: list[str] = field(default_factory=list)


def _diff_chunk(filename: str, patch: str) -> str:
    return f"--- a/{filename}\n+++ b/{filename}\n{patch}"


def select_and_batch(
    files: list[dict],
    max_diff_chars: int = 60_000,
    max_batches: int = 3,
) -> tuple[list[ReviewBatch], list[str]]:
    """Groups a PR's changed files into up to `max_batches` diff batches, each
    at most `max_diff_chars` long, for separate review calls.

    - Excludes generated/lockfile paths and files with no patch (binary), same
      as build_filtered_diff.
    - A file whose own patch is too large to fit in any batch is skipped
      entirely (reported in the returned skipped-filenames list) rather than
      truncated into a corrupted hunk - no file is ever split across batches.
    - Pure-deletion files (nothing added, so nothing to comment on) are
      reviewed last, so they're the first to be dropped if the budget runs out
      before genuinely new code.
    - Once `max_batches` batches are full, anything left over is skipped and
      named, rather than silently dropped.
    """
    candidates = []
    for f in files:
        filename = f.get("filename", "")
        patch = f.get("patch")
        if not patch or is_excluded(filename):
            continue
        candidates.append((filename, patch))

    candidates.sort(key=lambda item: (is_pure_deletion(item[1]), len(item[1])))

    batches: list[ReviewBatch] = []
    skipped: list[str] = []
    current_filenames: list[str] = []
    current_chunks: list[str] = []
    current_len = 0
    batches_full = False

    def flush_current() -> None:
        nonlocal current_filenames, current_chunks, current_len
        if current_filenames:
            batches.append(
                ReviewBatch(diff_text="\n".join(current_chunks), filenames=list(current_filenames))
            )
        current_filenames, current_chunks, current_len = [], [], 0

    for filename, patch in candidates:
        chunk = _diff_chunk(filename, patch)
        chunk_len = len(chunk)

        if chunk_len > max_diff_chars:
            skipped.append(filename)
            continue

        needs_new_batch = current_len + chunk_len > max_diff_chars

        if needs_new_batch:
            flush_current()
            # Flushing just used up one of the max_batches slots. If that
            # was the last slot, no further batch may be opened - everything
            # from here on is skipped, not silently packed into an
            # (uncounted) extra batch.
            if len(batches) >= max_batches:
                batches_full = True

        if batches_full:
            skipped.append(filename)
            continue

        current_filenames.append(filename)
        current_chunks.append(chunk)
        current_len += chunk_len

    # Safe to call even when batches_full: once full, every file goes to
    # skipped and current_* stays empty, so this is a no-op in that case.
    flush_current()

    return batches, skipped
