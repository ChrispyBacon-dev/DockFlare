import logging
from flask import Flask, render_template, request
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PREFERRED_URL_SCHEME'] = 'https'

@app.before_request
def detect_protocol():
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    app.config['PREFERRED_URL_SCHEME'] = 'https' if forwarded_proto == 'https' or request.is_secure else 'http'

@app.after_request
def add_security_headers(response):
    # ... (same as above) ...
    return response

@app.context_processor # <--- ADDED
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
def current_test_route(): # Use a distinct name for clarity
    logging.info("Attempting to render status_page.html (extremely simplified content)")
    try:
        # Pass only variables that might be used by the surrounding shell of status_page.html
        # (like those used in your base template if you extend one, or by the header/footer)
        # For now, let's assume very few are needed by the shell if the content is minimal.
        return render_template('status_page.html', 
                               CF_ACCOUNT_ID_CONFIGURED=True, # Dummy
                               ACCOUNT_ID_FOR_DISPLAY="Test", # Dummy
                               # Add any other vars your base template/header/footer might need
                              ) 
    except Exception as e:
        logging.error(f"Error rendering status_page.html (simplified): {e}", exc_info=True)
        return "Error rendering template, check logs", 500

if __name__ == '__main__':
    logging.info("Starting SUPER MINIMAL Flask app for testing render_template.")
    app.run(host='0.0.0.0', port=5000, debug=True)