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


def find_best_zone_for_hostname(hostname, zones):
    if not hostname or not zones:
        return None, None

    hostname_lower = hostname.lower().lstrip('.')
    if hostname_lower.startswith('*.'):
        hostname_lower = hostname_lower[2:]

    matches = []
    for zone in zones:
        zone_name = (zone.get('name') or '').lower()
        if not zone_name:
            continue
        if hostname_lower == zone_name or hostname_lower.endswith(f".{zone_name}"):
            matches.append(zone)

    if not matches:
        return None, None

    best_length = max(len(zone.get('name') or '') for zone in matches)
    best_zones = [zone for zone in matches if len(zone.get('name') or '') == best_length]
    chosen_zone = best_zones[0]
    return chosen_zone.get('id'), chosen_zone.get('name')
