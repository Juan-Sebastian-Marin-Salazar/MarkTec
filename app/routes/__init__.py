from .test import bp as test_bp
from .auth import bp as auth_bp
def register_routes(app):
    app.register_blueprint(test_bp)
    app.register_blueprint(auth_bp)