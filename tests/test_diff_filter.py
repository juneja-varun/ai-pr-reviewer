from ai_pr_reviewer.diff_filter import (
    build_filtered_diff,
    commentable_lines,
    is_excluded,
    is_pure_deletion,
)

# Real patch from django-otp/django-otp#191 (a merged PR). Line 7 - the added
# <link> tag - was confirmed against the actual merged file on GitHub, not just
# derived from re-reading this patch.
REAL_SINGLE_HUNK_PATCH = """\
@@ -4,20 +4,8 @@
 {% block extrastyle %}
     {{ block.super }}
     <link rel="stylesheet" type="text/css" href="{% static "admin/css/login.css" %}" />
+    <link rel="stylesheet" type="text/css" href="{% static "django_otp/css/login.css" %}" />
     {{ form.media }}
-
-    <style type="text/css">
-        input#id_otp_token,
-        select#id_otp_device
-        {
-            clear: both;
-            padding: 6px;
-            width: 100%;
-            -webkit-box-sizing: border-box;
-            -moz-box-sizing: border-box;
-                    box-sizing: border-box;
-        }
-    </style>
 {% endblock %}

 {% block bodyclass %}{{ block.super }} login{% endblock %}"""

# Real patch from ui/django-post_office#536 (a merged PR), trimmed to its first
# two hunks - used to confirm the new-file line counter resets per hunk header
# instead of continuing across hunks.
REAL_MULTI_HUNK_PATCH = """\
@@ -1,7 +1,6 @@
 import re
 import time
 from datetime import timedelta
-from multiprocessing.context import TimeoutError
 from unittest.mock import patch
 from zoneinfo import ZoneInfo

@@ -630,7 +629,8 @@ def test_invalid_expired(self):

     def test_batch_delivery_timeout(self):
         \"\"\"
-        Ensure that batch delivery timeout is respected.
+        Ensure that batch delivery timeout is respected, and that a timed-out
+        email is requeued rather than left to blow up send_queued().
         \"\"\"
         _ = Email.objects.create(
             to=['to@example.com'],
"""


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


def test_is_pure_deletion_true_for_deletion_only_patch():
    assert is_pure_deletion("@@ -1,2 +0,0 @@\n-old line one\n-old line two")


def test_is_pure_deletion_false_when_any_line_added():
    assert not is_pure_deletion(REAL_SINGLE_HUNK_PATCH)


def test_commentable_lines_matches_real_merged_file():
    # Expected set independently confirmed against the actual file content at
    # django-otp/django-otp@7113e02 (the PR's merge commit), not derived from
    # re-reading commentable_lines' own implementation.
    assert commentable_lines(REAL_SINGLE_HUNK_PATCH) == {4, 5, 6, 7, 8, 9, 10, 11}


def test_commentable_lines_resets_counter_per_hunk_header():
    result = commentable_lines(REAL_MULTI_HUNK_PATCH)
    assert {1, 2, 3, 4, 5, 6}.issubset(result)
    # The second hunk's own header says the new file starts at line 629 -
    # if the counter incorrectly kept counting up from hunk one instead of
    # resetting, this would be missing.
    assert 629 in result
    assert max(n for n in result if n < 100) == 6


def test_commentable_lines_empty_for_pure_deletion_patch():
    assert commentable_lines("@@ -1,2 +0,0 @@\n-old line one\n-old line two") == set()
