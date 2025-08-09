# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.

import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import check_password_hash
from cryptography.fernet import Fernet

from app.core.user import User


auth_bp = Blueprint('auth', __name__)


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


def _load_config_from_disk():
    data_dir = os.path.dirname(current_app.config.get('STATE_FILE_PATH', '/app/data/state.json'))
    key_path = os.path.join(data_dir, 'dockflare.key')
    cfg_path = os.path.join(data_dir, 'dockflare_config.dat')
    if not (os.path.exists(key_path) and os.path.exists(cfg_path)):
        return None
    with open(key_path, 'rb') as fk:
        key = fk.read()
    fernet = Fernet(key)
    with open(cfg_path, 'rb') as fc:
        encrypted = fc.read()
    decrypted = fernet.decrypt(encrypted)
    return json.loads(decrypted.decode('utf-8'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        loaded = _load_config_from_disk()
        if not loaded or 'admin' not in loaded:
            flash('Configuration not found. Please complete setup first.', 'error')
            return redirect(url_for('setup.step1_credentials'))
        admin = loaded.get('admin', {})
        if admin.get('username') != form.username.data:
            flash('Invalid credentials', 'error')
            return render_template('login.html', form=form)
        if not check_password_hash(admin.get('password_hash', ''), form.password.data):
            flash('Invalid credentials', 'error')
            return render_template('login.html', form=form)

        login_user(User(admin['username']))
        return redirect(url_for('web.status_page'))
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


