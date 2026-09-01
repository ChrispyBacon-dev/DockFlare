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
from wtforms import BooleanField, PasswordField, SubmitField, StringField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Optional

class SettingsForm(FlaskForm):
    """Form for editing general application settings."""
    tunnel_name = StringField(
        'Tunnel Name',
        validators=[DataRequired(message="A tunnel name is required.")]
    )
    cf_zone_id = StringField(
        'Primary Cloudflare Zone ID',
        validators=[Optional()]
    )
    tunnel_dns_scan_zone_names = StringField(
        'Other Zones to Scan (comma-separated)',
        description="e.g. my-other-domain.com,another.dev",
        validators=[Optional()]
    )
    grace_period_seconds = IntegerField(
        'Grace Period (seconds)',
        validators=[DataRequired(message="Grace period is required.")]
    )
    preserve_unmanaged_cf_ingress_fields = BooleanField(
        'Preserve Unmanaged Cloudflare Ingress Fields'
    )
    dockflare_public_url = StringField(
        'DockFlare Public URL',
        validators=[Optional()]
    )
    submit_settings = SubmitField('Save General Settings')

class SecuritySettingsForm(FlaskForm):
    """Form for editing security settings."""
    disable_password_login = BooleanField(
        'Disable Password Login'
    )
    oauth_session_timeout = IntegerField(
        'OAuth Session Timeout (seconds)',
        default=86400,
        validators=[Optional()]
    )
    oauth_audit_enabled = BooleanField(
        'Enable OAuth Audit Logging',
        default=True
    )
    submit_security_settings = SubmitField('Save Security Settings')

class ChangePasswordForm(FlaskForm):
    """Form for changing the user's password."""
    current_password = PasswordField(
        'Current Password',
        validators=[DataRequired()]
    )
    new_password = PasswordField(
        'New Password',
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters long.")
        ]
    )
    confirm_new_password = PasswordField(
        'Confirm New Password',
        validators=[
            DataRequired(),
            EqualTo('new_password', message='New passwords must match.')
        ]
    )
    submit = SubmitField('Change Password')


class LoginForm(FlaskForm):
    """Form for the main login page."""
    username = StringField(
        'Username',
        validators=[DataRequired(message="Username is required.")]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(message="Password is required.")]
    )
    submit = SubmitField('Login')

class CloudflareCredentialsForm(FlaskForm):
    """Form for updating Cloudflare API credentials."""
    cf_account_id = StringField(
        'Cloudflare Account ID',
        validators=[Optional(), Length(min=32, max=32, message="Account ID must be 32 characters long.")]
    )
    cf_api_token = PasswordField(
        'Cloudflare API Token',
        validators=[Optional(), Length(min=40, max=100, message="API Token must be at least 40 characters long.")]
    )
    submit_cloudflare_credentials = SubmitField('Update Cloudflare Credentials')


class NotificationSettingsForm(FlaskForm):
    enabled = BooleanField('Enable notifications')
    replacement_urls = TextAreaField('Replacement Apprise URLs', validators=[Optional(), Length(max=131072)])
    clear_urls = BooleanField('Clear configured destinations')
    failure_cooldown_seconds = IntegerField(
        'Failure cooldown (seconds)',
        validators=[DataRequired(), NumberRange(min=60, max=86400)],
        default=900,
    )
    rule_activated = BooleanField('Rule activated')
    rule_restored = BooleanField('Rule restored')
    rule_pending_deletion = BooleanField('Rule pending deletion')
    rule_deleted = BooleanField('Rule deleted')
    cloudflare_tunnel_failure = BooleanField('Cloudflare tunnel failure')
    cloudflare_dns_failure = BooleanField('Cloudflare DNS failure')
    cloudflare_access_failure = BooleanField('Cloudflare Access failure')
    docker_listener_failure = BooleanField('Docker listener failure')
    agent_offline = BooleanField('Agent offline')
    agent_online = BooleanField('Agent recovered')
    agent_enrolled = BooleanField('Agent enrolled')
    agent_enrollment_failed = BooleanField('Agent enrollment failed')
    agent_decommission_started = BooleanField('Agent decommission started')
    agent_decommission_completed = BooleanField('Agent decommission completed')
    agent_decommission_failed = BooleanField('Agent decommission failed')
    agent_decommission_stalled = BooleanField('Agent decommission stalled')
    tunnel_down = BooleanField('Tunnel down')
    tunnel_recovered = BooleanField('Tunnel recovered')
    access_policy_created = BooleanField('Access Policy created')
    access_policy_updated = BooleanField('Access Policy updated')
    access_policy_deleted = BooleanField('Access Policy deleted')
    submit_notifications = SubmitField('Save notification settings')
