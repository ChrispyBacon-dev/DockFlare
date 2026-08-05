import importlib.util
import pathlib
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "app" / "core" / "access_policy_rules.py"
SPEC = importlib.util.spec_from_file_location("access_policy_rules", MODULE_PATH)
RULES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RULES)


class AccessPolicyRuleTests(unittest.TestCase):
    def setUp(self):
        self.idps = {
            "google": "google-id",
            "github": "github-id"
        }

    def resolve_idp(self, name):
        return self.idps.get(name)

    def test_multiple_emails_are_or_within_selected_idp(self):
        policies = RULES.build_access_policies(
            "alice@gmail.com, bob@gmail.com, @example.com",
            idp_list=["google"],
            idp_resolver=self.resolve_idp
        )

        self.assertEqual(policies[0]["include"], [
            {"email": {"email": "alice@gmail.com"}},
            {"email": {"email": "bob@gmail.com"}},
            {"email_domain": {"domain": "example.com"}}
        ])
        self.assertEqual(policies[0]["require"], [
            {"login_method": {"id": "google-id"}}
        ])
        self.assertEqual(policies[1]["decision"], "deny")

    def test_multiple_idps_create_alternative_allow_policies(self):
        policies = RULES.build_access_policies(
            "alice@example.com, bob@example.com",
            idp_list=["google", "github"],
            idp_resolver=self.resolve_idp
        )

        allow_policies = [policy for policy in policies if policy["decision"] == "allow"]
        self.assertEqual(len(allow_policies), 2)
        self.assertEqual(allow_policies[0]["include"], allow_policies[1]["include"])
        self.assertEqual(allow_policies[0]["require"], [{"login_method": {"id": "google-id"}}])
        self.assertEqual(allow_policies[1]["require"], [{"login_method": {"id": "github-id"}}])

    def test_missing_idp_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            RULES.build_access_policies(
                "alice@example.com",
                idp_list=["google", "missing"],
                idp_resolver=self.resolve_idp
            )

    def test_idp_without_email_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "allowed email"):
            RULES.build_access_policies(
                "",
                idp_list=["google"],
                idp_resolver=self.resolve_idp
            )

    def test_ip_bypass_and_authentication_remain_separate(self):
        policies = RULES.build_access_policies(
            "alice@example.com",
            ip_ranges_str="192.0.2.0/24",
            idp_list=["google"],
            idp_resolver=self.resolve_idp
        )

        effective = RULES.effective_access_policies({"policies": policies})
        self.assertEqual([policy["decision"] for policy in effective], ["bypass", "allow"])

    def test_login_method_ids_reads_include_and_require(self):
        policies = [
            {
                "include": [{"login_method": {"id": "legacy-id"}}],
                "require": [{"login_method": {"id": "required-id"}}]
            }
        ]

        self.assertEqual(RULES.login_method_ids(policies), ["legacy-id", "required-id"])

    def test_legacy_or_policy_is_migrated(self):
        group = {
            "policies": [
                {
                    "name": "Allow defined users",
                    "decision": "allow",
                    "include": [
                        {"email": {"email": "alice@example.com"}},
                        {"email": {"email": "bob@example.com"}},
                        {"login_method": {"id": "google-id"}}
                    ]
                },
                {"name": "Default Deny", "decision": "deny", "include": [{"everyone": {}}]}
            ]
        }

        normalized, changed = RULES.normalize_managed_access_group(group)

        self.assertTrue(changed)
        self.assertEqual(normalized["policies"][0]["include"], [
            {"email": {"email": "alice@example.com"}},
            {"email": {"email": "bob@example.com"}}
        ])
        self.assertEqual(normalized["policies"][0]["require"], [
            {"login_method": {"id": "google-id"}}
        ])

    def test_inverted_require_policy_is_migrated(self):
        group = {
            "policies": [
                {
                    "name": "Allow defined users",
                    "decision": "allow",
                    "include": [{"login_method": {"id": "google-id"}}],
                    "require": [
                        {"email": {"email": "alice@example.com"}},
                        {"email": {"email": "bob@example.com"}}
                    ]
                }
            ]
        }

        normalized, changed = RULES.normalize_managed_access_group(group)

        self.assertTrue(changed)
        self.assertEqual(normalized["policies"][0]["include"], [
            {"email": {"email": "alice@example.com"}},
            {"email": {"email": "bob@example.com"}}
        ])
        self.assertEqual(normalized["policies"][0]["require"], [
            {"login_method": {"id": "google-id"}}
        ])


if __name__ == "__main__":
    unittest.main()
