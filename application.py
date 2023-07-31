import pymysql
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

pymysql.install_as_MySQLdb()

application = Flask(__name__)
application.config['SQLALCHEMY_DATABASE_URI']='mysql://root:4ytc1odZquCDr19V9Ltm@awseb-e-f39h2b6uxw-stack-awsebrdsdatabase-oufcg7eqqkbx.cww0u0pb9txq.us-east-2.rds.amazonaws.com/user'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
application.secret_key = "cedarhilltailor"

db = SQLAlchemy(application)

from views import views
from auth import auth

application.register_blueprint(views, url_prefix='/')
application.register_blueprint(auth, url_prefix='/')

from models import User

with application.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(application)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))
