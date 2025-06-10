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
# app/core/cloudflare_api.py
import copy
import logging
import requests
import json
import time
import threading
from app import config

zone_id_cache = {}  
zone_details_by_id_cache = {}  
_cached_account_email = None
_cached_account_email_timestamp = 0
_cache_lock = threading.Lock()

dns_semaphore = threading.Semaphore(config.MAX_CONCURRENT_DNS_OPS)


def cf_api_request(method, endpoint, json_data=None, params=None):

    url = f"{config.CF_API_BASE_URL}{endpoint}"
    error_msg = None
    try:
        logging.info(f"CF API Request: {method} {url} Params: {params}")
        if json_data:

            try:
                log_data = json.dumps(json_data)
            except TypeError:
                log_data = str(json_data) 
            logging.debug(f"CF API Request Data: {log_data[:500]}")
            
        response = requests.request(
            method,
            url,
            headers=config.CF_HEADERS,
            json=json_data,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        logging.info(f"CF API Response Status: {response.status_code}")

        if response.status_code == 204 or not response.content:
            return {"success": True, "result": None}
        
        try:
            response_data = response.json()
            logging.debug(f"CF API Response Body (first 500 chars): {str(response_data)[:500]}")
            
            if isinstance(response_data, dict) and 'success' in response_data:
                if response_data['success']:
                    return response_data
                else:
                    cf_errors = response_data.get('errors', [])
                    error_code = None
                    if cf_errors and isinstance(cf_errors, list) and len(cf_errors) > 0 and isinstance(cf_errors[0], dict):
                        error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown error')}"
                        error_code = cf_errors[0].get('code')
                    else:
                        error_msg = f"API reported failure but no error details provided. Response: {response_data}"
                    logging.error(f"CF API Request Failed ({method} {url}): {error_msg} - Full Errors: {cf_errors}")
                    api_exception = requests.exceptions.RequestException(error_msg, response=response)
                    api_exception.cf_error_code = error_code 
                    raise api_exception
            else:
                logging.warning(f"CF API response for {method} {url} was valid JSON but missing 'success' field. Status: {response.status_code}. Body: {str(response_data)[:200]}")
                raise requests.exceptions.RequestException(f"Unexpected JSON response format from API. Status: {response.status_code}", response=response)

        except json.JSONDecodeError:
            logging.error(f"CF API response for {method} {url} was not valid JSON. Status: {response.status_code}. Body: {response.text[:200]}")
            raise requests.exceptions.RequestException(f"Invalid JSON response from API. Status: {response.status_code}", response=response)
            
    except requests.exceptions.RequestException as e:
        if error_msg is None:
            log_error_msg = f"CF API Request Failed: {method} {url}. Original Exception: {e}"
            error_msg_for_exception = f"Request Exception: {e}"

            if e.response is not None:
                try:
                    error_data = e.response.json()
                    cf_errors = error_data.get('errors', [])
                    if cf_errors and isinstance(cf_errors, list) and len(cf_errors) > 0 and isinstance(cf_errors[0], dict):
                        error_msg_for_exception = f"API Error: {cf_errors[0].get('message', 'Unknown error')}"
                        if not hasattr(e, 'cf_error_code'):
                             e.cf_error_code = cf_errors[0].get('code')
                        log_error_msg += f" - API Details: {cf_errors[0].get('message', 'Unknown error')}"
                    else:
                        error_msg_for_exception = f"HTTP {e.response.status_code} - {e.response.text[:100]}"
                        log_error_msg += f" - HTTP {e.response.status_code} - Response Text (first 100): {e.response.text[:100]}"
                    logging.error(f"CF API Error Response Body: {error_data}")
                except (ValueError, AttributeError, json.JSONDecodeError):
                    error_msg_for_exception = f"HTTP {e.response.status_code} - {e.response.text[:100]}"
                    log_error_msg += f" - HTTP {e.response.status_code} - Response Text (first 100): {e.response.text[:100]}"
            logging.error(log_error_msg)
        raise

def get_zone_id_from_name(zone_name):
 
    global zone_id_cache
    if not zone_name:
        logging.warning("get_zone_id_from_name called with empty zone_name.")
        return None
    
    cache_ttl = config.ACCOUNT_EMAIL_CACHE_TTL
    current_time = time.time()

    with _cache_lock:
        cached_data = zone_id_cache.get(zone_name)
        if cached_data:
            zone_id, timestamp = cached_data
            if current_time - timestamp < cache_ttl:
                logging.debug(f"Zone ID for '{zone_name}' found in cache: {zone_id}")
                return zone_id
            else:
                logging.debug(f"Cached Zone ID for '{zone_name}' expired, refreshing.")
    
    logging.info(f"Zone ID for '{zone_name}' not in cache or expired. Querying Cloudflare API...")
    endpoint = "/zones"
    params = {"name": zone_name, "status": "active", "account.id": config.CF_ACCOUNT_ID}
    try:
        response_data = cf_api_request("GET", endpoint, params=params)
        results = response_data.get("result", [])

        if results and isinstance(results, list) and len(results) == 1:
            zone_id = results[0].get("id")
            zone_actual_name = results[0].get("name")
            if zone_id and zone_actual_name == zone_name:
                logging.info(f"Found Zone ID for '{zone_name}': {zone_id}")
                with _cache_lock:
                    zone_id_cache[zone_name] = (zone_id, current_time)
                return zone_id
            else:
                logging.error(f"API returned unexpected result or name mismatch for zone '{zone_name}': {results[0]}")
                return None
        elif results and len(results) > 1:
            logging.error(f"API returned multiple ({len(results)}) active zones matching name '{zone_name}' for account {config.CF_ACCOUNT_ID}. Cannot determine correct zone.")
            return None
        else:
            logging.warning(f"No active zone found matching name '{zone_name}' for account {config.CF_ACCOUNT_ID} via API.")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error looking up zone '{zone_name}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error looking up zone '{zone_name}': {e}", exc_info=True)
        return None

def get_zone_details_by_id(zone_id_to_check): 

    global zone_details_by_id_cache
    if not zone_id_to_check:
        logging.warning("get_zone_details_by_id called with empty zone_id.")
        return None

    with _cache_lock:
        if zone_id_to_check in zone_details_by_id_cache:
            logging.debug(f"Zone details for ID '{zone_id_to_check}' found in cache.")
            return zone_details_by_id_cache[zone_id_to_check]

    logging.info(f"Zone details for ID '{zone_id_to_check}' not in cache. Querying Cloudflare API...")
    endpoint = f"/zones/{zone_id_to_check}"
    try:
        response_data = cf_api_request("GET", endpoint)
        if response_data and response_data.get("success"):
            zone_data = response_data.get("result")
            if zone_data and isinstance(zone_data, dict) and zone_data.get("name"):
                logging.info(f"Found zone details for ID '{zone_id_to_check}': Name '{zone_data['name']}'")
                with _cache_lock:
                    zone_details_by_id_cache[zone_id_to_check] = zone_data
                return zone_data
            else:
                logging.error(f"API returned success for zone ID '{zone_id_to_check}' but result is missing or malformed: {zone_data}")
                return None
        else:
            logging.error(f"API call failed or returned success=false for zone ID '{zone_id_to_check}': {response_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error looking up zone ID '{zone_id_to_check}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error looking up zone ID '{zone_id_to_check}': {e}", exc_info=True)
        return None

def find_tunnel_via_api(name):
    logging.info(f"Finding tunnel '{name}' via API on account {config.CF_ACCOUNT_ID}")
    endpoint = f"/accounts/{config.CF_ACCOUNT_ID}/cfd_tunnel"
    params = {"name": name, "is_deleted": "false"}
    try:
        response_data = cf_api_request("GET", endpoint, params=params)
        tunnels = response_data.get("result", [])
        if tunnels and isinstance(tunnels, list):
            for tunnel_entry in tunnels:
                if tunnel_entry.get("name") == name:
                    tunnel_id = tunnel_entry.get("id")
                    if tunnel_id:
                        logging.info(f"Found existing tunnel '{name}' ID: {tunnel_id}. Getting token...")
                        token = get_tunnel_token_via_api(tunnel_id)
                        return tunnel_id, token
                    else:
                        logging.warning(f"Found tunnel entry for '{name}' but it has no ID: {tunnel_entry}")
                        return None, None
            logging.info(f"Tunnel '{name}' not found among listed tunnels.")
            return None, None
        else:
            logging.info(f"Tunnel '{name}' not found via API (no results array or empty).")
            return None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error finding tunnel '{name}': {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error finding tunnel '{name}': {e}", exc_info=True)
        raise

def get_tunnel_token_via_api(tunnel_id):
    logging.info(f"Getting token for tunnel ID '{tunnel_id}' on account {config.CF_ACCOUNT_ID}")
    endpoint = f"/accounts/{config.CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_id}/token"
    url = f"{config.CF_API_BASE_URL}{endpoint}"
    token = None
    try:
        logging.info(f"API Request: GET {url} (for token, raw request)")
        response = requests.request("GET", url, headers={"Authorization": f"Bearer {config.CF_API_TOKEN}"}, timeout=30)
        response.raise_for_status()
        try:
            token = response.json().get("result")
            logging.info("Successfully parsed tunnel token from JSON response.")
        except json.JSONDecodeError:
            # If JSON parsing fails, it's the legacy raw text response. Bugfix for Issue 83
            logging.info("Could not parse response as JSON, falling back to raw text for token.")
            token = response.text.strip()
        if not token or len(token) < 50:
            logging.error(f"Retrieved token for tunnel {tunnel_id} appears invalid (too short or empty). Value: '{token}'")
            raise ValueError("Invalid token format or content received from API")
        
        logging.info(f"Successfully retrieved and validated token for tunnel {tunnel_id}")
        return token

    except requests.exceptions.RequestException as e:
        error_msg = f"API Error getting token for tunnel {tunnel_id}: {e}"
        if e.response is not None:
            error_msg += f" Status: {e.response.status_code} Body (first 100): {e.response.text[:100]}"
        logging.error(error_msg)
        raise
    except Exception as e:
        logging.error(f"Unexpected error getting tunnel token for {tunnel_id}: {e}", exc_info=True)
        raise

def create_tunnel_via_api(name):
    logging.info(f"Creating tunnel '{name}' via API on account {config.CF_ACCOUNT_ID}")
    endpoint = f"/accounts/{config.CF_ACCOUNT_ID}/cfd_tunnel"
    payload = {"name": name, "config_src": "cloudflare"}
    try:
        response_data = cf_api_request("POST", endpoint, json_data=payload)
        result = response_data.get("result", {})
        tunnel_id = result.get("id")
        token = result.get("token")
        if not tunnel_id or not token:
            logging.error(f"API response for tunnel creation missing ID or Token: {result}")
            raise ValueError("Missing ID or Token in API response for tunnel creation")
        logging.info(f"Successfully created tunnel '{name}' with ID {tunnel_id}.")
        return tunnel_id, token
    except requests.exceptions.RequestException as e:
        logging.error(f"API error creating tunnel '{name}': {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error creating tunnel '{name}': {e}", exc_info=True)
        raise

def create_cloudflare_dns_record(zone_id, hostname, tunnel_id):
    acquired = False
    try:
        acquired = dns_semaphore.acquire(timeout=30)
        if not acquired:
            logging.error(f"Timed out waiting for DNS semaphore - too many concurrent operations. Skipping DNS creation for {hostname}")
            return "semaphore_timeout"
            
        if not zone_id or not hostname or not tunnel_id:
            logging.error("create_cloudflare_dns_record: Missing required arguments zone_id, hostname, or tunnel_id.")
            return None

        existing_record_id, correct_tunnel = find_dns_record_id(zone_id, hostname, tunnel_id)
        
        if existing_record_id:
            if correct_tunnel:
                logging.info(f"DNS record for {hostname} in zone {zone_id} already exists with ID {existing_record_id} and correct tunnel. Using existing record.")
                return existing_record_id
            else:
                logging.warning(f"DNS record for {hostname} in zone {zone_id} exists (ID: {existing_record_id}) but points to wrong tunnel. Updating...")
                update_payload = {
                    "type": "CNAME", "name": hostname,
                    "content": f"{tunnel_id}.cfargotunnel.com",
                    "ttl": 1, "proxied": True
                }
                update_endpoint = f"/zones/{zone_id}/dns_records/{existing_record_id}"
                try:
                    update_response = cf_api_request("PUT", update_endpoint, json_data=update_payload)
                    updated_record = update_response.get("result", {})
                    updated_id = updated_record.get("id")
                    if updated_id:
                        logging.info(f"Successfully updated DNS record for {hostname} to point to correct tunnel. ID: {updated_id}")
                        return updated_id
                    else:
                        logging.error(f"DNS record update API call for {hostname} reported success but response missing ID")
                        return existing_record_id 
                except Exception as update_err: 
                    logging.error(f"Error updating existing DNS record for {hostname}: {update_err}")
                    return existing_record_id # Return old ID
        
        record_name = hostname
        record_content = f"{tunnel_id}.cfargotunnel.com"
        endpoint = f"/zones/{zone_id}/dns_records"
        payload = {
            "type": "CNAME", "name": record_name, "content": record_content,
            "ttl": 1, "proxied": True
        }

        try:
            logging.info(f"Attempting to create DNS CNAME in zone {zone_id}: Name={record_name}, Content={record_content}, Proxied=True")
            response_data = cf_api_request("POST", endpoint, json_data=payload)
            result = response_data.get("result", {})
            new_record_id = result.get("id")
            if new_record_id:
                logging.info(f"Successfully created DNS record for {hostname} in zone {zone_id}. New ID: {new_record_id}")
                return new_record_id
            else:
                logging.error(f"DNS record creation API call for {hostname} reported success but response missing ID: {result}")
                return None
        except requests.exceptions.RequestException as e:
            cf_error_code = getattr(e, 'cf_error_code', None)
            if (cf_error_code == 81057 or
                (e.response is not None and
                 ("record already exists" in e.response.text.lower() or
                  "a, aaaa, or cname record with that host already exists" in e.response.text.lower()))):
                logging.warning(f"DNS record for {hostname} already exists in zone {zone_id} (API error code indicates conflict). Verifying...")
                time.sleep(1) # Give API a moment
                existing_id, _ = find_dns_record_id(zone_id, hostname, tunnel_id)
                if existing_id:
                    logging.info(f"Found existing record ID for {hostname} after conflict: {existing_id}")
                    return existing_id
                return "existing_record_unconfirmed" 
            else:
                logging.error(f"API error creating DNS record for {hostname}: {e}")
                return None
        except Exception as e:
            logging.error(f"Unexpected error creating DNS record for {hostname}: {e}", exc_info=True)
            return None
    finally:
        if acquired:
            dns_semaphore.release()
            logging.debug(f"Released DNS semaphore after processing {hostname}")

def find_dns_record_id(zone_id, hostname, tunnel_id):
    acquired = False
    try:
        acquired = dns_semaphore.acquire(timeout=15)
        if not acquired:
            logging.error(f"Timed out waiting for DNS semaphore in find_dns_record_id for {hostname}")
            return None, False

        if not zone_id or not hostname or not tunnel_id:
            logging.error("find_dns_record_id: Missing required arguments.")
            return None, False

        expected_content = f"{tunnel_id}.cfargotunnel.com"
        endpoint = f"/zones/{zone_id}/dns_records"
        
        params_specific = {"type": "CNAME", "name": hostname, "content": expected_content, "match": "all"}
        try:
            logging.info(f"Searching DNS (specific): Zone={zone_id}, Type=CNAME, Name={hostname}, Content={expected_content}")
            response_data = cf_api_request("GET", endpoint, params=params_specific)
            results = response_data.get("result", [])
            if results and isinstance(results, list) and len(results) == 1: # Expecting one exact match
                record = results[0]
                if record.get("id"):
                    logging.info(f"Found exact DNS record for {hostname} in zone {zone_id} with ID: {record.get('id')}")
                    return record.get("id"), True
            
            logging.info(f"Exact DNS record for {hostname} (content: {expected_content}) not found. Searching by name only.")
            params_by_name = {"type": "CNAME", "name": hostname}
            response_data_by_name = cf_api_request("GET", endpoint, params=params_by_name)
            results_by_name = response_data_by_name.get("result", [])

            if results_by_name and isinstance(results_by_name, list):
                for record in results_by_name: 
                    if record.get("id"):
                        record_content = record.get("content", "")
                        if record_content.lower() == expected_content.lower():
                            logging.info(f"Found DNS record for {hostname} by name search (correct content) with ID: {record.get('id')}")
                            return record.get("id"), True
                        else:
                            logging.warning(f"Found DNS CNAME for {hostname} (ID: {record.get('id')}) but it points to '{record_content}' instead of '{expected_content}'.")
                            return record.get("id"), False # Found a record, but wrong tunnel
                logging.info(f"Found CNAME(s) for {hostname}, but none match expected content '{expected_content}'.")

                if results_by_name[0].get("id"):
                    return results_by_name[0].get("id"), False

            logging.info(f"No CNAME DNS record found for {hostname} in zone {zone_id} after both searches.")
            return None, False
            
        except requests.exceptions.RequestException as e:
            logging.error(f"API error finding DNS record for {hostname}: {e}")
            return None, False
        except Exception as e:
            logging.error(f"Unexpected error finding DNS record for {hostname}: {e}", exc_info=True)
            return None, False
    finally:
        if acquired:
            dns_semaphore.release()
            logging.debug(f"Released DNS semaphore after find_dns_record_id for {hostname}")

def delete_cloudflare_dns_record(zone_id, hostname, tunnel_id):
    acquired = False
    try:
        acquired = dns_semaphore.acquire(timeout=30) 
        if not acquired:
            logging.error(f"Timed out waiting for DNS semaphore in delete_cloudflare_dns_record for {hostname}")
            return False

        if not zone_id or not hostname or not tunnel_id:
            logging.error("delete_cloudflare_dns_record: Missing required arguments.")
            return False

        record_id, is_correct_tunnel = find_dns_record_id(zone_id, hostname, tunnel_id)
        if not record_id:
            logging.warning(f"DNS record for {hostname} in zone {zone_id} (for tunnel {tunnel_id}) not found to delete. Assuming success or already deleted.")
            return True
       
        logging.info(f"Attempting to delete DNS record for {hostname} in zone {zone_id} (ID: {record_id})")
        endpoint = f"/zones/{zone_id}/dns_records/{record_id}"
        try:
            cf_api_request("DELETE", endpoint)
            logging.info(f"Successfully submitted deletion for DNS record {hostname} (ID: {record_id}) in zone {zone_id}.")
            return True
        except requests.exceptions.RequestException as e:
            if e.response is not None and e.response.status_code == 404:
                logging.warning(f"DNS record {record_id} for {hostname} in zone {zone_id} not found during delete attempt (404). Treating as success.")
                return True
            logging.error(f"API error deleting DNS record {record_id} for {hostname} in zone {zone_id}: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error deleting DNS record {record_id} for {hostname} in zone {zone_id}: {e}", exc_info=True)
            return False
    finally:
        if acquired:
            dns_semaphore.release()

def get_cloudflare_account_email():
    global _cached_account_email, _cached_account_email_timestamp
    current_time = time.time()
    
    with _cache_lock: 
        if _cached_account_email and (current_time - _cached_account_email_timestamp < config.ACCOUNT_EMAIL_CACHE_TTL):
            logging.debug(f"Returning cached Cloudflare account email: {_cached_account_email}")
            return _cached_account_email

    logging.info("Fetching Cloudflare account email from API.")
    try:
        response_data = cf_api_request("GET", "/user") 
        if response_data and response_data.get("success"):
            email = response_data.get("result", {}).get("email")
            if email:
                logging.info(f"Successfully fetched Cloudflare account email: {email}")
                with _cache_lock: 
                    _cached_account_email = email
                    _cached_account_email_timestamp = current_time
                return email
            else:
                logging.warning("Cloudflare account email not found in API response.")
                return None
        else:
            logging.warning(f"Failed to fetch Cloudflare account email, API call unsuccessful. Response: {response_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error fetching Cloudflare account email: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching Cloudflare account email: {e}", exc_info=True)
        return None

def get_current_cf_config(tunnel_id_to_query):
    if not tunnel_id_to_query:
        logging.warning("get_current_cf_config: tunnel_id_to_query not provided.")
        return None

    logging.debug(f"Fetching current CF tunnel configuration for tunnel ID {tunnel_id_to_query}.")
    endpoint = f"/accounts/{config.CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_id_to_query}/configurations"
    try:
        response_data = cf_api_request("GET", endpoint)
        if response_data and response_data.get("success"):
            result_data = response_data.get("result") 
            config_data = None
            if isinstance(result_data, dict):
                config_data = result_data.get("config") 

            if isinstance(config_data, dict):
                logging.debug(f"Fetched config for tunnel {tunnel_id_to_query}: {config_data}")
                return config_data 
            elif config_data is None:
                logging.info(f"Fetched 'config' for tunnel {tunnel_id_to_query} is null. Returning empty dict.")
                return {} 
            else:
                logging.warning(f"Unexpected type for 'config' field in API response for tunnel {tunnel_id_to_query}: {type(config_data)}. Result: {result_data}")
                return {} 
        else:
            logging.error(f"Get config API call failed or returned success=false for tunnel {tunnel_id_to_query}: {response_data}")
            return None 
    except requests.exceptions.RequestException as e:
        logging.error(f"API error fetching config for tunnel {tunnel_id_to_query}: {e}")
        raise 
    except Exception as e:
        logging.error(f"Unexpected error fetching config for tunnel {tunnel_id_to_query}: {e}", exc_info=True)
        raise

def get_all_account_cloudflare_tunnels():
    if not config.CF_ACCOUNT_ID:
        logging.warning("CF_ACCOUNT_ID is not configured. Cannot list all Cloudflare tunnels.")
        return []
    if not config.CF_API_TOKEN: 
        logging.error("Cloudflare API token not configured. Cannot list all account tunnels.")
        return []

    endpoint = f"/accounts/{config.CF_ACCOUNT_ID}/cfd_tunnel"
    params = {"is_deleted": "false", "per_page": 100} 
    
    logging.info(f"Attempting to list all Cloudflare tunnels for account ID {config.CF_ACCOUNT_ID}")
    all_tunnels = []
    page = 1
    while True:
        params["page"] = page
        try:
            response_data = cf_api_request("GET", endpoint, params=params)
            tunnels_page = response_data.get("result", [])
            if not isinstance(tunnels_page, list):
                logging.error(f"Unexpected data format for account tunnels list page {page}: {type(tunnels_page)}. Response: {response_data}")
                break 
            
            all_tunnels.extend(tunnels_page)
            
            
            if len(tunnels_page) < params["per_page"]:
                break
            page += 1
            if page > 10: 
                logging.warning("Exceeded 10 pages fetching tunnels. Assuming all fetched or API issue.")
                break
        except requests.exceptions.RequestException as e:
            logging.error(f"API error listing Cloudflare tunnels (page {page}): {e}")
            
            return [] 
        except Exception as e:
            logging.error(f"Unexpected error listing Cloudflare tunnels (page {page}): {e}", exc_info=True)
            return []

    logging.info(f"Successfully retrieved {len(all_tunnels)} Cloudflare tunnels from the account (any status).")
    
    
    desired_statuses = {"healthy", "degraded", "down", "inactive", "pending"} 
    filtered_tunnels = [
        tunnel for tunnel in all_tunnels if tunnel.get("status", "").lower() in desired_statuses
    ]
    
    logging.info(f"Returning {len(filtered_tunnels)} tunnels after client-side status check for relevant statuses.")
    filtered_tunnels.sort(key=lambda t: t.get("name", "").lower()) 
    return filtered_tunnels

def get_dns_records_for_tunnel(zone_id, tunnel_id):
    if not zone_id or not tunnel_id:
        logging.warning("get_dns_records_for_tunnel: Missing zone_id or tunnel_id.")
        return []

    
    zone_details = get_zone_details_by_id(zone_id)
    zone_name_for_display = zone_details.get("name") if zone_details else zone_id

    expected_cname_content = f"{tunnel_id}.cfargotunnel.com"
    endpoint = f"/zones/{zone_id}/dns_records"
    params = {"type": "CNAME", "content": expected_cname_content, "per_page": 100}
    
    logging.info(f"Fetching DNS records for tunnel {tunnel_id} in zone '{zone_name_for_display}' ({zone_id}) with content '{expected_cname_content}'")
    
    all_records_for_tunnel_in_zone = []
    page = 1
    while True:
        params["page"] = page
        try:
            response_data = cf_api_request("GET", endpoint, params=params) 
            dns_records_page = response_data.get("result", [])
            
            if not isinstance(dns_records_page, list):
                logging.error(f"Unexpected data format for DNS records list in zone {zone_name_for_display}, page {page}: {type(dns_records_page)}")
                break

            processed_page_records = []
            for record in dns_records_page:
                if record.get("name"): 
                    processed_page_records.append({
                        "name": record.get("name"), 
                        "id": record.get("id"), 
                        "zone_id": zone_id, 
                        "zone_name": zone_name_for_display 
                    })
            all_records_for_tunnel_in_zone.extend(processed_page_records)

            if len(dns_records_page) < params["per_page"]: 
                break
            page += 1
            if page > 10: # Safety break
                logging.warning(f"Exceeded 10 pages fetching DNS records for tunnel {tunnel_id} in zone {zone_name_for_display}.")
                break
        except requests.exceptions.RequestException as e:
            logging.error(f"API error fetching DNS records for tunnel {tunnel_id} in zone {zone_name_for_display} (page {page}): {e}")
            return [] 
        except Exception as e:
            logging.error(f"Unexpected error fetching DNS records for tunnel {tunnel_id} in zone {zone_name_for_display} (page {page}): {e}", exc_info=True)
            return []
            
    return all_records_for_tunnel_in_zone