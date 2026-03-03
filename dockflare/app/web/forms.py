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
# dockflare/app/web/forms.py
from flask_wtf import FlaskForm
from flask_babel import lazy_gettext as _l
from wtforms import BooleanField, PasswordField, SubmitField, StringField, IntegerField
from wtforms.validators import DataRequired, EqualTo, Length, Optional

class SettingsForm(FlaskForm):
    """Form for editing general application settings."""
    tunnel_name = StringField(
        _l('Tunnel Name'),
        validators=[DataRequired(message=_l('A tunnel name is required.'))]
    )
    cf_zone_id = StringField(
        _l('Primary Cloudflare Zone ID'),
        validators=[Optional()]
    )
    tunnel_dns_scan_zone_names = StringField(
        _l('Other Zones to Scan (comma-separated)'),
        description=_l('e.g. my-other-domain.com,another.dev'),
        validators=[Optional()]
    )
    grace_period_seconds = IntegerField(
        _l('Grace Period (seconds)'),
        validators=[DataRequired(message=_l('Grace period is required.'))]
    )
    submit_settings = SubmitField(_l('Save General Settings'))

class SecuritySettingsForm(FlaskForm):
    """Form for editing security settings."""
    disable_password_login = BooleanField(
        _l('Disable Password Login')
    )
    oauth_session_timeout = IntegerField(
        _l('OAuth Session Timeout (seconds)'),
        default=86400,
        validators=[Optional()]
    )
    oauth_audit_enabled = BooleanField(
        _l('Enable OAuth Audit Logging'),
        default=True
    )
    submit_security_settings = SubmitField(_l('Save Security Settings'))

class ChangePasswordForm(FlaskForm):
    """Form for changing the user's password."""
    current_password = PasswordField(
        _l('Current Password'),
        validators=[DataRequired()]
    )
    new_password = PasswordField(
        _l('New Password'),
        validators=[
            DataRequired(),
            Length(min=8, message=_l('Password must be at least 8 characters long.'))
        ]
    )
    confirm_new_password = PasswordField(
        _l('Confirm New Password'),
        validators=[
            DataRequired(),
            EqualTo('new_password', message=_l('New passwords must match.'))
        ]
    )
    submit = SubmitField(_l('Change Password'))


class LoginForm(FlaskForm):
    """Form for the main login page."""
    username = StringField(
        _l('Username'),
        validators=[DataRequired(message=_l('Username is required.'))]
    )
    password = PasswordField(
        _l('Password'),
        validators=[DataRequired(message=_l('Password is required.'))]
    )
    submit = SubmitField(_l('Login'))

class CloudflareCredentialsForm(FlaskForm):
    """Form for updating Cloudflare API credentials."""
    cf_account_id = StringField(
        _l('Cloudflare Account ID'),
        validators=[Optional(), Length(min=32, max=32, message=_l('Account ID must be 32 characters long.'))]
    )
    cf_api_token = PasswordField(
        _l('Cloudflare API Token'),
        validators=[Optional(), Length(min=40, max=40, message=_l('API Token must be 40 characters long.'))]
    )
    submit_cloudflare_credentials = SubmitField(_l('Update Cloudflare Credentials'))
