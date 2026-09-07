"""Tests for diff_batching, exercised against the real `files` payload from
GET /repos/django-otp/django-otp/pulls/191/files (a merged PR from this same
push) - real filenames, real patches, byte-for-byte as GitHub returned them -
rather than only synthetic fixtures, so the budget/overhead accounting is
checked against a real diff shape, not just internal consistency with itself.
"""
import json

from ai_pr_reviewer.diff_batching import select_and_batch

REAL_PR_FILES = json.loads(r"""
[
  {
    "filename": "src/django_otp/plugins/otp_hotp/static/otp_hotp/css/qrcode.css",
    "patch": "@@ -0,0 +1,11 @@\n+.qrcode-container {\n+    text-align: center;\n+}\n+\n+.qrcode-image {\n+    background-color: white;\n+}\n+\n+.qrcode-hidden {\n+    display: none;\n+}"
  },
  {
    "filename": "src/django_otp/plugins/otp_hotp/static/otp_hotp/js/qrcode.js",
    "patch": "@@ -0,0 +1,24 @@\n+function ready(fn) {\n+    if (document.readyState !== 'loading') {\n+        fn();\n+    } else {\n+        document.addEventListener('DOMContentLoaded', fn);\n+    }\n+}\n+\n+ready(function () {\n+    var qrCodeImage = document.querySelector('.qrcode-image');\n+    if (!qrCodeImage) {\n+        return;\n+    }\n+    qrCodeImage.addEventListener('error', function () {\n+        var qrCode = document.getElementById('qrcode');\n+        var noQrCode = document.getElementById('no-qrcode');\n+        if (qrCode) {\n+            qrCode.classList.add('qrcode-hidden');\n+        }\n+        if (noQrCode) {\n+            noQrCode.classList.remove('qrcode-hidden');\n+        }\n+    });\n+});"
  },
  {
    "filename": "src/django_otp/plugins/otp_hotp/templates/otp_hotp/admin/config.html",
    "patch": "@@ -1,15 +1,21 @@\n {% extends \"admin/base_site.html\" %}\n+{% load static %}\n+\n+{% block extrastyle %}\n+    {{ block.super }}\n+    <link rel=\"stylesheet\" type=\"text/css\" href=\"{% static \"otp_hotp/css/qrcode.css\" %}\" />\n+    <script src=\"{% static \"otp_hotp/js/qrcode.js\" %}\"></script>\n+{% endblock %}\n \n {% block content %}\n-<div style=\"text-align: center;\">\n+<div class=\"qrcode-container\">\n   <p id=\"qrcode\">\n     <img width=\"200\" height=\"200\"\n-         style=\"background-color: white\"\n+         class=\"qrcode-image\"\n          src=\"{% url \"admin:otp_hotp_hotpdevice_qrcode\" pk=device.pk %}\"\n-         onerror=\"document.getElementById('qrcode').style.display = 'none'; document.getElementById('no-qrcode').style.display = 'block';\"\n     >\n   </p>\n-  <p id=\"no-qrcode\" style=\"display: none\">\n+  <p id=\"no-qrcode\" class=\"qrcode-hidden\">\n     Install <a href=\"https://pypi.python.org/pypi/segno/\">segno</a> or <a href=\"https://pypi.python.org/pypi/qrcode/\">qrcode</a> or use the URL below:\n   </p>\n   <p>{{ device.config_url }}</p>"
  },
  {
    "filename": "src/django_otp/plugins/otp_hotp/tests.py",
    "patch": "@@ -284,6 +284,27 @@ def test_change_perm(self):\n                 response = self.client.get(url)\n                 self.assertEqual(response.status_code, 200)\n \n+    def test_config_page_has_no_inline_style_or_script(self):\n+        \"\"\"\n+        The QR code config page shouldn't rely on inline style attributes,\n+        <style> blocks, or event handler attributes (e.g. onerror), since\n+        those are blocked by a strict Content-Security-Policy.\n+\n+        https://github.com/django-otp/django-otp/issues/143\n+        \"\"\"\n+        self._add_device_perms('view_hotpdevice')\n+        self.client.login(username='admin', password='password')\n+\n+        url = reverse('admin:otp_hotp_hotpdevice_config', kwargs={'pk': self.device.pk})\n+        response = self.client.get(url)\n+        content = response.content.decode()\n+\n+        self.assertNotIn('style=\"', content)\n+        self.assertNotIn('<style', content)\n+        self.assertNotIn('onerror=', content)\n+        self.assertIn('otp_hotp/css/qrcode.css', content)\n+        self.assertIn('otp_hotp/js/qrcode.js', content)\n+\n     @override_settings(OTP_ADMIN_HIDE_SENSITIVE_DATA=True)\n     def test_sensitive_information_hidden_while_adding_device(self):\n         fields = self._get_fields(device=None)"
  },
  {
    "filename": "src/django_otp/plugins/otp_totp/static/otp_totp/css/qrcode.css",
    "patch": "@@ -0,0 +1,11 @@\n+.qrcode-container {\n+    text-align: center;\n+}\n+\n+.qrcode-image {\n+    background-color: white;\n+}\n+\n+.qrcode-hidden {\n+    display: none;\n+}"
  },
  {
    "filename": "src/django_otp/plugins/otp_totp/static/otp_totp/js/qrcode.js",
    "patch": "@@ -0,0 +1,24 @@\n+function ready(fn) {\n+    if (document.readyState !== 'loading') {\n+        fn();\n+    } else {\n+        document.addEventListener('DOMContentLoaded', fn);\n+    }\n+}\n+\n+ready(function () {\n+    var qrCodeImage = document.querySelector('.qrcode-image');\n+    if (!qrCodeImage) {\n+        return;\n+    }\n+    qrCodeImage.addEventListener('error', function () {\n+        var qrCode = document.getElementById('qrcode');\n+        var noQrCode = document.getElementById('no-qrcode');\n+        if (qrCode) {\n+            qrCode.classList.add('qrcode-hidden');\n+        }\n+        if (noQrCode) {\n+            noQrCode.classList.remove('qrcode-hidden');\n+        }\n+    });\n+});"
  },
  {
    "filename": "src/django_otp/plugins/otp_totp/templates/otp_totp/admin/config.html",
    "patch": "@@ -1,15 +1,21 @@\n {% extends \"admin/base_site.html\" %}\n+{% load static %}\n+\n+{% block extrastyle %}\n+    {{ block.super }}\n+    <link rel=\"stylesheet\" type=\"text/css\" href=\"{% static \"otp_totp/css/qrcode.css\" %}\" />\n+    <script src=\"{% static \"otp_totp/js/qrcode.js\" %}\"></script>\n+{% endblock %}\n \n {% block content %}\n-<div style=\"text-align: center;\">\n+<div class=\"qrcode-container\">\n   <p id=\"qrcode\">\n     <img width=\"200\" height=\"200\"\n-         style=\"background-color: white\"\n+         class=\"qrcode-image\"\n          src=\"{% url \"admin:otp_totp_totpdevice_qrcode\" pk=device.pk %}\"\n-         onerror=\"document.getElementById('qrcode').style.display = 'none'; document.getElementById('no-qrcode').style.display = 'block';\"\n     >\n   </p>\n-  <p id=\"no-qrcode\" style=\"display: none\">\n+  <p id=\"no-qrcode\" class=\"qrcode-hidden\">\n     Install <a href=\"https://pypi.python.org/pypi/segno/\">segno</a> or <a href=\"https://pypi.python.org/pypi/qrcode/\">qrcode</a> or use the URL below:\n   </p>\n   <p>{{ device.config_url }}</p>"
  },
  {
    "filename": "src/django_otp/plugins/otp_totp/tests.py",
    "patch": "@@ -240,6 +240,27 @@ def test_change_perm(self):\n                 response = self.client.get(url)\n                 self.assertEqual(response.status_code, 200)\n \n+    def test_config_page_has_no_inline_style_or_script(self):\n+        \"\"\"\n+        The QR code config page shouldn't rely on inline style attributes,\n+        <style> blocks, or event handler attributes (e.g. onerror), since\n+        those are blocked by a strict Content-Security-Policy.\n+\n+        https://github.com/django-otp/django-otp/issues/143\n+        \"\"\"\n+        self._add_device_perms('view_totpdevice')\n+        self.client.login(username='admin', password='password')\n+\n+        url = reverse('admin:otp_totp_totpdevice_config', kwargs={'pk': self.device.pk})\n+        response = self.client.get(url)\n+        content = response.content.decode()\n+\n+        self.assertNotIn('style=\"', content)\n+        self.assertNotIn('<style', content)\n+        self.assertNotIn('onerror=', content)\n+        self.assertIn('otp_totp/css/qrcode.css', content)\n+        self.assertIn('otp_totp/js/qrcode.js', content)\n+\n     @override_settings(OTP_ADMIN_HIDE_SENSITIVE_DATA=True)\n     def test_sensitive_information_hidden_while_adding_device(self):\n         fields = self._get_fields(device=None)"
  },
  {
    "filename": "src/django_otp/static/django_otp/css/login.css",
    "patch": "@@ -0,0 +1,10 @@\n+input#id_otp_token,\n+select#id_otp_device\n+{\n+    clear: both;\n+    padding: 6px;\n+    width: 100%;\n+    -webkit-box-sizing: border-box;\n+    -moz-box-sizing: border-box;\n+            box-sizing: border-box;\n+}"
  },
  {
    "filename": "src/django_otp/templates/otp/admin111/login.html",
    "patch": "@@ -4,20 +4,8 @@\n {% block extrastyle %}\n     {{ block.super }}\n     <link rel=\"stylesheet\" type=\"text/css\" href=\"{% static \"admin/css/login.css\" %}\" />\n+    <link rel=\"stylesheet\" type=\"text/css\" href=\"{% static \"django_otp/css/login.css\" %}\" />\n     {{ form.media }}\n-\n-    <style type=\"text/css\">\n-        input#id_otp_token,\n-        select#id_otp_device\n-        {\n-            clear: both;\n-            padding: 6px;\n-            width: 100%;\n-            -webkit-box-sizing: border-box;\n-            -moz-box-sizing: border-box;\n-                    box-sizing: border-box;\n-        }\n-    </style>\n {% endblock %}\n \n {% block bodyclass %}{{ block.super }} login{% endblock %}"
  },
  {
    "filename": "src/django_otp/tests.py",
    "patch": "@@ -427,6 +427,19 @@ def test_admin_login_template(self):\n         )\n         self.assertRedirects(response, '/')\n \n+    def test_admin_login_template_has_no_inline_style(self):\n+        \"\"\"\n+        The admin login page shouldn't rely on an inline <style> block,\n+        since that's blocked by a strict Content-Security-Policy.\n+\n+        https://github.com/django-otp/django-otp/issues/143\n+        \"\"\"\n+        response = self.client.get(reverse('otpadmin:login'))\n+        content = response.content.decode()\n+\n+        self.assertNotIn('<style', content)\n+        self.assertIn('django_otp/css/login.css', content)\n+\n     def test_authenticate(self):\n         device = self.alice.staticdevice_set.get()\n         token = device.token_set.get()"
  }
]
""")

ALL_FILENAMES = {f["filename"] for f in REAL_PR_FILES}


def _every_file_accounted_for(batches, skipped):
    seen = set(skipped)
    for b in batches:
        seen.update(b.filenames)
    return seen == ALL_FILENAMES


def test_select_and_batch_single_batch_when_under_budget():
    batches, skipped = select_and_batch(REAL_PR_FILES)
    assert len(batches) == 1
    assert skipped == []
    assert set(batches[0].filenames) == ALL_FILENAMES


def test_select_and_batch_splits_into_multiple_batches_when_over_budget():
    batches, skipped = select_and_batch(REAL_PR_FILES, max_diff_chars=1200, max_batches=10)
    assert len(batches) > 1
    for b in batches:
        assert len(b.diff_text) <= 1200
    assert _every_file_accounted_for(batches, skipped)


def test_select_and_batch_never_splits_a_single_file_across_batches():
    batches, _ = select_and_batch(REAL_PR_FILES, max_diff_chars=1200, max_batches=10)
    for b in batches:
        for filename in b.filenames:
            # the full patch appears intact in exactly one batch's diff_text
            assert b.diff_text.count(f"--- a/{filename}\n") == 1


def test_select_and_batch_skips_a_file_whose_patch_alone_exceeds_max_diff_chars():
    # the two tests.py-in-plugin patches (~1KB each) are the largest single
    # chunks in this fixture.
    batches, skipped = select_and_batch(REAL_PR_FILES, max_diff_chars=200, max_batches=10)
    assert "src/django_otp/plugins/otp_hotp/tests.py" in skipped
    assert "src/django_otp/plugins/otp_totp/tests.py" in skipped
    for b in batches:
        assert len(b.diff_text) <= 200


def test_select_and_batch_deprioritizes_pure_deletion_files():
    files = list(REAL_PR_FILES) + [
        {"filename": "src/deleted_module.py", "patch": "@@ -1,3 +0,0 @@\n-old1\n-old2\n-old3"}
    ]
    # A tight single-batch budget - the pure-deletion file should be dropped
    # before any of the genuinely new/changed real files are.
    _, skipped = select_and_batch(files, max_diff_chars=300, max_batches=1)
    assert "src/deleted_module.py" in skipped


def test_select_and_batch_caps_at_max_batches_and_reports_skipped():
    batches, skipped = select_and_batch(REAL_PR_FILES, max_diff_chars=1200, max_batches=2)
    assert len(batches) == 2
    assert skipped
    assert _every_file_accounted_for(batches, skipped)
