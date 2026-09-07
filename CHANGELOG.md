# Changelog

## 0.2.0

- Review findings are now structured (file, line, severity, category) via
  Claude tool-use, instead of a freeform markdown paragraph.
- Findings anchored to a real diff line are posted as actual inline PR
  review comments, not folded into one top-level comment.
- Pushing a new commit updates the existing summary comment and inline
  comments in place, instead of piling up a duplicate review on every push.
  Stale inline comments from a prior run are cleaned up automatically -
  unless a human has replied to one, in which case it's left alone.
- Added a `min-severity` input (default `MEDIUM`) to skip low-severity
  nitpicks by default.
- Large PRs are split into a few review batches instead of having their
  diff truncated at a fixed character count, which could previously cut a
  file's patch off mid-hunk.
- `get_pr_files` now follows pagination, instead of silently capping at
  100 changed files.

## 0.1.0

- Initial release: GitHub Action that reviews PR diffs with Claude and
  posts findings as a comment.
- Diff is built from the PR files API and filters out lockfiles and
  other generated files (`package-lock.json`, `yarn.lock`, `dist/*`,
  `build/*`, etc.) before it's sent to the model.
