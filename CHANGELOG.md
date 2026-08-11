# Changelog

## 0.1.0

- Initial release: GitHub Action that reviews PR diffs with Claude and
  posts findings as a comment.
- Diff is built from the PR files API and filters out lockfiles and
  other generated files (`package-lock.json`, `yarn.lock`, `dist/*`,
  `build/*`, etc.) before it's sent to the model.
