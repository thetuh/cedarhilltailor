from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_required, current_user
from flask_paginate import Pagination, get_page_args
from auth import admin_required, manager_required
from sqlalchemy import desc, not_
from models import User, Role, Garment, Job, garment_job_pair, Order, OrderItem, Customer, ItemJob
from application import application, db
from datetime import datetime
from decimal import Decimal
import json

views = Blueprint('views', __name__)

MAX_ITEMS_PER_PAGE = 8

# [ GUEST ] ---

@views.route('/')
def home():
    return render_template('home.html')

@views.route('/search-id/<int:order_id>')
def search_id(order_id):
    page, per_page, offset = get_page_args(page_parameter='page',
                                        per_page_parameter='per_page')

    per_page = MAX_ITEMS_PER_PAGE

    order_pagination = Order.query.filter_by(id=order_id).paginate(page=page, per_page=per_page)

    return render_template('search-id.html', order_pagination=order_pagination, order_id=order_id)

@views.route('/search-order')
def search_order():
    return render_template('search-order.html')

# [ MANAGER ] ---

@views.route('/create-order', methods=['GET', 'POST'])
@login_required
@manager_required
def create_order():
    if request.method == 'POST':
        first_name = request.form.get('first-name')
        last_name = request.form.get('last-name')
        phone_number = request.form.get('phone-number').replace('-', '')
        completion_date = request.form.get('date')

        errors = []

        # Input Validation
        if not first_name:
            errors.append('Please enter a first name')
        elif not last_name:
            errors.append('Please enter a last name')
        elif not phone_number:
            errors.append('Please enter a phone number')
        elif not completion_date:
            errors.append('Please enter a completion date')

        # Error message display
        if errors:
            error_message = ' '.join(errors)
            flash(error_message, category='error')
            return render_template('create-order.html')

        total_price = 0
        order_item_json_list = request.form.getlist('item[]')
        for order_item_json in order_item_json_list:
                total_price += Decimal(json.loads(order_item_json).get('price'))

        try:
            # Check if customer already exists
            customer = Customer.query.filter_by(phone_number=phone_number).first()
            if not customer:
                customer = Customer(first_name=first_name,last_name=last_name,phone_number=phone_number)
                db.session.add(customer)
                db.session.flush()
            
            new_order = Order(customer_id=customer.id,price=Decimal(total_price), order_date=datetime.now().date(), completion_date=completion_date)
            db.session.add(new_order)
            db.session.flush()

            for order_item_json in order_item_json_list:
                order_item = json.loads(order_item_json)
                price = order_item.get('price')
                description = order_item.get('description')
                
                new_order_item = OrderItem(order_id=new_order.id, price=price, description=description)
                db.session.add( new_order_item )
                db.session.flush()

                pair_ids = order_item.get('jobs')
                for pair_id in pair_ids:
                    new_item_job = ItemJob(item_id=new_order_item.id, pair_id=pair_id)
                    db.session.add(new_item_job)
                
            # Commit after adding all order items
            db.session.commit()

        except Exception as e:
            db.session.rollback()  # Rollback the transaction in case of an error
            flash(f"An error occurred: {str(e)}", category='error')
            garment_list = Garment.query.order_by(Garment.name).all()
            return render_template('create-order.html', garment_list=garment_list)

    garment_list = Garment.query.order_by(Garment.name).all()
    return render_template('create-order.html', garment_list=garment_list)

@views.route('/get_jobs_for_garment/<int:garment_id>')
@login_required
@manager_required
def get_jobs_for_garment(garment_id):
    garment = Garment.query.get(garment_id)
    if garment:
        jobs = garment.jobs
        return jsonify({"jobs": [{"id": job.id, "name": job.name} for job in jobs]})
    else:
        return jsonify({"jobs": []})

@views.route('/get_job_pairs/<int:garment_id>/<job_ids>')
@login_required
@manager_required
def get_job_pairs(garment_id, job_ids):
    selected_jobs = Job.query.filter(Job.id.in_(job_ids.split(","))).all()
    
    job_pairs = []
    for job in selected_jobs:
        job_pair = db.session.query(garment_job_pair).filter_by(garment_id=garment_id, job_id=job.id).first()
        if job_pair:
            job_pairs.append(job_pair.id)

    return jsonify({"jobPairs": job_pairs})

@views.route('/calculate_total_price/<int:garment_id>/<job_ids>')
@login_required
@manager_required
def calculate_total_price(garment_id, job_ids):
    selected_jobs = Job.query.filter(Job.id.in_(job_ids.split(","))).all()
    
    total_price = 0
    job_pairs = []
    for job in selected_jobs:
        price_entry = db.session.query(garment_job_pair).filter_by(garment_id=garment_id, job_id=job.id).first()
        
        if price_entry:
            total_price += price_entry.price
            job_pairs.append(price_entry.id)
            
    return jsonify({"totalPrice": total_price, "jobPairs": job_pairs })

@views.route('/inventory')
@login_required
@manager_required
def manage_inventory():
    return render_template('inventory.html')

@views.route('/inventory/garments')
@login_required
@manager_required
def manage_garments():
    return render_template('garments.html')

@views.route('/inventory/jobs')
@login_required
@manager_required
def manage_jobs():
    return render_template('jobs.html')

@views.route('/inventory/garments/edit')
@login_required
@manager_required
def edit_garments():
    page, per_page, offset = get_page_args(page_parameter='page',
                                           per_page_parameter='per_page')

    per_page = MAX_ITEMS_PER_PAGE

    # Query the Garment table and get paginated data
    garments_pagination = Garment.query.order_by(Garment.name).paginate(page=page, per_page=per_page)

    return render_template('edit-garments.html', garments_pagination=garments_pagination)

@views.route('/inventory/jobs/edit')
@login_required
@manager_required
def edit_jobs():
    page, per_page, offset = get_page_args(page_parameter='page',
                                           per_page_parameter='per_page')

    per_page = MAX_ITEMS_PER_PAGE

    garment_list = Garment.query.order_by(Garment.name).all()

    # Query the Garment table and get paginated data
    jobs_pagination = Job.query.order_by(Job.name).paginate(page=page, per_page=per_page)

    return render_template('edit-jobs.html', jobs_pagination=jobs_pagination, garment_list=garment_list)

# [ ADMIN ] ---

@views.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.filter(not_(User.username == 'admin')).order_by(User.role_id.asc()).all()
    available_roles = Role.query.all()
    return render_template('users.html', users=users, available_roles=available_roles)

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
        role_name = request.form.get('role')

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

        role = Role.query.filter_by(name=role_name).first()
        if not role:
            flash('Invalid role', category='error')
            return redirect(url_for('views.create_user'))

        new_user = User(username=username, password=generate_password_hash(password, method='sha256'), role_id=role.id)
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
        role_name = request.form.get('role')

        error = []

        # Sanity checks
        if not username:
            error.append('Please enter a valid username')

        # Error message display
        if error:
            error_message = ' '.join(error)
            flash(error_message, category='error')
            return redirect(url_for('views.manage_users'))

        # Update the user object with new data
        user.username = username

        if password:
            user.password = generate_password_hash(password, method='sha256')

        # Update the user's role
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            flash('Invalid role', category='error')
            return redirect(url_for('views.manage_users'))

        user.role_id = role.id        
        db.session.commit()

        flash(f"Successfully updated '{user.username}'", category='success')
        return redirect(url_for('views.manage_users'))

    return render_template('edit-user.html')
