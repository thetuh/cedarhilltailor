from flask import Flask
application = Flask(__name__)

@application.route('/')
def login():
    return 'Hello, World!'