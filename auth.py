from models import User
from flask import Blueprint, request, render_template, flash, redirect, url_for, session
from werkzeug.security import check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from alert import email_alert

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        error = []

        # Sanity checks
        if len(username) < 1:
            error.append('Please enter username')
        elif len(password) < 1:
            error.append('Please enter password')

        # Error message display
        if error:
            error_message = ' '.join(error)
            flash(error_message, category='error')
            return render_template('login.html')

        # Authentication
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session.pop('_flashes', None)
            flash('Logged in successfully', category='success')
            login_user(user, remember=True)
            # email_alert('Cedar Hill Alteration - Login Alert', user.username + " logged in from I.P. address " + request.remote_addr, 'email@gmail.com')
            return redirect(url_for('views.home'))
        else:
            flash('Invalid login', category='error')


    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    session.pop('_flashes', None)
    flash('Logged out successfully', category='success')
    logout_user()
    return redirect(url_for('auth.login'))