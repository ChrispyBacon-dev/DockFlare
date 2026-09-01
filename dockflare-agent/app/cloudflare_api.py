import requests
import logging

def update_tunnel_config(master_url, api_key, tunnel_id, ingress_rules):
    """
    Updates the Cloudflare tunnel configuration for the agent.
    """
    if not all([master_url, api_key, tunnel_id]):
        logging.error("Missing master_url, api_key, or tunnel_id for tunnel config update.")
        return False

    endpoint = f"/accounts/{get_account_id(master_url, api_key)}/cfd_tunnel/{tunnel_id}/configurations"
    url = f"{master_url.rstrip('/')}{endpoint}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"config": {"ingress": ingress_rules}}

    try:
        response = requests.put(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        logging.info(f"Successfully updated tunnel config for {tunnel_id}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error updating tunnel config for {tunnel_id}: {e}")
        return False

def generate_ingress_rules(rules):
    """
    Generates ingress rules for Cloudflare tunnel from agent rules.
    """
    ingress = []
    for rule_key, rule in rules.items():
        if rule.get("status") == "active":
            entry = {"hostname": rule["hostname"], "service": rule["service"]}
            if rule.get("path"):
                entry["path"] = rule["path"]
            ingress.append(entry)
    ingress.append({"service": "http_status:404"})
    return ingress

def get_account_id(master_url, api_key):
    """
    Retrieves the Cloudflare account ID from the master.
    """
    endpoint = "/accounts"
    url = f"{master_url.rstrip('/')}{endpoint}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and data.get("result"):
            return data["result"][0]["id"]
        else:
            logging.error(f"Failed to get account ID from master: {data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error getting account ID from master: {e}")
        return None
