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

# Association table for the many-to-many relationship between orders and garments
order_garment_association = db.Table(
    'order_garment_association',
    db.Column('order_id', db.Integer, db.ForeignKey('order.id'), primary_key=True),
    db.Column('garment_id', db.Integer, db.ForeignKey('garment.id'), primary_key=True)
)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(150), index=True)
    customer_phone_number = db.Column(db.String(20), index=True)

    order_date = db.Column(db.Date, index=True)
    completion_date = db.Column(db.Date, index=True)

    # many-to-many (Garment)
    garments = db.relationship('Garment', secondary=order_garment_association, backref='orders', lazy=True)

class Garment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    garment_name = db.Column(db.String(100))

    # many-to-many (Order)
    orders = db.relationship('Order', secondary=order_garment_association, backref='garments', lazy=True)

    # one-to-many (Job)
    jobs = db.relationship('Job', backref='garment', lazy=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.DECIMAL(10, 2), nullable=False, index=True)
    job_name = db.Column(db.String(100))

    # FK (Garment)
    garment_id = db.Column(db.Integer, db.ForeignKey('garment.id'), nullable=False, index=True)
