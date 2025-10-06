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
# app/core/idp_manager.py
import logging
import requests
from flask import current_app
from app.core import cloudflare_api

def get_supported_idp_types():
    return {
        "google": {
            "name": "Google",
            "category": "oauth",
            "fields": {
                "client_id": {"label": "Client ID", "type": "text", "required": True},
                "client_secret": {"label": "Client Secret", "type": "password", "required": True}
            }
        },
        "google-apps": {
            "name": "Google Workspace",
            "category": "oauth",
            "fields": {
                "client_id": {"label": "Client ID", "type": "text", "required": True},
                "client_secret": {"label": "Client Secret", "type": "password", "required": True},
                "apps_domain": {"label": "Apps Domain", "type": "text", "required": False, "placeholder": "example.com"}
            }
        },
        "azureAD": {
            "name": "Microsoft Azure AD",
            "category": "oauth",
            "fields": {
                "client_id": {"label": "Application (client) ID", "type": "text", "required": True},
                "client_secret": {"label": "Client Secret", "type": "password", "required": True},
                "directory_id": {"label": "Directory (tenant) ID", "type": "text", "required": True}
            }
        },
        "okta": {
            "name": "Okta",
            "category": "oauth",
            "fields": {
                "okta_account": {"label": "Okta Account URL", "type": "text", "required": True, "placeholder": "https://your-domain.okta.com"},
                "client_id": {"label": "Client ID", "type": "text", "required": True},
                "client_secret": {"label": "Client Secret", "type": "password", "required": True}
            }
        },
        "github": {
            "name": "GitHub",
            "category": "oauth",
            "fields": {
                "client_id": {"label": "Client ID", "type": "text", "required": True},
                "client_secret": {"label": "Client Secret", "type": "password", "required": True}
            }
        },
        "oidc": {
            "name": "Generic OpenID Connect",
            "category": "oauth",
            "fields": {
                "client_id": {"label": "Client ID", "type": "text", "required": True},
                "client_secret": {"label": "Client Secret", "type": "password", "required": True},
                "auth_url": {"label": "Authorization URL", "type": "text", "required": True, "placeholder": "https://provider.com/oauth2/authorize"},
                "token_url": {"label": "Token URL", "type": "text", "required": True, "placeholder": "https://provider.com/oauth2/token"},
                "certs_url": {"label": "JWKS URL", "type": "text", "required": True, "placeholder": "https://provider.com/.well-known/jwks.json"}
            }
        }
    }

def list_identity_providers():
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Listing Identity Providers for account {account_id}")
    endpoint = f"/accounts/{account_id}/access/identity_providers"

    try:
        response_data = cloudflare_api.cf_api_request("GET", endpoint)
        idps = response_data.get("result", [])
        logging.info(f"Retrieved {len(idps)} Identity Providers from Cloudflare")
        return idps
    except requests.exceptions.RequestException as e:
        logging.error(f"API error listing Identity Providers: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error listing Identity Providers: {e}", exc_info=True)
        return []

def get_identity_provider(idp_id):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Getting Identity Provider {idp_id} for account {account_id}")
    endpoint = f"/accounts/{account_id}/access/identity_providers/{idp_id}"

    try:
        response_data = cloudflare_api.cf_api_request("GET", endpoint)
        idp = response_data.get("result")
        if idp:
            logging.info(f"Retrieved Identity Provider: {idp.get('name', idp.get('type'))}")
        return idp
    except requests.exceptions.RequestException as e:
        logging.error(f"API error getting Identity Provider {idp_id}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error getting Identity Provider {idp_id}: {e}", exc_info=True)
        return None

def create_identity_provider(name, idp_type, config):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Creating Identity Provider '{name}' of type '{idp_type}' for account {account_id}")
    endpoint = f"/accounts/{account_id}/access/identity_providers"

    payload = {
        "name": name,
        "type": idp_type,
        "config": config
    }

    try:
        response_data = cloudflare_api.cf_api_request("POST", endpoint, json_data=payload)
        idp = response_data.get("result")
        if idp:
            logging.info(f"Successfully created Identity Provider with ID: {idp.get('id')}")
        return idp
    except requests.exceptions.RequestException as e:
        logging.error(f"API error creating Identity Provider '{name}': {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error creating Identity Provider '{name}': {e}", exc_info=True)
        raise

def update_identity_provider(idp_id, name=None, config=None):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Updating Identity Provider {idp_id} for account {account_id}")
    endpoint = f"/accounts/{account_id}/access/identity_providers/{idp_id}"

    payload = {}
    if name is not None:
        payload["name"] = name
    if config is not None:
        payload["config"] = config

    if not payload:
        logging.warning(f"No updates provided for Identity Provider {idp_id}")
        return None

    try:
        response_data = cloudflare_api.cf_api_request("PUT", endpoint, json_data=payload)
        idp = response_data.get("result")
        if idp:
            logging.info(f"Successfully updated Identity Provider {idp_id}")
        return idp
    except requests.exceptions.RequestException as e:
        logging.error(f"API error updating Identity Provider {idp_id}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error updating Identity Provider {idp_id}: {e}", exc_info=True)
        raise

def delete_identity_provider(idp_id):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Deleting Identity Provider {idp_id} for account {account_id}")
    endpoint = f"/accounts/{account_id}/access/identity_providers/{idp_id}"

    try:
        response_data = cloudflare_api.cf_api_request("DELETE", endpoint)
        logging.info(f"Successfully deleted Identity Provider {idp_id}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"API error deleting Identity Provider {idp_id}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error deleting Identity Provider {idp_id}: {e}", exc_info=True)
        raise

def is_system_managed_idp(idp_type):
    system_types = ["onetimepin"]
    return idp_type in system_types

def build_test_idp_url(idp_id):
    team_domain = current_app.config.get('CF_TEAM_DOMAIN')
    if not team_domain:
        try:
            idps = list_identity_providers()
            if idps and len(idps) > 0:
                redirect_url = idps[0].get('config', {}).get('redirect_url', '')
                if redirect_url:
                    team_domain = redirect_url.split('//')[1].split('/')[0] if '//' in redirect_url else None
        except:
            pass

    if team_domain:
        return f"https://{team_domain}/cdn-cgi/access/test-idp/{idp_id}"
    return None
