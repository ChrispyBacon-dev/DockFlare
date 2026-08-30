import pathlib
import tempfile
import unittest

from app import get_static_asset_version


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


if __name__ == "__main__":
    unittest.main()
