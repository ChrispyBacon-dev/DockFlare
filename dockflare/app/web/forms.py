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
# app/web/forms.py
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length

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