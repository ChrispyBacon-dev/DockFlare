"""
DockFlare CLI utilities for maintenance and troubleshooting.
"""
import argparse
import sys
import logging
from collections import defaultdict
from datetime import datetime

def cleanup_duplicate_policies(dry_run=True):
    """
    Scan for duplicate reusable policies (same name) and consolidate them.
    Keeps the oldest policy, deletes newer duplicates.
    Updates state.json to reference the correct policy IDs.

    Args:
        dry_run: If True, only show what would be done. If False, execute deletions.

    Returns:
        dict: Summary of actions taken
    """
    from app import app
    from app.core import reusable_policies
    from app.core.state_manager import access_groups, save_state, state_lock
    from app.web import config_loader

    config_data = config_loader.load_encrypted_config()
    if not config_data:
        logging.error("Failed to load DockFlare configuration. Ensure the application is configured.")
        logging.error("Run the web UI setup first: docker exec dockflare python -m app.main")
        return {"error": "Configuration not found"}

    config_loader.apply_config_to_app(app, config_data)

    with app.app_context():
        logging.info("=" * 60)
        logging.info("DUPLICATE POLICY CLEANUP UTILITY")
        logging.info("=" * 60)
        logging.info(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'APPLY (changes will be executed)'}")
        logging.info("")

        logging.info("Step 1: Fetching all reusable policies from Cloudflare...")
        policies = reusable_policies.list_reusable_policies()

        if not policies:
            logging.info("No reusable policies found.")
            return {"total_policies": 0, "duplicates_found": 0, "policies_deleted": 0}

        logging.info(f"Found {len(policies)} total policies")
        logging.info("")

        logging.info("Step 2: Grouping policies by name...")
        policies_by_name = defaultdict(list)
        for policy in policies:
            policy_name = policy.get("name", "")
            policies_by_name[policy_name].append(policy)

        logging.info("Step 3: Identifying duplicates...")
        duplicates = {name: policies_list for name, policies_list in policies_by_name.items() if len(policies_list) > 1}

        if not duplicates:
            logging.info("✓ No duplicate policies found. All policies have unique names.")
            return {"total_policies": len(policies), "duplicates_found": 0, "policies_deleted": 0}

        logging.info(f"✗ Found {len(duplicates)} policy names with duplicates:")
        logging.info("")

        total_to_delete = 0
        for name, dup_list in duplicates.items():
            logging.info(f"  Policy: '{name}' ({len(dup_list)} instances)")
            total_to_delete += len(dup_list) - 1

        logging.info("")
        logging.info(f"Total policies to delete: {total_to_delete}")
        logging.info("")

        logging.info("Step 4: Checking Access Applications for policy usage...")
        from app.core import cloudflare_api
        from flask import current_app

        account_id = current_app.config.get('CF_ACCOUNT_ID')
        endpoint = f"/accounts/{account_id}/access/apps"

        try:
            all_apps_response = cloudflare_api.cf_api_request("GET", endpoint, params={"per_page": 100})
            all_apps = all_apps_response.get("result", [])
            logging.info(f"Found {len(all_apps)} Access Applications to check")
        except Exception as e:
            logging.error(f"Failed to list Access Applications: {e}")
            all_apps = []

        logging.info("")

        logging.info("Step 5: Processing duplicates...")
        logging.info("")

        deleted_count = 0
        kept_count = 0
        state_updates = {}
        app_updates_needed = {}

        for name, dup_list in duplicates.items():
            logging.info(f"Processing: '{name}'")

            sorted_policies = sorted(dup_list, key=lambda p: p.get("created_at", ""))

            policy_to_keep = sorted_policies[0]
            policies_to_delete = sorted_policies[1:]

            kept_id = policy_to_keep.get("id")
            kept_created = policy_to_keep.get("created_at", "N/A")

            logging.info(f"  ✓ Keeping: ID={kept_id} (created: {kept_created})")
            kept_count += 1

            policy_ids_to_delete = [p.get("id") for p in policies_to_delete]
            apps_using_duplicates = []

            for app in all_apps:
                app_policies = app.get("policies", [])

                for policy_id in policy_ids_to_delete:
                    found = False

                    if isinstance(app_policies, list):
                        for policy in app_policies:
                            if isinstance(policy, str):
                                if policy == policy_id:
                                    found = True
                                    break
                            elif isinstance(policy, dict):
                                if policy.get("id") == policy_id:
                                    found = True
                                    break

                    if found:
                        apps_using_duplicates.append({
                            "app_id": app.get("id"),
                            "app_name": app.get("name"),
                            "app_domain": app.get("domain"),
                            "old_policy_id": policy_id,
                            "all_policies": app_policies
                        })
                        break

            if apps_using_duplicates:
                logging.info(f"  ⚠ Found {len(apps_using_duplicates)} Access Application(s) using duplicate policies:")
                for app_info in apps_using_duplicates:
                    logging.info(f"    - App: '{app_info['app_name']}' (domain: {app_info['app_domain']})")
                    logging.info(f"      Using policy: {app_info['old_policy_id']}")

                if not dry_run:
                    logging.info(f"  📝 Updating applications to use kept policy ID {kept_id}...")
                    from app.core import access_manager
                    for app_info in apps_using_duplicates:
                        app_id = app_info["app_id"]
                        app_name = app_info["app_name"]
                        old_policy_id = app_info["old_policy_id"]
                        all_policies = app_info["all_policies"]

                        updated_policies = []
                        for policy in all_policies:
                            if isinstance(policy, str):
                                updated_policies.append(kept_id if policy == old_policy_id else policy)
                            elif isinstance(policy, dict):
                                if policy.get("id") == old_policy_id:
                                    updated_policies.append(kept_id)
                                else:
                                    updated_policies.append(policy.get("id") if policy.get("id") else policy)
                            else:
                                updated_policies.append(policy)

                        try:
                            app_details = access_manager.get_cloudflare_access_application(app_id)
                            if app_details:
                                success = access_manager.update_cloudflare_access_application(
                                    app_id,
                                    app_details.get("domain"),
                                    app_details.get("name"),
                                    app_details.get("session_duration", "24h"),
                                    app_details.get("app_launcher_visible", False),
                                    app_details.get("self_hosted_domains", []),
                                    updated_policies,
                                    app_details.get("allowed_idps"),
                                    app_details.get("auto_redirect_to_identity", False),
                                    use_reusable=True
                                )
                                if success:
                                    logging.info(f"    ✓ Updated app '{app_name}': {old_policy_id} → {kept_id}")
                                else:
                                    logging.error(f"    ✗ Failed to update app '{app_name}'")
                            else:
                                logging.error(f"    ✗ Could not fetch details for app '{app_name}'")
                        except Exception as e:
                            logging.error(f"    ✗ Error updating app '{app_name}': {e}")
                    logging.info("")

            for policy in policies_to_delete:
                policy_id = policy.get("id")
                policy_created = policy.get("created_at", "N/A")

                if dry_run:
                    logging.info(f"  ✗ Would delete: ID={policy_id} (created: {policy_created})")
                else:
                    logging.info(f"  ✗ Deleting: ID={policy_id} (created: {policy_created})")
                    try:
                        success = reusable_policies.delete_reusable_policy(policy_id)
                        if success:
                            logging.info(f"    → Successfully deleted policy {policy_id}")
                            deleted_count += 1
                        else:
                            logging.error(f"    → Failed to delete policy {policy_id}")
                    except Exception as e:
                        error_msg = str(e)
                        if "409" in error_msg or "conflict" in error_msg.lower():
                            logging.error(f"    → Policy {policy_id} is still in use by applications")
                            logging.error(f"    → Detection may have missed some apps - please check Cloudflare dashboard")
                        else:
                            logging.error(f"    → Failed to delete policy {policy_id}: {e}")

            state_updates[name] = kept_id
            if apps_using_duplicates:
                app_updates_needed[name] = {
                    "kept_id": kept_id,
                    "apps": apps_using_duplicates
                }

            logging.info("")

        logging.info("Step 6: Updating state.json with correct policy IDs...")

        if dry_run:
            logging.info("DRY RUN: Would update state.json with the following changes:")

        state_updated = False
        with state_lock:
            for group_id, group_data in access_groups.items():
                policy_id = group_data.get("cloudflare_policy_id")

                if not policy_id:
                    continue

                current_policy_name = None
                for name, policies_list in policies_by_name.items():
                    for policy in policies_list:
                        if policy.get("id") == policy_id:
                            current_policy_name = name
                            break
                    if current_policy_name:
                        break

                if current_policy_name and current_policy_name in state_updates:
                    correct_id = state_updates[current_policy_name]
                    if policy_id != correct_id:
                        if dry_run:
                            logging.info(f"  Group '{group_id}': {policy_id} → {correct_id} (policy: {current_policy_name})")
                        else:
                            logging.info(f"  Updating group '{group_id}': {policy_id} → {correct_id}")
                            access_groups[group_id]["cloudflare_policy_id"] = correct_id
                            state_updated = True

        if state_updated and not dry_run:
            save_state()
            logging.info("✓ state.json updated successfully")
        elif not state_updated:
            logging.info("✓ No state.json updates needed")

        logging.info("")
        logging.info("=" * 60)
        logging.info("SUMMARY")
        logging.info("=" * 60)
        logging.info(f"Total policies scanned: {len(policies)}")
        logging.info(f"Duplicate policy names found: {len(duplicates)}")
        if dry_run:
            logging.info(f"Policies that would be deleted: {total_to_delete}")
            logging.info(f"Policies that would be kept: {kept_count}")
        else:
            logging.info(f"Policies deleted: {deleted_count}")
            logging.info(f"Policies kept: {kept_count}")
            logging.info(f"State updates applied: {state_updated}")
        logging.info("=" * 60)

        return {
            "total_policies": len(policies),
            "duplicates_found": len(duplicates),
            "policies_deleted": deleted_count if not dry_run else 0,
            "policies_kept": kept_count,
            "would_delete": total_to_delete if dry_run else 0
        }


def main():
    """CLI entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True
    )

    parser = argparse.ArgumentParser(
        description="DockFlare CLI utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m app.cli cleanup-duplicate-policies --dry-run
  python3 -m app.cli cleanup-duplicate-policies --apply
  docker exec dockflare python3 -m app.cli cleanup-duplicate-policies --dry-run
"""
    )

    parser.add_argument(
        "command",
        choices=["cleanup-duplicate-policies"],
        help="Command to execute"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing them (default)"
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute the cleanup (deletes duplicate policies)"
    )

    args = parser.parse_args()

    if args.apply:
        dry_run = False
    else:
        dry_run = True

    if args.command == "cleanup-duplicate-policies":
        try:
            logging.info("Starting cleanup utility...")
            result = cleanup_duplicate_policies(dry_run=dry_run)
            if result and "error" in result:
                logging.error(f"Cleanup failed: {result['error']}")
                sys.exit(1)
            logging.info("Cleanup utility completed successfully.")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Error executing cleanup: {e}", exc_info=True)
            sys.exit(1)
    else:
        logging.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
