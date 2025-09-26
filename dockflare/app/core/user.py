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
# dockflare/app/core/user.py
from flask_login import UserMixin
from datetime import datetime
from flask import current_app

class User(UserMixin):
    def __init__(self, username, auth_method='password', session_data=None):
        self.id = username
        self.auth_method = auth_method
        self.session_data = session_data or {}
        self.login_time = datetime.utcnow()

    @property
    def is_oauth_user(self):
        return self.auth_method == 'oauth'

    def is_session_valid(self, max_age_seconds=None):
        if max_age_seconds is None:
            max_age_seconds = current_app.config.get('OAUTH_SESSION_TIMEOUT', 86400)

        age = (datetime.utcnow() - self.login_time).total_seconds()
        return age < max_age_seconds
