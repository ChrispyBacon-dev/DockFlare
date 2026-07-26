import importlib.util
import pathlib
import unittest


ZONE_DETECTION_PATH = pathlib.Path(__file__).resolve().parents[1] / "app" / "core" / "zone_detection.py"
spec = importlib.util.spec_from_file_location("zone_detection", ZONE_DETECTION_PATH)
assert spec is not None and spec.loader is not None
zone_detection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(zone_detection)
find_best_zone_for_hostname = zone_detection.find_best_zone_for_hostname


class ZoneDetectionTest(unittest.TestCase):
    def test_selects_longest_matching_zone_suffix(self):
        zones = [
            {"id": "primary-zone", "name": "example.com"},
            {"id": "secondary-zone", "name": "secondary.example.com"},
        ]

        zone_id, zone_name = find_best_zone_for_hostname("app.secondary.example.com", zones)

        self.assertEqual(zone_id, "secondary-zone")
        self.assertEqual(zone_name, "secondary.example.com")

    def test_matches_wildcard_hostname_against_zone(self):
        zones = [{"id": "secondary-zone", "name": "secondary.example.com"}]

        zone_id, zone_name = find_best_zone_for_hostname("*.secondary.example.com", zones)

        self.assertEqual(zone_id, "secondary-zone")
        self.assertEqual(zone_name, "secondary.example.com")

    def test_returns_empty_result_when_no_zone_matches(self):
        zones = [{"id": "primary-zone", "name": "example.com"}]

        zone_id, zone_name = find_best_zone_for_hostname("app.other.test", zones)

        self.assertIsNone(zone_id)
        self.assertIsNone(zone_name)


if __name__ == "__main__":
    unittest.main()
