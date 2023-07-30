from application import db
from flask_login import UserMixin

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    
    # Define the many-to-many relationship with roles
    roles = db.relationship('Role', secondary='user_roles', backref=db.backref('users', lazy=True))

# Association table for the many-to-many relationship between users and roles
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

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

    # Define the one-to-many relationship with jobs
    jobs = db.relationship('Job', backref='garment', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False, index=True)
    garment_id = db.Column(db.Integer, db.ForeignKey('garment.id'), nullable=False, index=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    garment_id = db.Column(db.Integer, db.ForeignKey('garment.id'), nullable=False, index=True)
    price = db.Column(db.DECIMAL(10, 2), nullable=False, index=True)
    job_name = db.Column(db.String(100))
