from flask import Flask
from .api.routes import api_bp
from .api.webhook import webhook_bp
from .api.system import system_bp
from .core.database import init_db, register_db
from .core.scheduler import start_scheduler


def create_app():
    app = Flask(__name__)

    init_db()
    register_db(app)
    start_scheduler()

    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(webhook_bp, url_prefix='/api/v1/webhook')
    app.register_blueprint(system_bp, url_prefix='/api/v1/system')
    return app
