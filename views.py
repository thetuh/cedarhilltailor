from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from flask_paginate import Pagination, get_page_args
from auth import admin_required, manager_required
from sqlalchemy import desc, not_, func
from models import User, Role, Garment, Job, GarmentJobPair, Order, OrderItem, Customer, ItemJob, JobStatus, OrderStatus, Globals
from application import application, db
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
import traceback
import boto3
import json

views = Blueprint('views', __name__)

MAX_ITEMS_PER_PAGE = 8

# [ HELPER METHODS ] -----------------------------------------------
@views.route('/fetch-sales-tax-rate', methods=['GET'])
def fetch_sales_tax_rate():
    globals_record = Globals.query.first()
    if globals_record:
        return jsonify({'sales_tax_rate': float(globals_record.sales_tax_rate)})
    return jsonify({'sales_tax_rate': 0.0})

def get_sales_tax_rate():
    globals_record = Globals.query.first()
    if globals_record:
        return globals_record.sales_tax_rate
    return None

@views.route('/update-sales-tax-rate', methods=['POST'])
@login_required
@manager_required
def update_sales_tax_rate():
    try:
        data = request.json
        new_rate = float(data.get('new_rate', 0))

        # Not less than 0% or bigger than 100%
        if new_rate < 0 or new_rate > 1:
            return jsonify({'error': 'Invalid sales tax rate'}), 400

        # Fetch the existing Globals record
        globals_record = Globals.query.first()
        if globals_record is None:
            return jsonify({'error': 'Globals record not found'}), 404
        
        # Update the sales tax rate
        globals_record.sales_tax_rate = new_rate
        db.session.commit()  # Commit the changes to the database

        return jsonify({'success': True, 'new_rate': globals_record.sales_tax_rate}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def validate_order_input(first_name, last_name, phone_number, completion_date):
    errors = []
    if not first_name:
        errors.append('Please enter a first name')
    if not last_name:
        errors.append('Please enter a last name')
    if not phone_number:
        errors.append('Please enter a phone number')
    if not completion_date:
        errors.append('Please enter a completion date')
    return errors

def process_order_item(order_item_data, order_id):
    item_id = order_item_data.get('item_id')
    price = Decimal(order_item_data.get('price', 0))
    description = order_item_data.get('description', '')
    order = Order.query.get_or_404(order_id)

    if item_id and Decimal(item_id) != -1:  # Existing order item
        order_item = OrderItem.query.get_or_404(item_id)
        order_item.price = price
        order_item.description = description

        # Retrieve existing job pairs
        existing_item_jobs = ItemJob.query.filter_by(item_id=order_item.id).all()
        existing_pair_ids = {job.pair_id for job in existing_item_jobs}

        # Get the new pair IDs from the form
        pair_ids = order_item_data.get('jobs', [])
        new_pair_ids = set(pair_ids)

        # Determine pairs to delete (those that are in existing but not in new)
        pairs_to_delete = existing_pair_ids - new_pair_ids
        for pair_id in pairs_to_delete:
            job_to_delete = ItemJob.query.filter_by(item_id=order_item.id, pair_id=pair_id).first()
            if job_to_delete:
                db.session.delete(job_to_delete)

        # Add new job pairs that do not already exist
        for pair_id in new_pair_ids - existing_pair_ids:
            job_status = JobStatus.INCOMPLETE.value
            order.status = OrderStatus.INCOMPLETE.value
            new_item_job = ItemJob(item_id=order_item.id, pair_id=pair_id, status=job_status)
            db.session.add(new_item_job)

    else:  # New order item
        new_order_item = OrderItem(order_id=order_id, price=price, description=description)
        db.session.add(new_order_item)
        db.session.flush()  # Flush to get new_order_item.id

        # Add job pairs for the new order item
        pair_ids = order_item_data.get('jobs', [])
        for pair_id in pair_ids:
            job_status = JobStatus.INCOMPLETE.value
            order.status = OrderStatus.INCOMPLETE.value
            new_item_job = ItemJob(item_id=new_order_item.id, pair_id=pair_id, status=job_status)
            db.session.add(new_item_job)

def upload_image_to_bucket(file, filename):
    from application import bucket
    # Ensure filename is safe for saving
    filename = secure_filename(filename)
    blob = bucket.blob(f"images/{filename}")

    # Upload the file
    blob.upload_from_file(file, content_type=file.content_type)

    # Make the file publicly accessible (optional)
    blob.make_public()

    # Return the URL to the uploaded file
    return blob.public_url

# [ GUEST / SEAMSTRESS ROUTES ] -----------------------------------------------
@views.route('/')
def home():
    if current_user.is_authenticated:
        today = datetime.today()
        start_date = today - timedelta(days=6)

        # Query total price per day for the last 7 days
        results = (
            db.session.query(func.date(Order.order_date), func.sum(Order.price))
            .filter(Order.order_date >= start_date)
            .group_by(func.date(Order.order_date))
            .all()
        )

        # Query to calculate total revenue by garment type
        revenue_by_garment = (
            db.session.query(
                Garment.name,
                func.sum(OrderItem.price).label('total_revenue')
            )
            .join(ItemJob, OrderItem.id == ItemJob.item_id)  # Join ItemJob to OrderItem
            .join(GarmentJobPair, ItemJob.pair_id == GarmentJobPair.id)  # Join GarmentJobPair to ItemJob
            .join(Garment, GarmentJobPair.garment_id == Garment.id)  # Join Garment to GarmentJobPair
            .group_by(Garment.name)
            .order_by(func.sum(OrderItem.price).desc())
            .all()
        )

        # Prepare labels (garment names) and data (total revenue)
        revenue_by_garment_labels = [row[0] for row in revenue_by_garment]  # Garment names
        revenue_by_garment_data = [float(row[1]) for row in revenue_by_garment]  # Total revenue

        # Prepare data for the last 7 days
        last_7_days = [(today - timedelta(days=i)).strftime('%A') for i in range(6, -1, -1)]
        last_7_days_prices = {day: 0 for day in last_7_days}

        for order_date_str, total_price in results:
            # Ensure `order_date_str` is a string and convert to a datetime.date object
            if isinstance(order_date_str, str):
                order_date = datetime.strptime(order_date_str, '%Y-%m-%d').date()
            else:
                order_date = order_date_str  # Already a date object

            day = order_date.strftime('%A')
            last_7_days_prices[day] = float(total_price)

        # Prepare data for the chart
        labels = list(last_7_days_prices.keys())
        prices = list(last_7_days_prices.values())

        return render_template(
            'home.html', 
            last_7_days=labels, 
            last_7_days_prices=prices, 
            revenue_by_garment_labels=revenue_by_garment_labels, 
            revenue_by_garment_data=revenue_by_garment_data
        )

    return render_template('home.html')

@views.route('/search-orders')
def search_orders():
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    per_page = MAX_ITEMS_PER_PAGE

    # Get filter and sort options from request arguments
    order_id = request.args.get('order_id')

    phone_number = request.args.get('phone_number')
    if phone_number:
        phone_number = phone_number.replace('-', '')

    status = request.args.get('status')
    start_date = request.args.get('order_start_date')
    end_date = request.args.get('order_end_date')
    completion_start_date = request.args.get('completion_start_date')
    completion_end_date = request.args.get('completion_end_date')
    sort_by = request.args.get('sort_by', 'order_date_desc')

    # Base query with join to Customer for phone number filtering
    query = Order.query.join(Customer).filter(Customer.id == Order.customer_id)

    # Apply filters
    if order_id:
        query = query.filter(Order.id == order_id)
    if phone_number:
        query = query.filter(Customer.phone_number == phone_number)
    if status:
        query = query.filter(Order.status == int(status))
    if start_date:
        query = query.filter(Order.order_date >= start_date)
    if end_date:
        query = query.filter(Order.order_date <= end_date)
    if completion_start_date:
        query = query.filter(Order.completion_date >= completion_start_date)
    if completion_end_date:
        query = query.filter(Order.completion_date <= completion_end_date)

    # Apply sorting
    if sort_by == 'order_id_asc':
        query = query.order_by(Order.id.asc())
    else:
        query = query.order_by(Order.id.desc())
    
    # Paginate results
    order_pagination = query.paginate(page=page, per_page=per_page)

    return render_template('search-orders.html', order_pagination=order_pagination)

@views.route('/search-id/<int:order_id>')
def search_id(order_id):
    page, per_page, offset = get_page_args(page_parameter='page',
                                        per_page_parameter='per_page')

    per_page = MAX_ITEMS_PER_PAGE

    order_pagination = Order.query.filter_by(id=order_id).paginate(page=page, per_page=per_page)

    return render_template('search-id.html', order_pagination=order_pagination, order_id=order_id)

@views.route('/search-number/<phone_number>')
def search_number(phone_number):
    stripped_phone_number = phone_number.replace('-', '')

    page, per_page, offset = get_page_args(page_parameter='page',
                                            per_page_parameter='per_page')

    per_page = MAX_ITEMS_PER_PAGE

    cid = -1
    customer = Customer.query.filter_by(phone_number=stripped_phone_number).order_by(Customer.id.desc()).first()
    if customer:
        cid = customer.id

    order_pagination = Order.query.filter_by(customer_id=cid).order_by(Order.id.desc()).paginate(page=page, per_page=per_page)

    return render_template('search-number.html', order_pagination=order_pagination, phone_number=phone_number)

@views.route('/get-order-items/<int:order_id>')
@login_required
def get_order_items(order_id):
    order = Order.query.get_or_404(order_id)
    
    output = []
    for order_item in order.order_items:
        item_data = { 'item_id' : order_item.id,
        'garment_id' : order_item.item_jobs[0].pair.garment.id,
        'pair_ids' : [item_job.pair_id for item_job in order_item.item_jobs],
        'job_ids' : [item_job.pair.job.id for item_job in order_item.item_jobs],
        'price' : order_item.price,
        'description' : order_item.description }
    
        output.append(item_data)
    
    return { "order_items" : output }

# 'Soft' edit for job status
@views.route('/search-id/edit', methods=['GET', 'POST'])
@login_required
def edit_order():
    if request.method == 'POST':
        order_id = request.form.get('id')
        print(order_id)
        order = Order.query.get(order_id)
        if not order:
            flash('Order not found', category='error')
            return redirect(url_for('views.search_order'))

        # Add code to handle editing the order
    return redirect(url_for('views.search_order'))

# [ MANAGER ROUTES ] ---------------------------------------------
@views.route('/create-order', methods=['GET', 'POST'])
@login_required
@manager_required
def create_order():
    garment_list = Garment.query.order_by(Garment.name).all()
    
    if request.method == 'POST':
        first_name = request.form.get('first-name')
        last_name = request.form.get('last-name')
        phone_number = request.form.get('phone-number').replace('-', '')
        completion_date_str = request.form.get('date')

        # Validate input
        errors = validate_order_input(first_name, last_name, phone_number, completion_date_str)
        if errors:
            flash(' '.join(errors), category='error')
            return render_template('create-order.html', garment_list=garment_list)

        # Convert completion date string to date object
        try:
            completion_date = datetime.strptime(completion_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid completion date format. Please use YYYY-MM-DD', category='error')
            return render_template('create-order.html', garment_list=garment_list)

        subtotal = Decimal(0)  # Initialize total price
        order_items_data = []

        # Retrieve and parse all order items
        order_item_json_list = request.form.getlist('item[]')
        for order_item_json in order_item_json_list:
            order_item = json.loads(order_item_json)
            price = Decimal(order_item.get('price', 0))
            subtotal += price  # Add to subtotal
            order_items_data.append(order_item)

        sales_tax = subtotal * Decimal(get_sales_tax_rate())  # Calculate sales tax
        total_price = subtotal + sales_tax  # Calculate total price including tax

        # Check if customer exists or create a new one
        customer = Customer.query.filter_by(phone_number=phone_number).first()
        if not customer:
            customer = Customer(first_name=first_name, last_name=last_name, phone_number=phone_number)
            db.session.add(customer)
            db.session.flush()  # Flush to get customer ID

        try:
            # Create new order
            new_order = Order(
                customer_id=customer.id,
                price=total_price,  # Use the calculated total price
                order_date=datetime.now().date(),
                completion_date=completion_date,
                status=OrderStatus.INCOMPLETE.value
            )
            db.session.add(new_order)
            db.session.flush()  # Flush to get order ID

            # Add order items and job pairs
            for order_item in order_items_data:
                new_order_item = OrderItem(
                    order_id=new_order.id,
                    price=Decimal(order_item.get('price', 0)),  # Price for each item
                    description=order_item.get('description', '')
                )
                db.session.add(new_order_item)
                db.session.flush()  # Flush to get order item ID

                # Add job pairs (many-to-many relationship)
                pair_ids = order_item.get('jobs', [])
                for pair_id in pair_ids:
                    job_status = JobStatus.INCOMPLETE.value
                    new_item_job = ItemJob(item_id=new_order_item.id, pair_id=pair_id, status=job_status)
                    db.session.add(new_item_job)

            # Commit after all operations
            db.session.commit()
            flash(f'Successfully created order ID #{new_order.id}', category='success')

        except Exception as e:
            db.session.rollback()  # Rollback in case of an error
            flash(f"An error occurred while creating the order: {str(e)}", category='error')
            return render_template('create-order.html', garment_list=garment_list)

    return render_template('create-order.html', garment_list=garment_list)

@views.route('/edit-order/<int:order_id>', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_order_hard(order_id):
    order = Order.query.get_or_404(order_id)
    garment_list = Garment.query.order_by(Garment.name).all()

    if request.method == 'GET':
        return render_template('edit-order.html', order=order, garment_list=garment_list)

    elif request.method == 'POST':
        first_name = request.form.get('first-name')
        last_name = request.form.get('last-name')
        phone_number = request.form.get('phone-number').replace('-', '')
        completion_date_str = request.form.get('date')

        try:
            completion_date = datetime.strptime(completion_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid completion date format. Please use YYYY-MM-DD', category='error')
            return render_template('edit-order.html', order=order, garment_list=garment_list)

        # Validate inputs
        errors = validate_order_input(first_name, last_name, phone_number, completion_date_str)
        if errors:
            flash(' '.join(errors), category='error')
            return render_template('edit-order.html', order=order, garment_list=garment_list)

        total_price = 0
        order_item_json_list = request.form.getlist('item[]')

        try:
            # Get existing order items
            existing_order_items = OrderItem.query.filter(OrderItem.order_id == order.id).all()
            existing_item_job_ids = [item.id for item in existing_order_items]

            deleted_item_json_list = request.form.getlist('deleted[]')
            for deleted_item_json in deleted_item_json_list:
                try:
                    # Ensure data is valid JSON
                    data = json.loads(deleted_item_json)
                    
                    # Check if data is a list of item IDs
                    if isinstance(data, list):
                        for item_id in data:
                            try:
                                order_item = OrderItem.query.get(Decimal(item_id))
                                if order_item:
                                    db.session.delete(order_item)
                                    ItemJob.query.filter(ItemJob.item_id == order_item.id).delete()
                            except ValueError:
                                flash(f"Invalid item ID format: {item_id}", category='error')
                    else:
                        flash('Invalid format for deleted items. Expected a list', category='error')

                except json.JSONDecodeError:
                    flash('Error decoding deleted items. Ensure valid JSON format', category='error')


            # Process order items
            for order_item_entry in order_item_json_list:
                order_item_data = json.loads(order_item_entry)
                total_price += Decimal(order_item_data.get('price', 0))
                process_order_item(order_item_data, order_id=order.id)

            total_price += Decimal(get_sales_tax_rate()) * total_price

            # Update order price
            order.price = total_price
            order.completion_date = completion_date  # Update the completion date
            db.session.commit()
            flash(f'Successfully edited order ID #{order_id}', category='success')

        except Exception as e:
            db.session.rollback()
            error_message = f"An error occurred: {str(e)} at line {traceback.extract_tb(e.__traceback__)[0][1]}"
            flash(error_message, category='error')

    return redirect(url_for('views.search_orders'))

# Get jobs related to a specific garment
@views.route('/get_jobs_for_garment/<int:garment_id>')
@login_required
@manager_required
def get_jobs_for_garment(garment_id):
    garment = Garment.query.get(garment_id)
    if garment:
        jobs = garment.jobs
        return jsonify({"jobs": [{"id": job.id, "name": job.name} for job in jobs]})
    return jsonify({"jobs": []}), 404  # Return a 404 error if garment is not found

# Get job pairs based on garment and job IDs
@views.route('/get_job_pairs/<int:garment_id>/<job_ids>')
@login_required
@manager_required
def get_job_pairs(garment_id, job_ids):
    job_ids_list = job_ids.split(",")
    
    # Convert to integers and filter out invalid IDs
    job_ids_list = [int(job_id) for job_id in job_ids_list if job_id.isdigit()]
    selected_jobs = Job.query.filter(Job.id.in_(job_ids_list)).all()
    
    job_pairs = [
        job_pair.id for job in selected_jobs
        for job_pair in GarmentJobPair.query.filter_by(garment_id=garment_id, job_id=job.id).all()
    ]

    return jsonify({"jobPairs": job_pairs})

# Calculate total price based on garment and job IDs
@views.route('/calculate_total_price/<int:garment_id>/<job_ids>')
@login_required
@manager_required
def calculate_total_price(garment_id, job_ids):
    job_ids_list = job_ids.split(",")
    
    # Convert to integers and filter out invalid IDs
    job_ids_list = [int(job_id) for job_id in job_ids_list if job_id.isdigit()]
    selected_jobs = Job.query.filter(Job.id.in_(job_ids_list)).all()
    
    total_price = 0
    job_pairs = []
    
    for job in selected_jobs:
        price_entry = GarmentJobPair.query.filter_by(garment_id=garment_id, job_id=job.id).first()
        
        if price_entry:
            total_price += price_entry.price
            job_pairs.append(price_entry.id)
            
    return jsonify({"totalPrice": total_price, "jobPairs": job_pairs})

@views.route('/store')
@login_required
@manager_required
def manage_store():
    return render_template('store.html')

@views.route('/store/garments')
@login_required
@manager_required
def garments():
    page, per_page, offset = get_page_args(page_parameter='page',
                                           per_page_parameter='per_page')

    per_page = MAX_ITEMS_PER_PAGE

    # Query the Garment table and get paginated data
    garments_pagination = Garment.query.order_by(Garment.name).paginate(page=page, per_page=per_page)

    return render_template('garments.html', garments_pagination=garments_pagination)

@views.route('/store/jobs')
@login_required
@manager_required
def jobs():
    page, per_page, offset = get_page_args(page_parameter='page',
                                           per_page_parameter='per_page')

    per_page = MAX_ITEMS_PER_PAGE

    garment_list = Garment.query.order_by(Garment.name).all()

    # Query the Garment table and get paginated data
    jobs_pagination = Job.query.order_by(Job.name).paginate(page=page, per_page=per_page)

    return render_template('jobs.html', jobs_pagination=jobs_pagination, garment_list=garment_list)

@views.route('/store/pairs', methods=['GET', 'POST'])
@login_required
@manager_required
def pairs():
    garment_list = Garment.query.order_by(Garment.name).all()
    job_list = Job.query.order_by(Job.name).all()

    garment_job_pairs = []
    garment_id = None  # Initialize garment_id to None

    if request.method == 'POST':
        garment_id = request.form.get('garment_id')
        if garment_id:
            garment_job_pairs = GarmentJobPair.query.filter_by(garment_id=garment_id).all()

    return render_template('pairs.html', 
                           garment_list=garment_list, 
                           garment_job_pairs=garment_job_pairs, 
                           job_list=job_list, 
                           garment_id=garment_id)  # Pass garment_id to the template

# [ ADMIN ROUTES ] -----------------------------------------------
@views.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.filter(not_(User.username == 'admin')).order_by(User.role_id.asc()).all()
    available_roles = Role.query.all()
    return render_template('users.html', users=users, available_roles=available_roles)

@views.route('/performance')
@login_required
@admin_required
def performance():
    return render_template('performance.html')

@views.route('/revenue')
@login_required
@admin_required
def revenue():
    return render_template('revenue.html')

@views.route('/analytics')
@login_required
@admin_required
def analytics():
    return render_template('analytics.html')

@views.route('/store/garments/delete/<int:id>')
@login_required
@manager_required
def delete_garment(id):
    garment = Garment.query.get(id)
    if not garment:
        flash('Garment not found', category='error')
        return redirect(url_for('views.garments'))

    db.session.delete(garment)
    db.session.commit()

    flash(f"Successfully deleted' '{garment.name}'", category='success')
    return redirect(url_for('views.garments'))

@views.route('/store/jobs/delete/<int:id>')
@login_required
@manager_required
def delete_job(id):
    job = Job.query.get(id)
    if not job:
        flash('Job not found', category='error')
        return redirect(url_for('views.jobs'))

    db.session.delete(job)
    db.session.commit()

    flash(f"Successfully deleted' '{job.name}'", category='success')
    return redirect(url_for('views.jobs'))

@views.route('/store/pairs/delete/<int:id>')
@login_required
@manager_required
def delete_pair(id):
    pair = GarmentJobPair.query.get(id)
    if not pair:
        flash('Pair not found', category='error')
        return redirect(url_for('views.pairs'))

    db.session.delete(pair)  # This will also delete related ItemJob instances
    db.session.commit()

    flash("Successfully deleted pair", category='success')
    return redirect(url_for('views.pairs'))

@views.route('/update-status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
    order = Order.query.get(order_id)
    order_complete = 1

    for order_item in order.order_items:
        for item_job in order_item.item_jobs:
            checkbox_name = f'job_status_{item_job.item_id}_{item_job.pair_id}'
            
            if request.form.get(checkbox_name):  # If the job is marked as complete
                item_job.status = 1
                
                # If the job was incomplete before, record completion details
                if item_job.completed_by_id is None:
                    item_job.completed_by_id = current_user.id  # Track the user who completed it
                    item_job.completion_time = datetime.utcnow()  # Set completion time
            else:
                item_job.status = 0
                item_job.completed_by_id = None
                item_job.completion_time = None
                order_complete = 0  # If any item is incomplete, the entire order is incomplete

    order.status = order_complete
    db.session.commit()
    
    flash('Job statuses updated successfully', 'success')
    return redirect(url_for('views.search_orders', order_id=order_id))

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

@views.route('/store/garments/create', methods=['GET', 'POST'])
@login_required
@manager_required
def create_garment():
    if request.method == 'POST':
        name = request.form.get('name').strip()

        errors = []
        if not name:
            errors.append('Please enter a valid garment name')
        
        garment = Garment.query.filter_by(name=name).first()
        if garment:
            errors.append(f"Garment '{name}' already exists")

        if errors:
            flash(' '.join(errors), category='error')
            return redirect(url_for('views.garments'))

        new_garment = Garment(name=name)
        db.session.add(new_garment)
        db.session.commit()

        flash(f"Successfully added '{name}'", category='success')
        return redirect(url_for('views.garments'))

    return render_template('garments.html')

@views.route('/store/jobs/create', methods=['GET', 'POST'])
@login_required
@manager_required
def create_job():
    if request.method == 'POST':
        name = request.form.get('name').strip()

        # Validation
        if not name:
            flash('Please enter a valid job name', category='error')
            return redirect(url_for('views.jobs'))

        # Check if job already exists
        if Job.query.filter_by(name=name).first():
            flash(f"Job '{name}' already exists", category='error')
            return redirect(url_for('views.jobs'))

        # Create and commit new job
        new_job = Job(name=name)
        db.session.add(new_job)
        db.session.commit()

        flash(f"Successfully added '{name}'", category='success')
        return redirect(url_for('views.jobs'))

    return render_template('jobs.html')

@views.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        role_name = request.form.get('role').strip()

        errors = []

        # Sanity checks
        if not username:
            errors.append('Please enter a valid username')
        if not password:
            errors.append('Please enter a valid password')

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            errors.append(f"Username '{username}' already exists")

        # Handle errors
        if errors:
            flash(' '.join(errors), category='error')
            return redirect(url_for('views.manage_users'))

        # Find role by name
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            flash('Invalid role', category='error')
            return redirect(url_for('views.create_user'))

        # Create user
        new_user = User(username=username, password=generate_password_hash(password, method='sha256'), role_id=role.id)
        db.session.add(new_user)
        db.session.commit()

        flash(f"Successfully added '{username}'", category='success')
        return redirect(url_for('views.manage_users'))

    return render_template('users.html')

@views.route('/store/garments/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_garment():
    if request.method == 'POST':
        garment_id = request.form.get('id')
        name = request.form.get('name').strip()

        # Retrieve garment
        garment = Garment.query.get(garment_id)
        if not garment:
            flash('Garment not found', category='error')
            return redirect(url_for('views.garments'))

        # Validation
        if not name:
            flash('Please enter a valid garment name', category='error')
            return redirect(url_for('views.garments'))

        # Update garment
        garment.name = name
        db.session.commit()

        flash(f"Successfully updated '{garment.name}'", category='success')
        return redirect(url_for('views.garments'))

    return render_template('garments.html')

@views.route('/store/jobs/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_job():
    if request.method == 'POST':
        job_id = request.form.get('id')
        name = request.form.get('name').strip()

        # Retrieve job
        job = Job.query.get(job_id)
        if not job:
            flash('Job not found', category='error')
            return redirect(url_for('views.jobs'))

        # Validation
        if not name:
            flash('Please enter a valid job name', category='error')
            return redirect(url_for('views.jobs'))

        # Update job
        job.name = name
        db.session.commit()

        flash(f"Successfully updated '{job.name}'", category='success')
        return redirect(url_for('views.jobs'))

    return render_template('jobs.html')

@views.route('/store/pairs/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_pair():
    if request.method == 'POST':
        pair_id = request.form.get('id')
        price = request.form.get('price')

        # Retrieve pair
        pair = GarmentJobPair.query.get(pair_id)
        if not pair:
            flash('pair not found', category='error')
            return redirect(url_for('views.pairs'))

        # Validation
        if not price:
            flash('Please enter a valid price', category='error')
            return redirect(url_for('views.pairs'))

        # Update pair
        pair.price = price
        db.session.commit()

        flash(f"Successfully updated pair", category='success')
        return redirect(url_for('views.pairs'))

    return render_template('pairs.html')

@views.route('/store/pairs/create', methods=['GET', 'POST'])
@login_required
@manager_required
def create_garment_job_pair():
    if request.method == 'POST':
        garment_id = request.form.get('garment_id')
        job_id = request.form.get('job_id')
        price = request.form.get('price')

        errors = []
        if not garment_id:
            errors.append('Please select a valid garment')
        if not job_id:
            errors.append('Please select a valid job')
        if not price or Decimal(price) <= 0:
            errors.append('Please enter a valid price')

        # Check for existing garment-job pair
        if GarmentJobPair.query.filter_by(garment_id=garment_id, job_id=job_id).first():
            errors.append('This garment-job pair already exists')

        if errors:
            flash(' '.join(errors), category='error')
            return redirect(url_for('views.pairs'))

        try:
            new_pair = GarmentJobPair(garment_id=garment_id, job_id=job_id, price=Decimal(price))
            db.session.add(new_pair)
            db.session.commit()
            flash(f'Successfully created garment-job pair', category='success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', category='error')

        return redirect(url_for('views.pairs'))

    garment_list = Garment.query.order_by(Garment.name).all()
    job_list = Job.query.order_by(Job.name).all()
    return render_template('pairs.html', garment_list=garment_list, job_list=job_list)

@views.route('/users/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user():
    if request.method == 'POST':
        user_id = request.form.get('id')
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        role_name = request.form.get('role').strip()

        # Retrieve user
        user = User.query.get(user_id)
        if not user:
            flash('User not found', category='error')
            return redirect(url_for('views.manage_users'))

        errors = []

        # Validation
        if not username:
            errors.append('Please enter a valid username')

        # Handle errors
        if errors:
            flash(' '.join(errors), category='error')
            return redirect(url_for('views.manage_users'))

        # Update username and password
        user.username = username
        if password:
            user.password = generate_password_hash(password, method='sha256')

        # Update role
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            flash('Invalid role', category='error')
            return redirect(url_for('views.manage_users'))

        user.role_id = role.id
        db.session.commit()

        flash(f"Successfully updated '{user.username}'", category='success')
        return redirect(url_for('views.manage_users'))

    return render_template('edit-user.html')
