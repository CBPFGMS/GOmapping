from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import text

from .config import Config
from .extensions import db
from .routes.api import api_bp


def _ensure_sqlite_org_mapping_schema():
    """
    Ensure org_mapping.id is INTEGER PRIMARY KEY AUTOINCREMENT in SQLite.
    Older schema used BIGINT, which breaks auto-increment inserts on SQLite.
    """
    with db.engine.begin() as conn:
        table_rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='org_mapping'")
        ).fetchall()
        if not table_rows:
            return

        pragma_rows = conn.execute(text("PRAGMA table_info(org_mapping)")).fetchall()
        id_row = next((row for row in pragma_rows if row[1] == "id"), None)
        if not id_row:
            return

        id_type = str(id_row[2]).upper()
        if id_type == "INTEGER":
            return

        conn.execute(text("DROP TABLE IF EXISTS org_mapping_new"))
        conn.execute(
            text(
                """
                CREATE TABLE org_mapping_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    global_org_id INTEGER NOT NULL,
                    instance_org_id INTEGER,
                    instance_org_name VARCHAR(255) NOT NULL,
                    instance_org_acronym VARCHAR(50),
                    instance_org_type VARCHAR(255) NOT NULL,
                    parent_instance_org_id INTEGER,
                    fund_name VARCHAR(255),
                    fund_id INTEGER,
                    match_percent DECIMAL(5, 2),
                    risk_level VARCHAR(10),
                    status VARCHAR(20),
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO org_mapping_new (
                    id, global_org_id, instance_org_id, instance_org_name, instance_org_acronym,
                    instance_org_type, parent_instance_org_id, fund_name, fund_id, match_percent,
                    risk_level, status, created_at, updated_at
                )
                SELECT
                    id, global_org_id, instance_org_id, instance_org_name, instance_org_acronym,
                    instance_org_type, parent_instance_org_id, fund_name, fund_id, match_percent,
                    risk_level, status, created_at, updated_at
                FROM org_mapping
                """
            )
        )
        conn.execute(text("DROP TABLE org_mapping"))
        conn.execute(text("ALTER TABLE org_mapping_new RENAME TO org_mapping"))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config())

    db.init_app(app)
    with app.app_context():
        if app.config.get("AUTO_CREATE_TABLES", True) and str(app.config.get("SQLALCHEMY_DATABASE_URI", "")).startswith("sqlite"):
            db.create_all()
            _ensure_sqlite_org_mapping_schema()

    CORS(app, resources={r"/*": {"origins": app.config["CORS_ALLOWED_ORIGINS"]}})

    @app.get("/")
    def healthcheck():
        return jsonify({"status": "ok", "service": "gomapping-backend-flask"})

    app.register_blueprint(api_bp, url_prefix="")
    app.register_blueprint(api_bp, url_prefix="/api", name="api_prefixed")
    return app
