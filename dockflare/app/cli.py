# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev <https://github.com/ChrispyBacon-dev/DockFlare>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# dockflare/app/cli.py
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

        # Step 1: List all reusable policies
        logging.info("Step 1: Fetching all reusable policies from Cloudflare...")
        policies = reusable_policies.list_reusable_policies()

        if not policies:
            logging.info("No reusable policies found.")
            return {"total_policies": 0, "duplicates_found": 0, "policies_deleted": 0}

        logging.info(f"Found {len(policies)} total policies")
        logging.info("")

        # Step 2: Group policies by name
        logging.info("Step 2: Grouping policies by name...")
        policies_by_name = defaultdict(list)
        for policy in policies:
            policy_name = policy.get("name", "")
            policies_by_name[policy_name].append(policy)

        # Step 3: Identify duplicates
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

        # Step 4: Process each duplicate group
        logging.info("Step 4: Processing duplicates...")
        logging.info("")

        deleted_count = 0
        kept_count = 0
        state_updates = {}

        for name, dup_list in duplicates.items():
            logging.info(f"Processing: '{name}'")

            # Sort by created_at (oldest first)
            # Note: Cloudflare API returns created_at in ISO format
            sorted_policies = sorted(dup_list, key=lambda p: p.get("created_at", ""))

            # Keep the oldest one
            policy_to_keep = sorted_policies[0]
            policies_to_delete = sorted_policies[1:]

            kept_id = policy_to_keep.get("id")
            kept_created = policy_to_keep.get("created_at", "N/A")

            logging.info(f"  ✓ Keeping: ID={kept_id} (created: {kept_created})")
            kept_count += 1

            # Delete the rest
            for policy in policies_to_delete:
                policy_id = policy.get("id")
                policy_created = policy.get("created_at", "N/A")

                if dry_run:
                    logging.info(f"  ✗ Would delete: ID={policy_id} (created: {policy_created})")
                else:
                    logging.info(f"  ✗ Deleting: ID={policy_id} (created: {policy_created})")
                    success = reusable_policies.delete_reusable_policy(policy_id)
                    if success:
                        logging.info(f"    → Successfully deleted policy {policy_id}")
                        deleted_count += 1
                    else:
                        logging.error(f"    → Failed to delete policy {policy_id}")

            # Track which policy ID should be kept for this name
            state_updates[name] = kept_id
            logging.info("")

        # Step 5: Update state.json with correct policy IDs
        logging.info("Step 5: Updating state.json with correct policy IDs...")

        if dry_run:
            logging.info("DRY RUN: Would update state.json with the following changes:")

        state_updated = False
        with state_lock:
            for group_id, group_data in access_groups.items():
                policy_id = group_data.get("cloudflare_policy_id")

                if not policy_id:
                    continue

                # Check if this group references a policy that was deleted
                # by finding the policy name and checking if we kept a different ID
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
    parser = argparse.ArgumentParser(
        description="DockFlare CLI utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be cleaned up (dry run)
  python3 -m app.cli cleanup-duplicate-policies --dry-run

  # Actually perform the cleanup
  python3 -m app.cli cleanup-duplicate-policies --apply

  # Run from Docker container
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

    # Configure logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Determine mode
    if args.apply:
        dry_run = False
    else:
        dry_run = True  # Default to dry run for safety

    # Execute command
    if args.command == "cleanup-duplicate-policies":
        try:
            result = cleanup_duplicate_policies(dry_run=dry_run)
            sys.exit(0)
        except Exception as e:
            logging.error(f"Error executing cleanup: {e}", exc_info=True)
            sys.exit(1)
    else:
        logging.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
