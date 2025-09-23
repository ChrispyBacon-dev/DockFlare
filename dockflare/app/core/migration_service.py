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

import logging
from typing import Dict, List, Any, Optional, Tuple
from app.core.cloudflare_api import get_tunnel_configuration, parse_tunnel_rules_for_migration
from app.core.state_manager import managed_rules, state_lock, save_state
from app.core.utils import get_rule_key


class TunnelMigrationService:
    """Service for handling tunnel configuration migration when agents are assigned to existing tunnels."""

    @staticmethod
    def analyze_tunnel_for_migration(tunnel_id: str, agent_containers: List[Dict]) -> Dict[str, Any]:
        """
        Analyze an existing tunnel configuration for migration opportunities.

        Args:
            tunnel_id: The tunnel ID to analyze
            agent_containers: List of containers reported by the agent

        Returns:
            Dictionary containing migration analysis results
        """
        logging.info(f"Analyzing tunnel {tunnel_id} for migration opportunities")
        
        tunnel_config = get_tunnel_configuration(tunnel_id)
        if not tunnel_config:
            return {
                "tunnel_id": tunnel_id,
                "existing_rules": [],
                "agent_containers": agent_containers,
                "auto_import": [],
                "conflicts": [],
                "orphaned": [],
                "new_containers": []
            }

        tunnel_rules = parse_tunnel_rules_for_migration(tunnel_config)

        container_lookup = {}
        for container in agent_containers:
            labels = container.get("labels", {})
            if labels.get("dockflare.enable") == "true":
                hostname = labels.get("dockflare.hostname")
                if hostname:
                    container_lookup[hostname] = container

        auto_import = []
        conflicts = []
        orphaned = []

        for rule in tunnel_rules:
            rule_hostname = rule["hostname"]

            matching_container = container_lookup.get(rule_hostname)

            if matching_container:

                container_service = TunnelMigrationService._extract_service_from_container(matching_container)
                if container_service and container_service != rule["service"]:
                    conflicts.append({
                        "rule": rule,
                        "container": matching_container,
                        "conflict_type": "service_url",
                        "tunnel_service": rule["service"],
                        "container_service": container_service
                    })
                else:

                    rule["container_id"] = matching_container["id"]
                    rule["source"] = "docker"
                    auto_import.append(rule)
            else:

                orphaned.append(rule)

        new_containers = []
        for container in agent_containers:
            labels = container.get("labels", {})
            hostname = labels.get("dockflare.hostname")
            if hostname and hostname not in [r["hostname"] for r in tunnel_rules]:
                new_containers.append(container)

        result = {
            "tunnel_id": tunnel_id,
            "existing_rules": tunnel_rules,
            "agent_containers": agent_containers,
            "auto_import": auto_import,
            "conflicts": conflicts,
            "orphaned": orphaned,
            "new_containers": new_containers
        }

        logging.info(f"Migration analysis complete: {len(auto_import)} auto-import, {len(conflicts)} conflicts, {len(orphaned)} orphaned, {len(new_containers)} new")
        return result

    @staticmethod
    def execute_auto_import(migration_analysis: Dict[str, Any]) -> Tuple[int, List[str]]:
        """
        Execute the auto-import phase of migration.

        Args:
            migration_analysis: Results from analyze_tunnel_for_migration

        Returns:
            Tuple of (imported_count, error_messages)
        """
        auto_import_rules = migration_analysis.get("auto_import", [])
        if not auto_import_rules:
            return 0, []

        imported_count = 0
        errors = []

        with state_lock:
            for rule in auto_import_rules:
                try:
                    rule_key = get_rule_key(rule["hostname"], rule["path"])
                    
                    if rule_key in managed_rules:
                        logging.info(f"Rule {rule_key} already exists in master state, skipping auto-import")
                        continue
                    
                    managed_rules[rule_key] = rule
                    imported_count += 1
                    logging.info(f"Auto-imported rule: {rule_key}")

                except Exception as e:
                    error_msg = f"Failed to import rule {rule.get('hostname', 'unknown')}: {e}"
                    errors.append(error_msg)
                    logging.error(error_msg)

            if imported_count > 0:
                save_state()

        logging.info(f"Auto-import completed: {imported_count} rules imported, {len(errors)} errors")
        return imported_count, errors

    @staticmethod
    def _extract_service_from_container(container: Dict) -> Optional[str]:
        """Extract the service URL from a container's DockFlare labels."""
        labels = container.get("labels", {})

        # Check for explicit service label
        service = labels.get("dockflare.service")
        if service:
            return service

        # Try to construct from individual components
        port = labels.get("dockflare.port")
        if not port:
            return None

        protocol = labels.get("dockflare.protocol", "http")
        container_name = container.get("name", "").lstrip("/")

        if container_name:
            return f"{protocol}://{container_name}:{port}"

        return None

    @staticmethod
    def get_migration_status(agent_id: str) -> Optional[Dict]:
        """
        Get the current migration status for an agent.
        This would be stored in agent metadata.
        """
        from app.core.state_manager import get_agent

        agent = get_agent(agent_id)
        if not agent:
            return None

        return agent.get("migration_status")

    @staticmethod
    def set_migration_status(agent_id: str, status: Dict) -> bool:
        """
        Set the migration status for an agent.
        """
        from app.core.state_manager import update_agent

        return update_agent(agent_id, {"migration_status": status})

    @staticmethod
    def trigger_migration_analysis(agent_id: str, tunnel_id: str, agent_containers: List[Dict]) -> Dict:
        """
        Trigger migration analysis and auto-import for an agent.

        Args:
            agent_id: The agent ID
            tunnel_id: The tunnel ID the agent is assigned to
            agent_containers: List of containers from agent

        Returns:
            Migration results including what was auto-imported and any conflicts
        """
        try:
            
            analysis = TunnelMigrationService.analyze_tunnel_for_migration(tunnel_id, agent_containers)

            
            imported_count, errors = TunnelMigrationService.execute_auto_import(analysis)

            
            migration_status = {
                "last_analysis": analysis,
                "auto_imported": imported_count,
                "has_conflicts": len(analysis.get("conflicts", [])) > 0,
                "has_orphaned": len(analysis.get("orphaned", [])) > 0,
                "errors": errors,
                "completed_at": None if (analysis.get("conflicts") or analysis.get("orphaned")) else True
            }

            TunnelMigrationService.set_migration_status(agent_id, migration_status)

            return {
                "success": True,
                "imported_count": imported_count,
                "conflicts": analysis.get("conflicts", []),
                "orphaned": analysis.get("orphaned", []),
                "errors": errors
            }

        except Exception as e:
            logging.error(f"Error during migration analysis for agent {agent_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "imported_count": 0,
                "conflicts": [],
                "orphaned": [],
                "errors": [str(e)]
            }