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

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(150), index=True)
    customer_phone_number = db.Column(db.String(20), index=True)

    order_date = db.Column(db.Date, index=True)
    completion_date = db.Column(db.Date, index=True)

    # one-to-many (Garment)
    garments = db.relationship('Garment', backref='order', lazy=True)

class GarmName(db.Model):
    __tablename__ = 'garmname'  # Add this line to explicitly set the table name
    id = db.Column(db.Integer, primary_key=True)
    garment_name = db.Column(db.String(100))

    # one-to-many (Garment)
    g_garments = db.relationship('Garment', backref='garmname', lazy=True)

class JobName(db.Model):
    __tablename__ = 'jobname'  # Add this line to explicitly set the table name
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(100))

    # one-to-many (Job)
    j_jobs = db.relationship('Job', backref='jobname', lazy=True) 

class Garment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # FK (GarmName)
    garm_name_id = db.Column(db.Integer, db.ForeignKey('garmname.id'), nullable=False)

    # FK (Order)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False, index=True)

    # one-to-many (Job)
    jobs = db.relationship('Job', backref='garment', lazy=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.DECIMAL(10, 2), nullable=False, index=True)

    # FK (GarmentItem)
    job_name_id = db.Column(db.Integer, db.ForeignKey('jobname.id'), nullable=False)

    # FK (Garment)
    garment_id = db.Column(db.Integer, db.ForeignKey('garment.id'), nullable=False, index=True)