from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

application = Flask(__name__)

application.config['SQLALCHEMY_DATABASE_URI']='mysql://root:password@awseb-e-f39h2b6uxw-stack-awsebrdsdatabase-oufcg7eqqkbx.cww0u0pb9txq.us-east-2.rds.amazonaws.com/user'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
application.secret_key = "cedarhilltailor"

db = SQLAlchemy(application)

class User(db.Model):
    username = db.Column(db.String(120), primary_key=True)
    password = db.Column(db.String(120), nullable=False)

@application.route('/')
def home():
    return render_template('index.html')