# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev

from flask_login import UserMixin


class User(UserMixin):
    """Simple user object for Flask-Login sessions.

    This class intentionally does not persist to any database. It only
    represents the authenticated admin user configured during setup.
    """

    def __init__(self, username: str):
        self.id = username


