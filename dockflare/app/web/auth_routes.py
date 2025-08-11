from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import check_password_hash
from app.core.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth', template_folder='../templates')

class LoginForm(FlaskForm):
    """Form for the login page."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles the user login process."""
    if current_user.is_authenticated:
        return redirect(url_for('web.status_page'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        stored_username = current_app.config.get('DOCKFLARE_USERNAME')
        stored_hash = current_app.config.get('DOCKFLARE_PASSWORD_HASH')

        if username == stored_username and stored_hash and check_password_hash(stored_hash, password):
            user = User(username)
            login_user(user)

            next_page = request.args.get('next')
            return redirect(next_page or url_for('web.status_page'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html', form=form, title="Login")

@auth_bp.route('/logout')
def logout():
    """Handles the user logout process."""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
