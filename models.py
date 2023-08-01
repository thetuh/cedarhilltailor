from application import db
from flask_login import UserMixin

# Junction table for the many-to-many relationship between Garments and Jobs
garment_job_association = db.Table('garment_job_association',
    db.Column('garment_id', db.Integer, db.ForeignKey('garment.id'), primary_key=True),
    db.Column('job_id', db.Integer, db.ForeignKey('job.id'), primary_key=True)
)

class Garment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    # Many-to-many (Job)
    jobs = db.relationship('Job', secondary=garment_job_association, backref='garments', lazy='joined')

    def get_jobs(self):
        return self.jobs

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    # Other job-specific attributes can be added here

class GarmentJobPrice(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Many-to-one (Garment)
    garment_id = db.Column(db.Integer, db.ForeignKey('garment.id'), nullable=False)
    garment = db.relationship('Garment', backref='prices')

    # Many-to-one (Job)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    job = db.relationship('Job', backref='prices')

    # Price field for the specific garment and job combination
    price = db.Column(db.Float, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Additional order-related attributes can be added here

    # Many-to-one (Garment)
    garment_id = db.Column(db.Integer, db.ForeignKey('garment.id'), nullable=False, index=True)
    garment = db.relationship('Garment', backref='orders')

    # Many-to-one (Job)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False, index=True)
    job = db.relationship('Job', backref='orders')

    # Price field that is auto-populated by the garment and job both selected
    price = db.Column(db.Float, nullable=False)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    # One-to-many (User)
    users = db.relationship('User', backref='role', lazy=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    # Foreign Key (Role)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False, index=True)
