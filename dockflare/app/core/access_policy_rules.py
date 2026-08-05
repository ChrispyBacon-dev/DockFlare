def build_access_policies(email_str, ip_ranges_str=None, countries_list=None, idp_list=None, idp_resolver=None, public_mode=False):
    policies = []
    email_rules = []
    ip_rules = []
    idp_rules = []

    if email_str and email_str.strip():
        for part in [value.strip() for value in email_str.split(',') if value.strip()]:
            if part.startswith('@'):
                email_rules.append({"email_domain": {"domain": part[1:]}})
            else:
                email_rules.append({"email": {"email": part}})

    requested_idps = [] if public_mode else [value.strip() for value in (idp_list or []) if value.strip()]
    unresolved_idps = []
    for friendly_name in requested_idps:
        idp_id = idp_resolver(friendly_name) if idp_resolver else None
        if idp_id:
            idp_rules.append({"login_method": {"id": idp_id}})
        else:
            unresolved_idps.append(friendly_name)

    if unresolved_idps:
        raise ValueError(f"Identity provider not found: {', '.join(unresolved_idps)}")

    if idp_rules and not email_rules and not public_mode:
        raise ValueError("When using Identity Providers, you must specify allowed email addresses to prevent unauthorized access.")

    if ip_ranges_str and ip_ranges_str.strip():
        for ip in [value.strip() for value in ip_ranges_str.split(',') if value.strip()]:
            ip_rules.append({"ip": {"ip": ip}})

    if ip_rules:
        policies.append({"name": "Bypass for defined IPs", "decision": "bypass", "include": ip_rules})

    if public_mode:
        policy = {
            "name": "Public Access (Bypass) with geo-blocking" if countries_list else "Public Access (Bypass)",
            "decision": "bypass",
            "include": [{"everyone": {}}]
        }
        if countries_list:
            policy["exclude"] = [{"geo": {"country_code": country.upper()}} for country in countries_list]
        policies.append(policy)
        return policies

    if countries_list and not email_rules and not idp_rules:
        raise ValueError(
            "Invalid configuration: You've selected geo-restrictions but no authentication method (email or identity provider). "
            "To create a public access rule with geo-restrictions, please switch to 'Public Access' mode."
        )

    allow_policies = []
    if idp_rules:
        for index, idp_rule in enumerate(idp_rules, start=1):
            allow_policies.append({
                "name": "Allow defined users" if len(idp_rules) == 1 else f"Allow defined users via IdP {index}",
                "decision": "allow",
                "include": email_rules,
                "require": [idp_rule]
            })
    elif email_rules:
        allow_policies.append({
            "name": "Allow defined users",
            "decision": "allow",
            "include": email_rules
        })

    if countries_list:
        excluded_countries = [{"geo": {"country_code": country.upper()}} for country in countries_list]
        for policy in allow_policies:
            policy["exclude"] = excluded_countries

    policies.extend(allow_policies)
    if allow_policies:
        policies.append({"name": "Default Deny", "decision": "deny", "include": [{"everyone": {}}]})
    else:
        policies.append({"name": "Default Deny (No rules defined)", "decision": "deny", "include": [{"everyone": {}}]})

    return policies


def is_default_deny_policy(policy):
    return (
        policy.get("decision") == "deny"
        and policy.get("include") == [{"everyone": {}}]
    )


def effective_access_policies(group):
    return [
        policy
        for policy in group.get("policies", [])
        if not is_default_deny_policy(policy)
    ]


def login_method_ids(policies):
    ids = []
    for policy in policies:
        for rule_type in ("include", "require"):
            for rule in policy.get(rule_type, []):
                idp_id = rule.get("login_method", {}).get("id")
                if idp_id and idp_id not in ids:
                    ids.append(idp_id)
    return ids


def normalize_managed_access_group(group):
    if group.get("external_policy"):
        return group, False

    normalized_policies = []
    changed = False
    for policy in group.get("policies", []):
        include_rules = policy.get("include", [])
        require_rules = policy.get("require", [])
        combined_rules = include_rules + require_rules
        email_rules = [
            rule for rule in combined_rules
            if "email" in rule or "email_domain" in rule
        ]
        idp_rules = [rule for rule in combined_rules if "login_method" in rule]
        supported_rules = email_rules + idp_rules

        if (
            policy.get("decision") == "allow"
            and email_rules
            and idp_rules
            and len(supported_rules) == len(combined_rules)
        ):
            for index, idp_rule in enumerate(idp_rules, start=1):
                normalized = {
                    key: value
                    for key, value in policy.items()
                    if key not in ("name", "include", "require")
                }
                normalized["name"] = "Allow defined users" if len(idp_rules) == 1 else f"Allow defined users via IdP {index}"
                normalized["include"] = email_rules
                normalized["require"] = [idp_rule]
                normalized_policies.append(normalized)
            if len(idp_rules) != 1 or include_rules != email_rules or require_rules != [idp_rules[0]]:
                changed = True
        else:
            normalized_policies.append(policy)

    normalized_group = dict(group)
    normalized_group["policies"] = normalized_policies
    normalized_group["allowed_idps"] = login_method_ids(normalized_policies)
    if normalized_policies != group.get("policies", []):
        changed = True
    if normalized_group.get("allowed_idps") != group.get("allowed_idps"):
        changed = True
    return normalized_group, changed
