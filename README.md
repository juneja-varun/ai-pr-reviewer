# AI PR Reviewer

A GitHub Action that reviews pull request diffs with Claude and posts real
inline review comments — correctness bugs, security issues, obvious
performance problems, and missing test coverage, skipping style nits a
linter already catches. Pushing a new commit updates the existing review
instead of piling up duplicates.

[![CI](https://github.com/juneja-varun/ai-pr-reviewer/actions/workflows/ci.yml/badge.svg)](https://github.com/juneja-varun/ai-pr-reviewer/actions/workflows/ci.yml)

## How it works

```
PR opened/updated
       │
       ▼
GitHub Action checks out the repo
       │
       ▼
ai_pr_reviewer fetches the PR's changed files via the GitHub REST API
(following pagination on large PRs)
       │
       ▼
Lockfiles and generated files (package-lock.json, dist/*, etc.) are
filtered out, and the remaining files are split into a few review
batches if the diff is too large for one request
       │
       ▼
Each batch is sent to Claude, which reports findings via a forced tool
call - {file, line, severity, category, summary} - not freeform text
       │
       ▼
Findings below the severity threshold are dropped; the rest are split
into ones that anchor to a real diff line and ones that don't
       │
       ▼
The summary comment is updated in place (or created, on the first run);
anchorable findings are posted as inline review comments, and any of the
bot's own stale, unreplied comments from a prior run are cleaned up
```

## Usage

Add a workflow to the repo you want reviewed:

```yaml
# .github/workflows/review.yml
name: AI PR Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: juneja-varun/ai-pr-reviewer@main
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Add `ANTHROPIC_API_KEY` as a repository secret (Settings → Secrets and
variables → Actions).

### Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `anthropic-api-key` | yes | — | Anthropic API key |
| `github-token` | no | `${{ github.token }}` | Token used to read the diff and post the comment |
| `model` | no | `claude-sonnet-5` | Anthropic model to use |
| `min-severity` | no | `MEDIUM` | Minimum severity to report (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) |

## Local development

```bash
pip install -e ".[dev]"
ruff check src tests
pytest -v
```

Run it against a real PR locally:

```bash
export GITHUB_TOKEN=...
export ANTHROPIC_API_KEY=...
export GITHUB_REPOSITORY=owner/repo
export PR_NUMBER=123
python -m ai_pr_reviewer
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Why

Most "AI code review" tools are black boxes. This one started as a
~200-line proof of concept and has grown since - structured findings
via tool-use, real inline comments anchored to diff lines, idempotent
re-review, smarter handling of large diffs - because those are the
actual gaps between a demo and something worth trusting on a real PR.
It's still dependency-light (`requests` only, no framework, no vendored
LLM SDK) and every module is still small enough to read end to end.

## License

MIT
