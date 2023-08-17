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

# Junction table used to store the association of a pair and order id
# Note that the price can be different from the garment_job_pair table since it can be manually overrided
class OrderItem(db.Model):
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), primary_key=True)
    pair_id = db.Column(db.Integer, db.ForeignKey('garment_job_pair.id'), primary_key=True)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)

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
