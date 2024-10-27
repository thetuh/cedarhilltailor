import os
import pymysql
import sqlalchemy
from google.cloud import storage
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
from flask_migrate import Migrate

# Use pymysql as MySQL driver
pymysql.install_as_MySQLdb()

application = Flask(__name__)

# Set the environment variables
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_name = os.getenv("DB_NAME")
db_host = os.getenv("INSTANCE_HOST")
db_port = os.getenv("DB_PORT")

# Create the SQLAlchemy engine
application.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{quote(db_pass)}@{db_host}:{db_port}/{db_name}"

# Disable SQLALCHEMY_TRACK_MODIFICATIONS to avoid overhead
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Secret key for session management
application.secret_key = os.getenv("SECRET_KEY")

# Initialize SQLAlchemy
db = SQLAlchemy(application)

# Initialize Flask-Migrate
migrate = Migrate(application, db)

# Import and register blueprints
from views import views
from auth import auth

application.register_blueprint(views, url_prefix='/')
application.register_blueprint(auth, url_prefix='/')

# Create all models
with application.app_context():
    db.create_all()

# Ensure globals are initialized (sales tax rate, store name, etc.)
from models import Globals
with application.app_context():
    if not Globals.query.first():
        db.session.add(Globals(sales_tax_rate=0.0826, store_name='Cedar Hill Tailor'))
        db.session.commit()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(application)

storage_client = storage.Client()
bucket_name = "cedarhilltailor"
bucket = storage_client.bucket(bucket_name)

from models import User
@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Run the application
if __name__ == "__main__":
    application.run(host="0.0.0.0", port=8080)
