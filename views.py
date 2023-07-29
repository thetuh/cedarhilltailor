from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_required, current_user
from application import db
from models import User

views = Blueprint('views', __name__)

# [ GUEST ] ---

@views.route('/')
def home():
    return render_template('home.html')

@views.route('/search-order')
def search_order():
    return render_template('search-order.html')

# [ MANAGER ] ---

@views.route('/create-order')
@login_required
def create_order():
    return render_template('create-order.html')

# [ ADMIN ] ---

@views.route('/users')
@login_required
def manage_users():
    if current_user.id == 1:
        # Query all users except the admin user to prevent accidental deletion
        users = User.query.filter(User.id != 1).all()
        return render_template('users.html', users=users)
    else:
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))

@views.route('/users/delete/<id>')
@login_required
def delete_user(id):
    if current_user.id == 1:
        user = User.query.get(id)
        if not user:
            flash('User not found', category='error')
            return redirect(url_for('views.manage_users'))
        
        db.session.delete(user)
        db.session.commit()

        flash("Successfully deleted '" + user.username + "'", category='success')
        return redirect(url_for('views.manage_users'))
    else:
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))

@views.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.id == 1:
        username = request.form.get('username')
        password = request.form.get('password')

        error = []

        # Sanity checks
        if len(username) < 1:
            error.append('Please enter valid username')
        elif len(password) < 1:
            error.append('Please enter valid password')

        user = User.query.filter_by(username=username).first()
        if user:
            error.append("Username '" + username + ' already exists')

        new_user = User(username=username, password=generate_password_hash(password, method='sha256'))
        db.session.add(new_user)
        db.session.commit()

        flash("Successfully added '" + username + "'", category='success')
        return redirect(url_for('views.manage_users')) 
    else:
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))

@views.route('/users/edit', methods=['GET', 'POST'])
@login_required
def edit_user():
    if current_user.id == 1:
        if request.method == 'POST':
            user = User.query.get(request.form.get('id'))
            if not user:
                flash('User not found', category='error')
                return redirect(url_for('views.manage_users'))

            username = request.form.get('username')
            password = request.form.get('password')

            error = []

            # Sanity checks
            if len(username) < 1:
                error.append('Please enter valid username')
            elif len(password) < 1:
                error.append('Please enter valid password')
            elif check_password_hash(user.password, password):
                error.append('Password is already in use')

            # Error message display
            if error:
                error_message = ' '.join(error)
                flash(error_message, category='error')
                return redirect(url_for('views.manage_users'))

            # Update the user object with new data
            user.username = username
            user.password = generate_password_hash(password, method='sha256')
            db.session.commit()

            flash("Successfully updated '" + user.username + "'", category='success')
            return redirect(url_for('views.manage_users'))
    else:
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))