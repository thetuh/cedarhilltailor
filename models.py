from application import db
from flask_login import UserMixin

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    # one-to-many (User)
    users = db.relationship('User', backref='role', lazy=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    # FK (Role)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False, index=True)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), index=True)
    email = db.Column(db.String(150), unique=True)
    phone_number = db.Column(db.String(20), index=True)

    # one-to-many (Order)
    orders = db.relationship('Order', backref='customer', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.Date, index=True)

    # FK (Customer)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False, index=True)

    # one-to-many (Garment)
    garments = db.relationship('Garment', backref='order', lazy=True)

class Garment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    garment_name = db.Column(db.String(100))

    # FK (Order)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False, index=True)

    # one-to-many (Job)
    jobs = db.relationship('Job', backref='garment', lazy=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.DECIMAL(10, 2), nullable=False, index=True)
    job_name = db.Column(db.String(100))

    # FK (Garment)
    garment_id = db.Column(db.Integer, db.ForeignKey('garment.id'), nullable=False, index=True)
