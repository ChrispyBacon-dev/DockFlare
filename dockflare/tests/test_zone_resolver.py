import importlib.util
import pathlib
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "app" / "core" / "zone_resolver.py"
SPEC = importlib.util.spec_from_file_location("zone_resolver", MODULE_PATH)
RESOLVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESOLVER)


class ZoneResolverTests(unittest.TestCase):
    def setUp(self):
        self.zones = [
            {"id": "parent", "name": "side.co.uk"},
            {"id": "nested", "name": "internal.side.co.uk"},
            {"id": "primary", "name": "example.net"},
        ]

    def test_multi_label_zone(self):
        result = RESOLVER.match_zone_for_hostname("domain.side.co.uk", self.zones)
        self.assertEqual(result, {"id": "parent", "name": "side.co.uk"})

    def test_apex_zone(self):
        result = RESOLVER.match_zone_for_hostname("side.co.uk", self.zones)
        self.assertEqual(result["id"], "parent")

    def test_nested_zone_wins(self):
        result = RESOLVER.match_zone_for_hostname("app.internal.side.co.uk", self.zones)
        self.assertEqual(result["id"], "nested")

    def test_label_boundary_is_required(self):
        result = RESOLVER.match_zone_for_hostname("notside.co.uk", self.zones)
        self.assertIsNone(result)

    def test_wildcard_is_normalized(self):
        result = RESOLVER.match_zone_for_hostname("*.apps.side.co.uk", self.zones)
        self.assertEqual(result["id"], "parent")

    def test_case_and_root_dot_are_normalized(self):
        result = RESOLVER.match_zone_for_hostname("APP.SIDE.CO.UK.", self.zones)
        self.assertEqual(result["name"], "side.co.uk")

    def test_idna_is_normalized(self):
        zones = [{"id": "idna", "name": "xn--bcher-kva.example"}]
        result = RESOLVER.match_zone_for_hostname("shop.bücher.example", zones)
        self.assertEqual(result["id"], "idna")

    def test_invalid_explicit_name_fails_closed(self):
        with self.assertRaises(RESOLVER.ZoneResolutionError) as raised:
            RESOLVER.resolve_zone("app.side.co.uk", self.zones, explicit_zone_name="invalid.example")
        self.assertEqual(raised.exception.code, "explicit_zone_not_found")

    def test_explicit_zone_must_contain_hostname(self):
        with self.assertRaises(RESOLVER.ZoneResolutionError) as raised:
            RESOLVER.resolve_zone("app.side.co.uk", self.zones, explicit_zone_id="primary")
        self.assertEqual(raised.exception.code, "explicit_zone_conflict")

    def test_unavailable_inventory_can_use_compatibility_default(self):
        result = RESOLVER.resolve_zone(
            "app.side.co.uk",
            [],
            default_zone_id="parent",
            inventory_status="unavailable",
            allow_unverified_default=True,
        )
        self.assertEqual(result["source"], "default_unverified")
        self.assertFalse(result["verified"])

    def test_strict_caller_rejects_unavailable_inventory(self):
        with self.assertRaises(RESOLVER.ZoneResolutionError) as raised:
            RESOLVER.resolve_zone("app.side.co.uk", [], inventory_status="unavailable")
        self.assertEqual(raised.exception.code, "inventory_unavailable")

    def test_default_zone_mismatch_is_rejected(self):
        with self.assertRaises(RESOLVER.ZoneResolutionError) as raised:
            RESOLVER.resolve_zone("app.unknown.test", self.zones, default_zone_id="primary")
        self.assertEqual(raised.exception.code, "default_zone_mismatch")

    def test_missing_default_zone_is_rejected(self):
        with self.assertRaises(RESOLVER.ZoneResolutionError) as raised:
            RESOLVER.resolve_zone("app.unknown.test", self.zones, default_zone_id="missing")
        self.assertEqual(raised.exception.code, "default_zone_not_found")

    def test_invalid_dns_characters_are_rejected(self):
        with self.assertRaises(RESOLVER.ZoneResolutionError) as raised:
            RESOLVER.normalize_dns_name("bad_name.side.co.uk")
        self.assertEqual(raised.exception.code, "hostname_invalid")

    def test_duplicate_normalized_zone_is_rejected(self):
        zones = [
            {"id": "one", "name": "side.co.uk"},
            {"id": "two", "name": "SIDE.CO.UK"},
        ]
        with self.assertRaises(RESOLVER.ZoneResolutionError) as raised:
            RESOLVER.match_zone_for_hostname("app.side.co.uk", zones)
        self.assertEqual(raised.exception.code, "explicit_zone_conflict")


if __name__ == "__main__":
    unittest.main()
