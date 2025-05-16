import logging
from flask import Flask, render_template, request, url_for # Added url_for
import os
import copy # For deepcopy if you re-introduce rules_for_template
from datetime import datetime, timezone # For date formatting if re-introducing rules

# --- Minimal example initializations needed by status_page.html shell ---
CF_ACCOUNT_ID_CONFIGURED = True
ACCOUNT_ID_FOR_DISPLAY = "Test Account ID"
CF_ZONE_ID_CONFIGURED = True # Assuming your template might check this
docker_client = True # Dummy, or actual init if needed by a helper

# Provide minimal structures for these, matching what the template expects
tunnel_state_minimal = {
    "name": "test-tunnel", "id": "test-id", "token": "test-token-value", 
    "status_message": "Minimal Test OK", "error": None
}
# Ensure .get('error') can be called, and .last_action_status for agent_state
cloudflared_agent_state_minimal = {
    "container_status": "running", 
    "last_action_status": None
}
managed_rules_minimal = {} # If rules are iterated somewhere still visible
initialization_status_minimal = { "complete": True, "in_progress": False }

# Dummy for get_display_token if your template uses it directly
def get_display_token(token):
    if not token: return "N/A"
    return f"{token[:2]}...{token[-2:]}" if len(token) > 4 else token

# Keep the cached version of get_all_account_cloudflare_tunnels
_all_tunnels_cache = [] 
_all_tunnels_cache_time = 0
_ALL_TUNNELS_CACHE_TTL = 120
# state_lock = threading.Lock() # Define if used by get_all_account_cloudflare_tunnels

def get_all_account_cloudflare_tunnels(): 
    global _all_tunnels_cache, _all_tunnels_cache_time
    # with state_lock: # If you defined and use state_lock
    current_time = time.time()
    if _all_tunnels_cache is not None and (current_time - _all_tunnels_cache_time < _ALL_TUNNELS_CACHE_TTL):
        logging.info("Returning all_account_tunnels from cache.")
        return _all_tunnels_cache
    logging.info("Cache miss for all_account_tunnels, returning empty for this test.")
    _all_tunnels_cache = [] 
    _all_tunnels_cache_time = current_time
    return []

CLOUDFLARED_CONTAINER_NAME = "test-agent-minimal"
USE_EXTERNAL_CLOUDFLARED = False
EXTERNAL_TUNNEL_ID = None
# --- End of minimal initializations ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s')
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PREFERRED_URL_SCHEME'] = 'https'

@app.before_request
def detect_protocol():
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    app.config['PREFERRED_URL_SCHEME'] = 'https' if forwarded_proto == 'https' or request.is_secure else 'http'

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    is_https = forwarded_proto == 'https' or request.is_secure
    csp = (
        "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; "
        "script-src * 'unsafe-inline' 'unsafe-eval'; "
        "style-src * 'unsafe-inline'; "
        "img-src * data: blob:; "
        "font-src * data:; "
        "connect-src *; "
        "frame-src *; "
    )
    if is_https:
        csp += "upgrade-insecure-requests; "
    response.headers['Content-Security-Policy'] = csp
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if is_https:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Authorization'
    return response

@app.context_processor
def inject_protocol():
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    is_https = forwarded_proto == 'https' or request.is_secure
    base_url = f"{'https' if is_https else 'http'}://{request.host}"
    request_scheme = request.scheme
    return {
        'protocol': 'https' if is_https else 'http',
        'is_https': is_https,
        'base_url': base_url,
        'host': request.host,
        'request_scheme': request_scheme
    }

@app.route('/')
def current_test_route():
    logging.info("Attempting to render ORIGINAL status_page.html (simplified content, more vars)")
    try:
        display_token_val = get_display_token(tunnel_state_minimal.get("token"))
        docker_available = docker_client is not None # Or just True for this test
        all_account_tunnels_list_val = get_all_account_cloudflare_tunnels()

        return render_template('status_page.html',
                            tunnel_state=tunnel_state_minimal,
                            agent_state=cloudflared_agent_state_minimal,
                            initialization=initialization_status_minimal,
                            display_token=display_token_val,
                            cloudflared_container_name=CLOUDFLARED_CONTAINER_NAME,
                            docker_available=docker_available,
                            external_cloudflared=USE_EXTERNAL_CLOUDFLARED,
                            external_tunnel_id=EXTERNAL_TUNNEL_ID,
                            rules=managed_rules_minimal, # Pass the minimal rules dict
                            all_account_tunnels=all_account_tunnels_list_val,
                            CF_ACCOUNT_ID_CONFIGURED=CF_ACCOUNT_ID_CONFIGURED,
                            ACCOUNT_ID_FOR_DISPLAY=ACCOUNT_ID_FOR_DISPLAY,
                            CF_ZONE_ID_CONFIGURED=CF_ZONE_ID_CONFIGURED
                            # Add any other specific variables your template's visible parts might need
                            )
    except Exception as e:
        logging.error(f"Error rendering status_page.html (more vars): {e}", exc_info=True)
        return f"Error rendering template: {e}", 500

if __name__ == '__main__':
    logging.info("Starting MODIFIED MINIMAL Flask app for testing status_page.html (more vars).")
    app.run(host='0.0.0.0', port=5000, debug=True)