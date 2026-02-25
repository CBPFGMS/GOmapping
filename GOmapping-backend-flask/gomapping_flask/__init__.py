from flask import Flask, jsonify
from flask_cors import CORS

from .config import Config
from .extensions import db
from .routes.api import api_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config())

    db.init_app(app)
    CORS(app, resources={r"/*": {"origins": app.config["CORS_ALLOWED_ORIGINS"]}})

    @app.get("/")
    def healthcheck():
        return jsonify({"status": "ok", "service": "gomapping-backend-flask"})

    app.register_blueprint(api_bp, url_prefix="")
    app.register_blueprint(api_bp, url_prefix="/api", name="api_prefixed")
    return app
