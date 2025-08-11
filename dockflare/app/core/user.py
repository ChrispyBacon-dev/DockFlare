from flask_login import UserMixin

class User(UserMixin):
    """
    A simple user class for Flask-Login.
    This class is not a database model but a representation of the logged-in user.
    """
    def __init__(self, username):
        self.id = username
