from ai_pr_reviewer.diff_filter import build_filtered_diff, is_excluded


def test_is_excluded_matches_known_lockfiles():
    assert is_excluded("package-lock.json")
    assert is_excluded("frontend/yarn.lock")
    assert is_excluded("backend/poetry.lock")
    assert is_excluded("app.min.js")
    assert is_excluded("dist/bundle.js")
    assert is_excluded("frontend/dist/bundle.js")


def test_is_excluded_does_not_match_regular_source():
    assert not is_excluded("src/app.py")
    assert not is_excluded("orders/tasks.py")
    assert not is_excluded("package.json")  # the manifest itself, not the lock


def test_build_filtered_diff_skips_excluded_and_binary_files():
    files = [
        {"filename": "src/app.py", "patch": "@@ -1 +1 @@\n-old\n+new"},
        {"filename": "package-lock.json", "patch": "@@ -1,50 +1,50 @@\n... huge ..."},
        {"filename": "logo.png"},  # no "patch" key - binary file
    ]

    diff = build_filtered_diff(files)

    assert "src/app.py" in diff
    assert "package-lock.json" not in diff
    assert "logo.png" not in diff


def test_build_filtered_diff_empty_when_everything_excluded():
    files = [{"filename": "yarn.lock", "patch": "@@ -1 +1 @@\n-a\n+b"}]
    assert build_filtered_diff(files) == ""
