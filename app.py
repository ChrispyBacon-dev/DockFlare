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
def super_minimal_route():
    logging.info("Attempting to render super_minimal.html")
    try:
        # If inject_protocol is added, make sure super_minimal.html doesn't try to use these vars
        # or pass dummy values if it does. For now, it doesn't.
        return render_template('super_minimal.html')
    except Exception as e:
        logging.error(f"Error rendering super_minimal.html: {e}", exc_info=True)
        return "Error rendering template, check logs", 500

if __name__ == '__main__':
    logging.info("Starting SUPER MINIMAL Flask app for testing render_template.")
    app.run(host='0.0.0.0', port=5000, debug=True)