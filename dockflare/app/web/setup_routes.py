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
# app/web/setup_routes.py
import os
import json
import requests
import logging
import threading
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Optional
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash
from app import config


setup_bp = Blueprint('setup', __name__, url_prefix='/setup', template_folder='../templates')


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

class ImportEnvForm(FlaskForm):
    """Form for acknowledging the .env import."""
    submit = SubmitField('Proceed to User Creation')

class FinalizeForm(FlaskForm):
    """Form for Step 4: Finalization."""
    submit = SubmitField('Complete Setup')


@setup_bp.route('/import-env', methods=['GET', 'POST'])
def step_import_env():
    """Handles the import of settings from environment variables for migration."""

    if not session.get('is_env_import'):
        return redirect(url_for('setup.step1_api_credentials'))

    form = ImportEnvForm()

    if form.validate_on_submit():

        if not session.get('cf_api_token') or not session.get('cf_account_id'):
            flash('Critical information (API Token or Account ID) was missing from the import. Please configure manually.', 'danger')
            session.clear()
            return redirect(url_for('setup.step1_api_credentials'))

        flash('Settings confirmed. Please create an admin user to continue.', 'info')
        return redirect(url_for('setup.step3_admin_user'))

    imported_settings = {
        'CF_API_TOKEN': '********' if session.get('cf_api_token') else 'Not Found',
        'CF_ACCOUNT_ID': session.get('cf_account_id', 'Not Found'),
        'TUNNEL_NAME': session.get('tunnel_name', 'Not Found'),
        'CF_ZONE_ID': session.get('cf_zone_id') or 'Not Set',
        'TUNNEL_DNS_SCAN_ZONE_NAMES': session.get('tunnel_dns_scan_zone_names') or 'Not Set',
        'GRACE_PERIOD_SECONDS': session.get('grace_period_seconds') or 'Not Set',
    }
   
    if not session.get('cf_api_token') or not session.get('cf_account_id'):
        flash('Warning: Missing required fields (CF_API_TOKEN or CF_ACCOUNT_ID). You will not be able to proceed.', 'warning')

    return render_template('setup/step_import_env.html', form=form, title="Setup: Import from .env", summary=imported_settings)

@setup_bp.route('/credentials', methods=['GET', 'POST'])
def step1_api_credentials():
    
    form = CredentialsForm()
    if form.validate_on_submit():
        token = form.cf_api_token.data
        account_id = form.cf_account_id.data

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
                    error_message = response.json().get('errors', [{}])[0].get('message', error_message)
                except:
                    pass
                flash(f'Validation failed. Cloudflare API returned: {error_message}', 'danger')
        except requests.exceptions.RequestException as e:
            flash(f'Could not connect to the Cloudflare API: {e}', 'danger')
        
    return render_template('setup/step1.html', form=form, title="Setup: API Credentials")

@setup_bp.route('/tunnel', methods=['GET', 'POST'])
def step2_tunnel_config():
    
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
    
    if 'username' not in session:
        return redirect(url_for('setup.step3_admin_user'))

    form = FinalizeForm()
    if form.validate_on_submit():
            
        data_path = os.path.dirname(config.STATE_FILE_PATH)
        key = Fernet.generate_key()
        key_file = os.path.join(data_path, 'dockflare.key')
        config_file = os.path.join(data_path, 'dockflare_config.dat')
        os.makedirs(data_path, exist_ok=True)
        
        with open(key_file, 'wb') as f:
            f.write(key)
        
        hashed_password = generate_password_hash(session['password'])
        
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
        
        fernet = Fernet(key)
        encrypted_payload = fernet.encrypt(json.dumps(config_payload).encode('utf-8'))
        with open(config_file, 'wb') as f:
            f.write(encrypted_payload)
            
        current_app.is_configured = True
        from app import config as config_module
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
        
        from app.main import start_core_services
        logging.info("Setup complete. Triggering core services to start in a background thread.")
        init_thread = threading.Thread(target=start_core_services, daemon=True)
        init_thread.start()

        session.clear()
        flash('Setup complete! Please log in to continue.', 'success')
        return redirect(url_for('auth.login'))
        
    config_summary = {key: val for key, val in session.items() if key != 'csrf_token' and not key.startswith('_')}
    if 'cf_api_token' in config_summary:
        config_summary['cf_api_token'] = '********'
    if 'password' in config_summary:
        del config_summary['password']
        
    return render_template('setup/step4.html', form=form, title="Setup: Finalize", summary=config_summary)