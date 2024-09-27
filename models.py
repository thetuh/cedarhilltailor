from enum import Enum
from application import db
from flask_login import UserMixin
from sqlalchemy.schema import UniqueConstraint

class JobStatus(Enum):
    INCOMPLETE = 0
    COMPLETE = 1

class OrderStatus(Enum):
    INCOMPLETE = 0
    COMPLETE = 1

class GarmentJobPair(db.Model):
    __tablename__ = 'garment_job_pair'

    id = db.Column(db.Integer, primary_key=True)
    garment_id = db.Column(db.Integer, db.ForeignKey('garment.id'), index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), index=True)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)

    # Unique constraint on garment_id and job_id
    db.UniqueConstraint('garment_id', 'job_id', name='uq_garment_job_pair')

    # Relationships
    garment = db.relationship('Garment', backref='garment_job_pairs')
    job = db.relationship('Job', backref='garment_job_pairs')

    # Ensure the backref name is unique to avoid conflicts
    item_jobs = db.relationship('ItemJob', backref='garment_job_pair_ref', lazy='joined', cascade='all, delete-orphan')

class ItemJob(db.Model):
    __tablename__ = 'item_job'

    item_id = db.Column(db.Integer, db.ForeignKey('order_item.id'), primary_key=True)
    pair_id = db.Column(db.Integer, db.ForeignKey('garment_job_pair.id'), primary_key=True)

    status = db.Column(db.SmallInteger, nullable=False, default=JobStatus.INCOMPLETE)

    # Ensure that this backref name is unique
    pair = db.relationship('GarmentJobPair', backref='item_jobs_ref', lazy='joined')

# Junction table used to store the association of a order and its items (image, description, price)
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    # One-to-many (ItemJob)
    item_jobs = db.relationship('ItemJob', backref='order_item', lazy='joined', cascade='all, delete-orphan')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)
    order_date = db.Column(db.Date, index=True, nullable=False)
    completion_date = db.Column(db.Date, index=True, nullable=False)

    status = db.Column(db.SmallInteger, nullable=False, default=OrderStatus.INCOMPLETE)

    # One-to-many (OrderItem)
    order_items = db.relationship('OrderItem', backref='order', lazy='joined', cascade='all, delete-orphan')

class Garment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    # Many-to-many (Job)
    jobs = db.relationship('Job', secondary='garment_job_pair', backref='garments', lazy='dynamic', viewonly=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    # One-to-many (User)
    users = db.relationship('User', backref='role', lazy='joined')

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False, index=True)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(10), unique=True, index=True)

    # One-to-many (Order)
    orders = db.relationship('Order', backref='customer', lazy='joined')