from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_required, current_user
from application import db
from models import User

views = Blueprint('views', __name__)

# Custom decorator for authorization
def admin_required(func):
    def decorated_func(*args, **kwargs):
        if current_user.id == 1:
            return func(*args, **kwargs)
        else:
            flash('Unauthorized access', category='error')
            return redirect(url_for('views.home'))
    decorated_func.__name__ = func.__name__  # Preserve the original function name
    return decorated_func

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
@admin_required
def manage_users():
    users = User.query.filter(User.id != 1).all()
    return render_template('users.html', users=users)

@views.route('/users/delete/<int:id>')
@login_required
@admin_required
def delete_user(id):
    user = User.query.get(id)
    if not user:
        flash('User not found', category='error')
        return redirect(url_for('views.manage_users'))

    db.session.delete(user)
    db.session.commit()

    flash(f"Successfully deleted '{user.username}'", category='success')
    return redirect(url_for('views.manage_users'))

@views.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        error = []

        # Sanity checks
        if not username:
            error.append('Please enter a valid username')
        elif not password:
            error.append('Please enter a valid password')

        user = User.query.filter_by(username=username).first()
        if user:
            error.append(f"Username '{username}' already exists")

        # Error message display
        if error:
            error_message = ' '.join(error)
            flash(error_message, category='error')
            return redirect(url_for('views.manage_users'))

        new_user = User(username=username, password=generate_password_hash(password, method='sha256'))
        db.session.add(new_user)
        db.session.commit()

        flash(f"Successfully added '{username}'", category='success')
        return redirect(url_for('views.manage_users')) 

    return render_template('create-user.html')

@views.route('/users/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user():
    if request.method == 'POST':
        user_id = request.form.get('id')
        user = User.query.get(user_id)
        if not user:
            flash('User not found', category='error')
            return redirect(url_for('views.manage_users'))

        username = request.form.get('username')
        password = request.form.get('password')

        error = []

        # Sanity checks
        if not username:
            error.append('Please enter a valid username')
        if not password:
            error.append('Please enter a valid password')
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

        flash(f"Successfully updated '{user.username}'", category='success')
        return redirect(url_for('views.manage_users'))

    return render_template('edit-user.html')
