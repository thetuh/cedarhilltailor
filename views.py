from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@views.route('/search-order', methods=['GET', 'POST'])
def search_order():
    return render_template('search-order.html')

@views.route('/create-order', methods=['GET', 'POST'])
@login_required
def create_order():
    return render_template('create-order.html')