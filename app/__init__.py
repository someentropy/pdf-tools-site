from flask import Flask
from app.routes import app_routes

def create_app():
    app = Flask(__name__)
    app.secret_key = "supersecretkey"
    app.register_blueprint(app_routes)
    return app
