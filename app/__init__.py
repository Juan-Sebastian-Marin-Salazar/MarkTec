from flask import Flask
from .config import Config
from .routes import register_routes

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    register_routes(app)

    return app