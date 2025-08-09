import os
import json
import requests
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Optional
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash
import threading
from app import config

# Define the blueprint for the setup wizard
setup_bp = Blueprint('setup', __name__, url_prefix='/setup', template_folder='../templates')

# --- Forms for each step of the wizard ---

class CredentialsForm(FlaskForm):
    """Form for Step 1: Cloudflare API Credentials."""
    cf_api_token = PasswordField('Cloudflare API Token', validators=[DataRequired()])
    cf_account_id = StringField('Cloudflare Account ID', validators=[DataRequired()])
    submit = SubmitField('Next')

class TunnelForm(FlaskForm):
    """Form for Step 2: Tunnel and Zone Configuration."""
    tunnel_name = StringField('Tunnel Name', default='dockflare-tunnel', validators=[DataRequired()])
    cf_zone_id = StringField('Primary Cloudflare Zone ID (Optional)', validators=[Optional()])
    tunnel_dns_scan_zone_names = StringField('Other Zones to Scan (comma-separated, optional)', description="e.g. my-other-domain.com,another.dev")
    grace_period_seconds = IntegerField('Grace Period (seconds)', default=28800, validators=[DataRequired()])
    submit = SubmitField('Next')

class AdminUserForm(FlaskForm):
    """Form for Step 3: Admin User Creation."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('confirm_password', message='Passwords must match.')])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Next')

class FinalizeForm(FlaskForm):
    """Form for Step 4: Finalization."""
    submit = SubmitField('Complete Setup')

# --- Routes for the setup wizard ---

@setup_bp.route('/credentials', methods=['GET', 'POST'])
def step1_api_credentials():
    """Handles the collection and validation of Cloudflare API credentials."""
    form = CredentialsForm()
    if form.validate_on_submit():
        token = form.cf_api_token.data
        account_id = form.cf_account_id.data

        # Verify credentials with a simple, read-only API call to Cloudflare
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel?is_deleted=false"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                session['cf_api_token'] = token
                session['cf_account_id'] = account_id
                flash('Credentials verified successfully.', 'success')
                return redirect(url_for('setup.step2_tunnel_config'))
            else:
                error_message = "Invalid credentials or permissions."
                try:
                    # Attempt to parse a more specific error from Cloudflare's response
                    error_message = response.json().get('errors', [{}])[0].get('message', error_message)
                except:
                    pass # Keep the generic error message if parsing fails
                flash(f'Validation failed. Cloudflare API returned: {error_message}', 'danger')
        except requests.exceptions.RequestException as e:
            flash(f'Could not connect to the Cloudflare API: {e}', 'danger')

    return render_template('setup/step1.html', form=form, title="Setup: API Credentials")

@setup_bp.route('/tunnel', methods=['GET', 'POST'])
def step2_tunnel_config():
    """Handles the configuration of the Cloudflare Tunnel and DNS settings."""
    if 'cf_api_token' not in session:
        return redirect(url_for('setup.step1_api_credentials'))

    form = TunnelForm()
    if form.validate_on_submit():
        session['tunnel_name'] = form.tunnel_name.data
        session['cf_zone_id'] = form.cf_zone_id.data
        session['tunnel_dns_scan_zone_names'] = form.tunnel_dns_scan_zone_names.data
        session['grace_period_seconds'] = form.grace_period_seconds.data
        return redirect(url_for('setup.step3_admin_user'))

    return render_template('setup/step2.html', form=form, title="Setup: Tunnel Configuration")

@setup_bp.route('/admin', methods=['GET', 'POST'])
def step3_admin_user():
    """Handles the creation of the administrative user for the DockFlare UI."""
    if 'tunnel_name' not in session:
        return redirect(url_for('setup.step2_tunnel_config'))

    form = AdminUserForm()
    if form.validate_on_submit():
        session['username'] = form.username.data
        session['password'] = form.password.data
        return redirect(url_for('setup.step4_finalize'))

    return render_template('setup/step3.html', form=form, title="Setup: Admin User")

@setup_bp.route('/finalize', methods=['GET', 'POST'])
def step4_finalize():
    """Finalizes the setup, saving all configuration and securing the application."""
    if 'username' not in session:
        return redirect(url_for('setup.step3_admin_user'))

    form = FinalizeForm()
    if form.validate_on_submit():
        # --- CRITICAL OPERATION: Save all configuration ---
        
        # 1. Generate and save the encryption key
        # This now correctly uses the imported `config` module for the static path.
        data_path = os.path.dirname(config.STATE_FILE_PATH)
        key = Fernet.generate_key()
        key_file = os.path.join(data_path, 'dockflare.key')
        config_file = os.path.join(data_path, 'dockflare_config.dat')
        os.makedirs(data_path, exist_ok=True)
        
        with open(key_file, 'wb') as f:
            f.write(key)
        
        # 2. Hash the admin password
        hashed_password = generate_password_hash(session['password'])
        
        # 3. Assemble the configuration payload
        config_payload = {
            'cf_api_token': session['cf_api_token'],
            'cf_account_id': session['cf_account_id'],
            'tunnel_name': session['tunnel_name'],
            'cf_zone_id': session.get('cf_zone_id'),
            'tunnel_dns_scan_zone_names': session.get('tunnel_dns_scan_zone_names', ''),
            'grace_period_seconds': session['grace_period_seconds'],
            'username': session['username'],
            'password': hashed_password,
        }
        
        # 4. Encrypt and save the payload
        fernet = Fernet(key)
        encrypted_payload = fernet.encrypt(json.dumps(config_payload).encode('utf-8'))
        with open(config_file, 'wb') as f:
            f.write(encrypted_payload)
            
        # 5. Set the application to "configured" mode and update the running config
        current_app.is_configured = True
        from app import config as config_module
        
        # Renamed local variable to `app_config` to avoid name collision.
        app_config = current_app.config
        
        app_config['CF_API_TOKEN'] = config_payload['cf_api_token']
        config_module.CF_API_TOKEN = app_config['CF_API_TOKEN']
        app_config['CF_ACCOUNT_ID'] = config_payload['cf_account_id']
        config_module.CF_ACCOUNT_ID = app_config['CF_ACCOUNT_ID']
        app_config['TUNNEL_NAME'] = config_payload['tunnel_name']
        config_module.TUNNEL_NAME = app_config['TUNNEL_NAME']
        app_config['CLOUDFLARED_CONTAINER_NAME'] = f"cloudflared-agent-{app_config['TUNNEL_NAME']}"
        app_config['CF_ZONE_ID'] = config_payload['cf_zone_id']
        config_module.CF_ZONE_ID = app_config['CF_ZONE_ID']
        tunnel_dns_scan_zone_names_str = config_payload.get('tunnel_dns_scan_zone_names', '')
        app_config['TUNNEL_DNS_SCAN_ZONE_NAMES'] = [name.strip() for name in tunnel_dns_scan_zone_names_str.split(',') if name.strip()]
        config_module.TUNNEL_DNS_SCAN_ZONE_NAMES = app_config['TUNNEL_DNS_SCAN_ZONE_NAMES']
        app_config['GRACE_PERIOD_SECONDS'] = int(config_payload.get('grace_period_seconds', 28800))
        config_module.GRACE_PERIOD_SECONDS = app_config['GRACE_PERIOD_SECONDS']
        app_config['DOCKFLARE_USERNAME'] = config_payload['username']
        app_config['DOCKFLARE_PASSWORD_HASH'] = config_payload['password']
        if config_module.CF_API_TOKEN:
            config_module.CF_HEADERS['Authorization'] = f"Bearer {config_module.CF_API_TOKEN}"
        
        # 6. Start core services in the background (import is local to prevent circular dependency)
        from app.main import start_core_services
        logging.info("Setup complete. Triggering core services to start in a background thread.")
        init_thread = threading.Thread(target=start_core_services, daemon=True)
        init_thread.start()

        # 7. Clean up session and redirect to the login page
        session.clear()
        flash('Setup complete! Please log in to continue.', 'success')
        return redirect(url_for('auth.login'))
        
    # For the GET request, display a summary of the configuration
    config_summary = {key: val for key, val in session.items() if key != 'csrf_token' and not key.startswith('_')}
    if 'cf_api_token' in config_summary:
        config_summary['cf_api_token'] = '********'
    if 'password' in config_summary:
        del config_summary['password'] # Do not show the password, even masked
        
    return render_template('setup/step4.html', form=form, title="Setup: Finalize", summary=config_summary)