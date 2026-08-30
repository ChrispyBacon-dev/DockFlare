import pathlib
import tempfile
import unittest

from flask import render_template_string

from app import app, get_static_asset_version


class StaticAssetVersionTests(unittest.TestCase):
    def test_asset_version_changes_with_content(self):
        with tempfile.TemporaryDirectory() as directory:
            asset_path = pathlib.Path(directory) / "main.js"
            asset_path.write_text("first", encoding="utf-8")
            first_version = get_static_asset_version(asset_path)

            asset_path.write_text("second", encoding="utf-8")
            second_version = get_static_asset_version(asset_path)

        self.assertEqual(len(first_version), 12)
        self.assertNotEqual(first_version, second_version)

    def test_missing_asset_uses_application_version(self):
        version = get_static_asset_version("/missing/dockflare/main.js")
        self.assertTrue(version)
        self.assertNotIn("/", version)

    def test_base_template_renders_fingerprinted_main_script(self):
        main_js_path = pathlib.Path(app.static_folder) / "js" / "main.js"
        expected_version = get_static_asset_version(main_js_path)

        with app.test_request_context("/"):
            rendered = render_template_string(
                '{% extends "base.html" %}{% block content %}{% endblock %}'
            )

        self.assertIn(
            f'src="/static/js/main.js?v={expected_version}"',
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
