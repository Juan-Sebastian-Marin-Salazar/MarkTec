from flask import Flask
from dotenv import load_dotenv  # ← Import necesario
import os                     # ← Necesario para usar variables de entorno

from .config import Config
from .routes import register_routes

# Cargar variables del archivo .env
load_dotenv()  # ← Esto permite usar EMAIL_USER, EMAIL_PASS, SECRET_KEY, etc.

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Cargar configuración desde config.py
    app.config.from_object(Config)
    # Asignar SECRET_KEY desde .env
    app.secret_key = os.getenv("SECRET_KEY", "default_key_segura")
    # Registrar todas las rutas
    register_routes(app)

    return app