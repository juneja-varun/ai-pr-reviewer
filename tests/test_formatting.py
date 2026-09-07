from ai_pr_reviewer.formatting import (
    FINDING_MARKER,
    SUMMARY_MARKER,
    Finding,
    meets_threshold,
    render_empty_diff_body,
    render_inline_comment_body,
    render_no_issues_body,
    render_summary_body,
)


def test_meets_threshold_ordering():
    assert meets_threshold("CRITICAL", "LOW")
    assert meets_threshold("MEDIUM", "MEDIUM")
    assert not meets_threshold("LOW", "MEDIUM")
    assert not meets_threshold("HIGH", "CRITICAL")


def test_render_empty_diff_body_has_marker():
    body = render_empty_diff_body()
    assert SUMMARY_MARKER in body
    assert "Nothing to review" in body


def test_render_no_issues_body_has_marker_and_threshold():
    body = render_no_issues_body("HIGH")
    assert SUMMARY_MARKER in body
    assert "HIGH" in body


def test_render_summary_body_includes_marker_and_counts():
    findings = [
        Finding(file="a.py", line=1, severity="HIGH", category="correctness", summary="bug"),
        Finding(file="a.py", line=2, severity="LOW", category="test_coverage", summary="nit"),
    ]
    shown = [findings[0]]
    body = render_summary_body(
        reviewed_files=["a.py", "b.py"],
        skipped_files=[],
        all_findings=findings,
        shown_findings=shown,
        unanchored_findings=[],
        min_severity="MEDIUM",
    )
    assert SUMMARY_MARKER in body
    assert "Reviewed 2 files" in body
    assert "1 finding at or above MEDIUM" in body
    assert "1 HIGH" in body
    assert "1 finding below MEDIUM severity suppressed" in body


def test_render_summary_body_uses_singular_for_one_file_and_one_finding():
    findings = [Finding(file="a.py", line=1, severity="HIGH", category="correctness", summary="bug")]
    body = render_summary_body(
        reviewed_files=["a.py"],
        skipped_files=[],
        all_findings=findings,
        shown_findings=findings,
        unanchored_findings=[],
        min_severity="MEDIUM",
    )
    assert "Reviewed 1 file." in body
    assert "1 finding at or above MEDIUM" in body
    assert "file(s)" not in body
    assert "finding(s)" not in body


def test_render_summary_body_lists_unanchored_findings_separately():
    finding = Finding(file="a.py", line=999, severity="HIGH", category="correctness", summary="drifted")
    body = render_summary_body(
        reviewed_files=["a.py"],
        skipped_files=[],
        all_findings=[finding],
        shown_findings=[finding],
        unanchored_findings=[finding],
        min_severity="MEDIUM",
    )
    assert "couldn't be anchored" in body
    assert "drifted" in body


def test_render_summary_body_lists_skipped_files():
    body = render_summary_body(
        reviewed_files=["a.py"],
        skipped_files=["huge.py"],
        all_findings=[],
        shown_findings=[],
        unanchored_findings=[],
        min_severity="MEDIUM",
    )
    assert "1 file skipped as too large to review" in body
    assert "huge.py" in body


def test_render_inline_comment_body_has_finding_marker():
    finding = Finding(file="a.py", line=1, severity="CRITICAL", category="security", summary="sql injection")
    body = render_inline_comment_body(finding)
    assert FINDING_MARKER in body
    assert "CRITICAL" in body
    assert "sql injection" in body
