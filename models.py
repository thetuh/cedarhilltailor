from application import db
from flask_login import UserMixin

# Junction table used to store the association of a particular <garment, job> pair and its base cost
garment_job_pair = db.Table('garment_job_pair',
    db.Column('id', db.Integer, primary_key=True),

    # These two form a composite key
    db.Column('garment_id', db.Integer, db.ForeignKey('garment.id'), index=True),
    db.Column('job_id', db.Integer, db.ForeignKey('job.id'), index=True),

    db.Column('price', db.DECIMAL(10, 2), nullable=False),

    # Define a unique constraint on garment_id and job_id
    db.UniqueConstraint('garment_id', 'job_id', name='uq_garment_job_pair')
)

# Junction table used to store the association of job pair and order id
class ItemJob(db.Model):
    item_id = db.Column(db.Integer, db.ForeignKey('order_item.id'), primary_key=True)
    pair_id = db.Column(db.Integer, db.ForeignKey('garment_job_pair.id'), primary_key=True)

# Junction table used to store the association of a order and its items (image, description, price)
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)
    order_date = db.Column(db.Date, index=True, nullable=False)
    completion_date = db.Column(db.Date, index=True, nullable=False)

    # One-to-many (OrderItem)
    order_items = db.relationship('OrderItem', backref='order', lazy='joined')

class Garment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    # Many-to-many (Job)
    jobs = db.relationship('Job', secondary=garment_job_pair, backref='garments', lazy='joined')

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