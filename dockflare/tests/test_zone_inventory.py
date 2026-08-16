import unittest
from unittest.mock import patch

import requests

from app import app
from app.core import cloudflare_api


class ZoneInventoryTests(unittest.TestCase):
    def setUp(self):
        cloudflare_api._last_good_zone_inventories.clear()

    def tearDown(self):
        cloudflare_api._last_good_zone_inventories.clear()

    def test_inventory_uses_supported_pagination(self):
        first_page = [{"id": f"zone-{index}", "name": f"zone-{index}.example"} for index in range(50)]
        second_page = [{"id": "zone-50", "name": "zone-50.example"}]
        responses = [
            {"result": first_page, "result_info": {"total_pages": 2}},
            {"result": second_page, "result_info": {"total_pages": 2}},
        ]
        with app.app_context(), patch.dict(app.config, {"CF_ACCOUNT_ID": "account-1"}), \
             patch.object(cloudflare_api.cache, "get", return_value=None), \
             patch.object(cloudflare_api.cache, "set") as cache_set, \
             patch.object(cloudflare_api, "cf_api_request", side_effect=responses) as request:
            inventory = cloudflare_api.get_account_zone_inventory(force_refresh=True)
        self.assertEqual(inventory["status"], "complete")
        self.assertEqual(len(inventory["zones"]), 51)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args_list[0].kwargs["params"]["per_page"], 50)
        self.assertEqual(request.call_args_list[1].kwargs["params"]["page"], 2)
        cache_set.assert_called_once()

    def test_partial_refresh_keeps_last_known_good_inventory(self):
        previous = [{"id": "zone-1", "name": "example.com"}]
        cloudflare_api._last_good_zone_inventories["account-1"] = previous
        first_page = [{"id": f"zone-{index}", "name": f"zone-{index}.example"} for index in range(50)]
        responses = [
            {"result": first_page, "result_info": {"total_pages": 2}},
            requests.exceptions.RequestException("upstream failure"),
        ]
        with app.app_context(), patch.dict(app.config, {"CF_ACCOUNT_ID": "account-1"}), \
             patch.object(cloudflare_api.cache, "get", return_value=None), \
             patch.object(cloudflare_api.cache, "set") as cache_set, \
             patch.object(cloudflare_api, "cf_api_request", side_effect=responses):
            inventory = cloudflare_api.get_account_zone_inventory(force_refresh=True)
        self.assertEqual(inventory["status"], "stale")
        self.assertEqual(inventory["zones"], previous)
        cache_set.assert_not_called()

    def test_failed_first_load_is_not_cached_as_empty_success(self):
        with app.app_context(), patch.dict(app.config, {"CF_ACCOUNT_ID": "account-1"}), \
             patch.object(cloudflare_api.cache, "get", return_value=None), \
             patch.object(cloudflare_api.cache, "set") as cache_set, \
             patch.object(cloudflare_api, "cf_api_request", side_effect=requests.exceptions.RequestException("upstream failure")):
            inventory = cloudflare_api.get_account_zone_inventory(force_refresh=True)
        self.assertEqual(inventory["status"], "unavailable")
        self.assertEqual(inventory["zones"], [])
        cache_set.assert_not_called()


if __name__ == "__main__":
    unittest.main()
