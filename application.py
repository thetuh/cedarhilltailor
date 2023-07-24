from flask import Flask, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql

pymysql.install_as_MySQLdb()

application = Flask(__name__)
application.config['SQLALCHEMY_DATABASE_URI']='mysql://root:password@awseb-e-f39h2b6uxw-stack-awsebrdsdatabase-oufcg7eqqkbx.cww0u0pb9txq.us-east-2.rds.amazonaws.com/user'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
application.secret_key = "cedarhilltailor"

db = SQLAlchemy(application)

class User(db.Model):
    username = db.Column(db.String(150), primary_key=True)
    password = db.Column(db.String(150), nullable=False)

@application.route('/')
def home():
    return render_template('index.html')

@application.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Sanity checks
        if len(username) < 1:
            flash('Please enter a username', category='error')
            return render_template('index.html')
        elif len(password) < 1:
            flash('Please enter a password', category='error')
            return render_template('index.html')

        # Authentication
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            return ('Success')
        else:
            return ('Invalid login')


    return render_template('index.html')