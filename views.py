from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

views = Blueprint('views', __name__)

# [ GUEST ] ---

@views.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@views.route('/search-order', methods=['GET', 'POST'])
def search_order():
    return render_template('search-order.html')

# [ MANAGER ] ---

@views.route('/create-order', methods=['GET', 'POST'])
@login_required
def create_order():
    return render_template('create-order.html')

# [ ADMIN ] ---

@views.route('/manage-users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.id == 1:
        return render_template('manage-users.html')
    else:
        flash('Unauthorized access', category='error')
        return redirect(url_for('views.home'))