# AI PR Reviewer

A GitHub Action that reviews pull request diffs with Claude and posts the
findings as a PR comment — correctness bugs, security issues, obvious
performance problems, and missing test coverage, skipping style nits a
linter already catches.

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
       │
       ▼
Lockfiles and generated files (package-lock.json, dist/*, etc.) are
filtered out before anything is sent to the model
       │
       ▼
Remaining diff is sent to Claude with a fixed review-focused system prompt
       │
       ▼
Structured summary + findings posted as a PR comment
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

Most "AI code review" tools are black boxes. This one is ~200 lines,
does one thing, and every piece — diff fetching, prompt, comment
formatting — is readable in a sitting.

## License

MIT
