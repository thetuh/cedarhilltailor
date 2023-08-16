from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_required, current_user
from flask_paginate import Pagination, get_page_args
from auth import admin_required, manager_required
from sqlalchemy import desc, not_
from models import User, Role, Garment, Job, garment_job_association
from application import application, db

views = Blueprint('views', __name__)

MAX_ITEMS_PER_PAGE = 8

# [ GUEST ] ---

@views.route('/')
def home():
    return render_template('home.html')

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
        phone_number = request.form.get('phone-number')
        garment_id = request.form.get('garment')
        job_id = request.form.get('job')
        price = request.form.get('price')

        errors = []

        # Input Validation
        if not first_name:
            errors.append('Please enter a first name')
        elif not last_name:
            errors.append('Please enter a last name')
        elif not phone_number:
            errors.append('Please enter a phone number')
        elif not garment_id:
            errors.append('Please select a garment')
        elif not job_id:
            errors.append('Please select a job')
        elif not price:
            errors.append('Please input price')

        # Error message display
        if errors:
            error_message = ' '.join(errors)
            flash(error_message, category='error')
            return render_template('create-order.html')
    
        job = Job.query.filter_by(id=job_id).first()
        print(job.name)
    
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

@views.route('/calculate_total_price/<int:garment_id>/<job_ids>')
@login_required
@manager_required
def calculate_total_price(garment_id, job_ids):
    selected_jobs = Job.query.filter(Job.id.in_(job_ids.split(","))).all()
    
    total_price = 0
    for job in selected_jobs:
        price_query = db.session.query(garment_job_association).filter_by(garment_id=garment_id, job_id=job.id)
        price_entry = price_query.first()
        
        if price_entry:
            total_price += price_entry.price
            
    return jsonify({"totalPrice": total_price})

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
