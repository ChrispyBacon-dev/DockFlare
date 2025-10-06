#!/usr/bin/env python3
import requests
import json
import sys

BASE_URL = "http://localhost:5001"
API_KEY = "APIKEY123"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def test_create_access_group():
    print("\n=== Test 1: Create Access Group ===")
    payload = {
        "group_id": "test-reusable-policy",
        "policies": [
            {
                "name": "Allow Test Users",
                "decision": "allow",
                "include": [
                    {"email": {"email": "test@example.com"}}
                ]
            }
        ],
        "session_duration": "24h",
        "app_launcher_visible": False
    }

    response = requests.post(
        f"{BASE_URL}/api/v2/access/groups",
        headers=headers,
        json=payload
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code in [200, 201]

def test_list_access_groups():
    print("\n=== Test 2: List Access Groups ===")
    response = requests.get(
        f"{BASE_URL}/api/v2/access/groups",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")

    if data.get("access_groups"):
        for group_id, group_data in data["access_groups"].items():
            if group_data.get("cloudflare_policy_id"):
                print(f"\n✓ Group '{group_id}' has Cloudflare policy ID: {group_data['cloudflare_policy_id']}")

    return response.status_code == 200

def test_create_manual_rule_with_access_group():
    print("\n=== Test 3: Create Manual Rule with Access Group ===")
    payload = {
        "hostname": "test-reusable.dockflare.app",
        "service": "http://test:8080",
        "access_groups": ["test-reusable-policy"]
    }

    response = requests.post(
        f"{BASE_URL}/api/v2/rules/manual",
        headers=headers,
        json=payload
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code in [200, 201]

def test_check_cloudflare_policy():
    print("\n=== Test 4: Check Cloudflare Policy Creation ===")
    response = requests.get(
        f"{BASE_URL}/api/v2/access/groups",
        headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        groups = data.get("access_groups", {})

        test_group = groups.get("test-reusable-policy")
        if test_group and test_group.get("cloudflare_policy_id"):
            policy_id = test_group["cloudflare_policy_id"]
            print(f"✓ Cloudflare reusable policy created: {policy_id}")
            print(f"✓ This policy can now be reused across multiple applications")
            return True
        else:
            print("✗ No Cloudflare policy ID found")
            return False

    return False

def test_feature_flag():
    print("\n=== Test 5: Check Feature Flag ===")
    response = requests.get(
        f"{BASE_URL}/api/v2/config",
        headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        use_reusable = data.get("USE_REUSABLE_POLICIES", False)
        print(f"USE_REUSABLE_POLICIES: {use_reusable}")
        return use_reusable

    return False

def main():
    print("Testing Reusable Policies Implementation")
    print("=" * 50)

    tests = [
        ("Feature Flag Check", test_feature_flag),
        ("Create Access Group", test_create_access_group),
        ("List Access Groups", test_list_access_groups),
        ("Check Cloudflare Policy", test_check_cloudflare_policy),
        ("Create Manual Rule", test_create_manual_rule_with_access_group),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with error: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
