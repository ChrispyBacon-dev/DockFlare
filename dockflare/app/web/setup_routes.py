# DockFlare Setup Wizard Blueprint

import os
import json
import requests
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, EqualTo
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash

from app.core.cloudflare_api import get_all_account_cloudflare_tunnels


setup_bp = Blueprint('setup', __name__, url_prefix='/setup')


def _data_dir():
    return os.path.dirname(current_app.config.get('STATE_FILE_PATH', '/app/data/state.json'))


class CredentialsForm(FlaskForm):
    cf_api_token = PasswordField('Cloudflare API Token', validators=[DataRequired()])
    cf_account_id = StringField('Cloudflare Account ID', validators=[DataRequired()])
    submit = SubmitField('Next')


class TunnelForm(FlaskForm):
    tunnel_name = StringField('Tunnel Name', validators=[DataRequired()])
    cf_zone_id = StringField('Default Zone ID', validators=[Optional()])
    tunnel_dns_scan_zone_names = StringField('Additional Zone Names (comma separated)', validators=[Optional()])
    grace_period_seconds = IntegerField('Grace Period (seconds)', validators=[NumberRange(min=0)], default=28800)
    submit = SubmitField('Next')


class AdminForm(FlaskForm):
    username = StringField('Admin Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Next')


@setup_bp.route('/credentials', methods=['GET', 'POST'])
def step1_credentials():
    form = CredentialsForm()
    if request.method == 'POST' and form.validate_on_submit():
        # Validate token with Cloudflare /user endpoint
        try:
            resp = requests.get(
                'https://api.cloudflare.com/client/v4/user',
                headers={'Authorization': f'Bearer {form.cf_api_token.data}'},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict) or data.get('success') is not True:
                flash('Cloudflare API token validation failed. Please check the token.', 'error')
                return render_template('setup/credentials.html', form=form)
        except Exception:
            flash('Cloudflare API token validation failed. Please verify connectivity and token.', 'error')
            return render_template('setup/credentials.html', form=form)

        # Validate account ID by attempting to list tunnels (read-only)
        try:
            account_id = form.cf_account_id.data.strip()
            resp2 = requests.get(
                f'https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel',
                headers={'Authorization': f'Bearer {form.cf_api_token.data}'},
                params={'is_deleted': 'false', 'per_page': 1},
                timeout=15
            )
            resp2.raise_for_status()
            data2 = resp2.json()
            if not isinstance(data2, dict) or data2.get('success') is not True:
                flash('Account ID validation failed. Please verify the Account ID belongs to the API token.', 'error')
                return render_template('setup/credentials.html', form=form)
        except Exception:
            flash('Account ID validation failed. Please verify the Account ID belongs to the API token.', 'error')
            return render_template('setup/credentials.html', form=form)

        session['setup'] = session.get('setup', {})
        session['setup'].update({
            'cf_api_token': form.cf_api_token.data,
            'cf_account_id': form.cf_account_id.data,
        })
        session.modified = True
        return redirect(url_for('setup.step2_tunnel'))
    return render_template('setup/credentials.html', form=form)


@setup_bp.route('/tunnel', methods=['GET', 'POST'])
def step2_tunnel():
    form = TunnelForm()
    if request.method == 'POST' and form.validate_on_submit():
        session['setup'] = session.get('setup', {})
        session['setup'].update({
            'tunnel_name': form.tunnel_name.data,
            'cf_zone_id': form.cf_zone_id.data or None,
            'tunnel_dns_scan_zone_names': form.tunnel_dns_scan_zone_names.data or '',
            'grace_period_seconds': form.grace_period_seconds.data or 28800,
        })
        session.modified = True
        return redirect(url_for('setup.step3_admin'))
    return render_template('setup/tunnel.html', form=form)


@setup_bp.route('/admin', methods=['GET', 'POST'])
def step3_admin():
    form = AdminForm()
    if request.method == 'POST' and form.validate_on_submit():
        session['setup'] = session.get('setup', {})
        session['setup'].update({
            'admin_username': form.username.data,
            'admin_password': form.password.data,
        })
        session.modified = True
        return redirect(url_for('setup.finalize'))
    return render_template('setup/admin.html', form=form)


@setup_bp.route('/finalize', methods=['GET', 'POST'])
def finalize():
    if request.method == 'POST':
        data = session.get('setup') or {}
        if not data:
            flash('Setup session expired. Please restart.', 'error')
            return redirect(url_for('setup.step1_credentials'))

        # Build payload
        payload = {
            'cf_api_token': data.get('cf_api_token'),
            'cf_account_id': data.get('cf_account_id'),
            'cf_zone_id': data.get('cf_zone_id'),
            'tunnel_name': data.get('tunnel_name'),
            'tunnel_dns_scan_zone_names': data.get('tunnel_dns_scan_zone_names') or '',
            'grace_period_seconds': int(data.get('grace_period_seconds') or 28800),
            'admin': {
                'username': data.get('admin_username'),
                'password_hash': generate_password_hash(data.get('admin_password', '')),
            }
        }

        # Encrypt and persist
        os.makedirs(_data_dir(), exist_ok=True)
        key = Fernet.generate_key()
        with open(os.path.join(_data_dir(), 'dockflare.key'), 'wb') as fk:
            fk.write(key)
        fernet = Fernet(key)
        encrypted = fernet.encrypt(json.dumps(payload).encode('utf-8'))
        with open(os.path.join(_data_dir(), 'dockflare_config.dat'), 'wb') as fc:
            fc.write(encrypted)

        # Cleanup session and mark configured
        session.pop('setup', None)
        try:
            # Load the configuration into the running app without restart
            from app.__init__ import _load_encrypted_configuration
            _load_encrypted_configuration(current_app)
        except Exception:
            current_app.is_configured = True
        flash('Setup complete. Please login.', 'success')
        return redirect(url_for('auth.login'))

    # GET - show summary
    summary = session.get('setup') or {}
    masked = summary.copy()
    if masked.get('cf_api_token'):
        t = masked['cf_api_token']
        masked['cf_api_token'] = f"{t[:4]}...{t[-4:]}" if len(t) > 8 else '***'
    return render_template('setup/finalize.html', summary=masked)


