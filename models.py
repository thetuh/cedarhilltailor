from application import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150), nullable=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), index=True)
    email = db.Column(db.String(150), unique=True)
    phone_number = db.Column(db.String(20), index=True)

    # Define the one-to-many relationship with orders
    orders = db.relationship('Order', backref='customer', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False, index=True)
    order_date = db.Column(db.Date, index=True)

    # Define the one-to-many relationship with order items
    order_items = db.relationship('OrderItem', backref='order', lazy=True)

class Garment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    garment_name = db.Column(db.String(100))
    price = db.Column(db.DECIMAL(10, 2), nullable=False, index=True)

    # Define the one-to-many relationship with jobs
    jobs = db.relationship('Job', backref='garment', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False, index=True)
    garment_id = db.Column(db.Integer, db.ForeignKey('garment.id'), nullable=False, index=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    garment_id = db.Column(db.Integer, db.ForeignKey('garment.id'), nullable=False, index=True)
    job_name = db.Column(db.String(100))

