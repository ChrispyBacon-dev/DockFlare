class ZoneResolutionError(ValueError):
    def __init__(self, code, candidates=None):
        super().__init__(code)
        self.code = code
        self.candidates = candidates or []


def normalize_dns_name(value, allow_wildcard=True):
    if not isinstance(value, str):
        raise ZoneResolutionError("hostname_invalid")
    normalized = value.strip().rstrip(".")
    if allow_wildcard and normalized.startswith("*."):
        normalized = normalized[2:]
    if not normalized or len(normalized) > 253:
        raise ZoneResolutionError("hostname_invalid")
    labels = normalized.split(".")
    if any(not label for label in labels):
        raise ZoneResolutionError("hostname_invalid")
    try:
        ascii_labels = [label.encode("idna").decode("ascii").lower() for label in labels]
    except (UnicodeError, UnicodeDecodeError):
        raise ZoneResolutionError("hostname_invalid")
    if len(".".join(ascii_labels)) > 253 or any(
        len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or any(not (character.isalnum() or character == "-") for character in label)
        for label in ascii_labels
    ):
        raise ZoneResolutionError("hostname_invalid")
    return ".".join(ascii_labels)


def normalize_zones(zones):
    normalized = []
    for zone in zones or []:
        if not isinstance(zone, dict) or not zone.get("id") or not zone.get("name"):
            continue
        try:
            name = normalize_dns_name(zone["name"], allow_wildcard=False)
        except ZoneResolutionError:
            continue
        normalized.append({"id": str(zone["id"]), "name": name})
    return normalized


def _unique_candidate(candidates):
    unique = {(zone["id"], zone["name"]): zone for zone in candidates}
    values = list(unique.values())
    if len(values) != 1:
        raise ZoneResolutionError("explicit_zone_conflict", values)
    return values[0]


def hostname_in_zone(hostname, zone_name):
    host = normalize_dns_name(hostname)
    zone = normalize_dns_name(zone_name, allow_wildcard=False)
    return host == zone or host.endswith("." + zone)


def match_zone_for_hostname(hostname, zones):
    host = normalize_dns_name(hostname)
    candidates = [zone for zone in normalize_zones(zones) if host == zone["name"] or host.endswith("." + zone["name"])]
    if not candidates:
        return None
    longest = max(len(zone["name"].split(".")) for zone in candidates)
    best = [zone for zone in candidates if len(zone["name"].split(".")) == longest]
    return _unique_candidate(best)


def select_explicit_zone(zones, zone_id=None, zone_name=None):
    normalized = normalize_zones(zones)
    requested_name = normalize_dns_name(zone_name, allow_wildcard=False) if zone_name else None
    by_id = [zone for zone in normalized if zone_id and zone["id"] == str(zone_id)]
    by_name = [zone for zone in normalized if requested_name and zone["name"] == requested_name]
    if zone_id and not by_id:
        raise ZoneResolutionError("explicit_zone_not_found")
    if requested_name and not by_name:
        raise ZoneResolutionError("explicit_zone_not_found")
    if zone_id and requested_name:
        candidate = _unique_candidate(by_id)
        if candidate not in by_name:
            raise ZoneResolutionError("explicit_zone_conflict", by_id + by_name)
        return candidate
    return _unique_candidate(by_id or by_name)


def resolve_zone(hostname, zones, explicit_zone_id=None, explicit_zone_name=None, default_zone_id=None, inventory_status="complete", allow_unverified_default=False):
    host = normalize_dns_name(hostname)
    usable_inventory = inventory_status in {"complete", "cached", "stale"}
    if explicit_zone_id or explicit_zone_name:
        if not usable_inventory:
            raise ZoneResolutionError("inventory_unavailable")
        selected = select_explicit_zone(zones, explicit_zone_id, explicit_zone_name)
        if not hostname_in_zone(host, selected["name"]):
            raise ZoneResolutionError("explicit_zone_conflict", [selected])
        source = "explicit_id" if explicit_zone_id else "explicit_name"
        return {**selected, "source": source, "inventory_status": inventory_status, "verified": True}
    if usable_inventory:
        selected = match_zone_for_hostname(host, zones)
        if selected:
            return {**selected, "source": "hostname", "inventory_status": inventory_status, "verified": True}
        if default_zone_id:
            defaults = [zone for zone in normalize_zones(zones) if zone["id"] == str(default_zone_id)]
            if not defaults:
                raise ZoneResolutionError("default_zone_not_found")
            if not hostname_in_zone(host, defaults[0]["name"]):
                raise ZoneResolutionError("default_zone_mismatch", defaults)
        raise ZoneResolutionError("zone_not_found", normalize_zones(zones))
    if allow_unverified_default and default_zone_id:
        return {"id": str(default_zone_id), "name": None, "source": "default_unverified", "inventory_status": inventory_status, "verified": False}
    raise ZoneResolutionError("inventory_unavailable")
