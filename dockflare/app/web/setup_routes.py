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
# dockflare/app/web/setup_routes.py
import os
import json
import requests
import logging
import threading
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Optional
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash
from app import config
from app.core import backup_manager
from app.core.container_name import build_cloudflared_container_name
from app.i18n import t as _t
from app.web import config_loader

setup_bp = Blueprint('setup', __name__, url_prefix='/setup', template_folder='../templates')


def _setup_lock_exists():
    data_path = os.path.dirname(config.STATE_FILE_PATH)
    key_file = os.path.join(data_path, 'dockflare.key')
    config_file = os.path.join(data_path, 'dockflare_config.dat')
    return os.path.exists(key_file) and os.path.exists(config_file)

# Step 1
class AdminUserForm(FlaskForm):
    """Form for Step 1: Admin User Creation."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('confirm_password', message='Passwords must match.')])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Next')

# Step 2
class CredentialsForm(FlaskForm):
    """Form for Step 2: Cloudflare API Credentials."""
    cf_api_token = PasswordField('Cloudflare API Token', validators=[DataRequired()])
    cf_account_id = StringField('Cloudflare Account ID', validators=[DataRequired()])
    submit = SubmitField('Next')

# Step 3
class TunnelForm(FlaskForm):
    """Form for Step 3: Tunnel and Zone Configuration."""
    tunnel_name = StringField('Tunnel Name', default='dockflare-tunnel', validators=[DataRequired()])
    cf_zone_id = StringField('Primary Cloudflare Zone ID (Optional)', validators=[Optional()])
    tunnel_dns_scan_zone_names = StringField('Other Zones to Scan (comma-separated, optional)', description="e.g. my-other-domain.com,another.dev")
    grace_period_seconds = IntegerField('Grace Period (seconds)', default=28800, validators=[DataRequired()])
    submit = SubmitField('Next')

# Step 4
class FinalizeForm(FlaskForm):
    """Form for Step 4: Finalization."""
    submit = SubmitField('Complete Setup')

class ImportEnvForm(FlaskForm):
    """Form for acknowledging the .env import."""
    submit = SubmitField('Proceed to User Creation')

@setup_bp.route('/', methods=['GET'])
@setup_bp.route('/step1', methods=['GET', 'POST'])
def step1_admin_user():
    if _setup_lock_exists():
        return redirect(url_for('auth.login'))
    form = AdminUserForm()
    is_migration = session.get('is_env_import', False)

    if form.validate_on_submit():
        session['username'] = form.username.data
        session['password'] = form.password.data

        if is_migration:

            return redirect(url_for('setup.step4_finalize'))
        else:

            return redirect(url_for('setup.step2_api_credentials'))

    return render_template(
        'setup/step1_user.html',
        form=form,
        title="Step 1: Setup Web Access",
        current_step=1,
        is_migration=is_migration,
        show_restore_option=True
    )


@setup_bp.route('/restore', methods=['GET', 'POST'])
def restore_from_backup():
    if _setup_lock_exists():
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        file = request.files.get('backup_file')
        if not file or file.filename == '':
            flash(_t('flash.setup.restore_select_error'), 'danger')
            return redirect(url_for('setup.restore_from_backup'))

        try:
            result = backup_manager.restore_backup(file, allow_legacy_json=False)
            is_full_archive = result.mode != "legacy_state"
            backup_manager.refresh_runtime_after_restore(result)

            if 'state.json' in result.files_applied:
                try:
                    from app.core.reconciler import reconcile_state_threaded

                    reconcile_state_threaded()
                except Exception as err:  # pylint: disable=broad-except
                    logging.error("SETUP_RESTORE: Failed to trigger reconciliation: %s", err, exc_info=True)

            config_payload = config_loader.load_encrypted_config()
            if not config_payload:
                flash(_t('flash.setup.restore_config_error'), 'danger')
                return redirect(url_for('setup.restore_from_backup'))

            config_loader.apply_config_to_app(current_app, config_payload)
            current_app.import_from_env = False

            if is_full_archive:
                return render_template('restore_restarting.html', countdown_seconds=7)

            return redirect(url_for('auth.login'))
        except Exception as err:
            logging.error("SETUP_RESTORE: Failed restoring backup: %s", err, exc_info=True)
            flash(_t('flash.setup.restore_failed'), 'danger')
            return redirect(url_for('setup.restore_from_backup'))

    return render_template('setup/restore.html', title='Restore from Backup', current_step=0)

@setup_bp.route('/step2', methods=['GET', 'POST'])
def step2_api_credentials():
    if _setup_lock_exists():
        return redirect(url_for('auth.login'))
    if 'username' not in session:
        return redirect(url_for('setup.step1_admin_user'))

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
                flash(_t('flash.setup.credentials_verified'), 'success')
                return redirect(url_for('setup.step3_tunnel_config'))
            else:
                error_message = "Invalid credentials or permissions."
                try:
                    error_message = response.json().get('errors', [{}])[0].get('message', error_message)
                except Exception:
                    pass
                flash(_t('flash.setup.validation_failed', errorMessage=error_message), 'danger')
        except requests.exceptions.RequestException as e:
            flash(_t('flash.setup.api_connection_failed', error=str(e)), 'danger')

    return render_template('setup/step2_cloudflare.html', form=form, title="Step 2: Cloudflare Configuration", current_step=2)

@setup_bp.route('/step3', methods=['GET', 'POST'])
def step3_tunnel_config():
    if _setup_lock_exists():
        return redirect(url_for('auth.login'))
    if 'cf_api_token' not in session:
        return redirect(url_for('setup.step2_api_credentials'))

    form = TunnelForm()
    if form.validate_on_submit():
        session['tunnel_name'] = form.tunnel_name.data
        session['cf_zone_id'] = form.cf_zone_id.data
        session['tunnel_dns_scan_zone_names'] = form.tunnel_dns_scan_zone_names.data
        session['grace_period_seconds'] = form.grace_period_seconds.data
        return redirect(url_for('setup.step4_finalize'))

    return render_template('setup/step3_tunnel.html', form=form, title="Step 3: Tunnel Configuration", current_step=3)

@setup_bp.route('/step4', methods=['GET', 'POST'])
def step4_finalize():
    if _setup_lock_exists():
        return redirect(url_for('auth.login'))
    if 'tunnel_name' not in session:
        return redirect(url_for('setup.step3_tunnel_config'))

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

        master_api_key = session.get('master_api_key') or os.getenv('DOCKFLARE_API_KEY')
        if not master_api_key:
            master_api_key = secrets.token_urlsafe(40)
            session['master_api_key'] = master_api_key

        config_payload = {
            'cf_api_token': session['cf_api_token'],
            'cf_account_id': session['cf_account_id'],
            'tunnel_name': session['tunnel_name'],
            'cf_zone_id': session.get('cf_zone_id'),
            'tunnel_dns_scan_zone_names': session.get('tunnel_dns_scan_zone_names', ''),
            'grace_period_seconds': session['grace_period_seconds'],
            'preserve_unmanaged_cf_ingress_fields': False,
            'username': session['username'],
            'password': hashed_password,
            'master_api_key': master_api_key,
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
        app_config['CLOUDFLARED_CONTAINER_NAME'] = build_cloudflared_container_name(app_config['TUNNEL_NAME'])
        app_config['CF_ZONE_ID'] = config_payload['cf_zone_id']
        config_module.CF_ZONE_ID = app_config['CF_ZONE_ID']
        tunnel_dns_scan_zone_names_str = config_payload.get('tunnel_dns_scan_zone_names', '')
        app_config['TUNNEL_DNS_SCAN_ZONE_NAMES'] = [name.strip() for name in tunnel_dns_scan_zone_names_str.split(',') if name.strip()]
        config_module.TUNNEL_DNS_SCAN_ZONE_NAMES = app_config['TUNNEL_DNS_SCAN_ZONE_NAMES']
        app_config['GRACE_PERIOD_SECONDS'] = int(config_payload.get('grace_period_seconds', 28800))
        config_module.GRACE_PERIOD_SECONDS = app_config['GRACE_PERIOD_SECONDS']
        app_config['PRESERVE_UNMANAGED_CF_INGRESS_FIELDS'] = bool(config_payload.get('preserve_unmanaged_cf_ingress_fields', False))
        config_module.PRESERVE_UNMANAGED_CF_INGRESS_FIELDS = app_config['PRESERVE_UNMANAGED_CF_INGRESS_FIELDS']
        app_config['DOCKFLARE_USERNAME'] = config_payload['username']
        app_config['DOCKFLARE_PASSWORD_HASH'] = config_payload['password']
        app_config['MASTER_API_KEY'] = master_api_key
        if config_module.CF_API_TOKEN:
            config_module.CF_HEADERS['Authorization'] = f"Bearer {config_module.CF_API_TOKEN}"
        config_module.MASTER_API_KEY = master_api_key

        from app.main import start_core_services
        logging.info("Setup complete. Triggering core services to start in a background thread.")
        init_thread = threading.Thread(target=start_core_services, daemon=True)
        init_thread.start()

        session.clear()
        flash(_t('flash.setup.setup_complete'), 'success')
        return redirect(url_for('web.login'))

    config_summary = {key: val for key, val in session.items() if key != 'csrf_token' and not key.startswith('_')}
    if 'cf_api_token' in config_summary:
        config_summary['cf_api_token'] = '********'
    if 'password' in config_summary:
        del config_summary['password']
    if 'master_api_key' in config_summary:
        config_summary['master_api_key'] = '********'

    return render_template('setup/step4_finalize.html', form=form, title="Step 4: Finalize Setup", summary=config_summary, current_step=4)

@setup_bp.route('/import-env', methods=['GET', 'POST'])
def step_import_env():
    if _setup_lock_exists():
        return redirect(url_for('auth.login'))
    """Handles the import of settings from environment variables for migration."""
    if request.method == 'POST' and 'cancel' in request.form:
        
        keys_to_clear = [
            'is_env_import', 'cf_api_token', 'cf_account_id', 'tunnel_name',
            'cf_zone_id', 'tunnel_dns_scan_zone_names', 'grace_period_seconds'
        ]
        for key in keys_to_clear:
            session.pop(key, None)
        flash(_t('flash.setup.migration_cancelled'), 'info')
        return redirect(url_for('setup.step1_admin_user'))

    if not session.get('is_env_import'):

        return redirect(url_for('setup.step1_admin_user'))

    form = ImportEnvForm()

    if form.validate_on_submit():

        if not session.get('cf_api_token') or not session.get('cf_account_id'):
            flash(_t('flash.setup.critical_info_missing'), 'danger')
            session.clear()

            return redirect(url_for('setup.step2_api_credentials'))

        flash(_t('flash.setup.settings_confirmed'), 'info')
        return redirect(url_for('setup.step1_admin_user'))

    imported_settings = {
        'CF_API_TOKEN': '********' if session.get('cf_api_token') else 'Not Found',
        'CF_ACCOUNT_ID': session.get('cf_account_id', 'Not Found'),
        'TUNNEL_NAME': session.get('tunnel_name', 'Not Found'),
        'CF_ZONE_ID': session.get('cf_zone_id') or 'Not Set',
        'TUNNEL_DNS_SCAN_ZONE_NAMES': session.get('tunnel_dns_scan_zone_names') or 'Not Set',
        'GRACE_PERIOD_SECONDS': session.get('grace_period_seconds') or 'Not Set',
    }

    if not session.get('cf_api_token') or not session.get('cf_account_id'):
        flash(_t('flash.setup.required_fields_missing'), 'warning')

    return render_template('setup/step_import_env.html', form=form, title="Setup: Import from .env", summary=imported_settings)
