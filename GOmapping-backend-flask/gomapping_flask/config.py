import os
from pathlib import Path
from urllib.parse import quote_plus


class Config:
    def __init__(self) -> None:
        debug_raw = os.getenv("FLASK_DEBUG", "true").lower()
        self.DEBUG = debug_raw in {"1", "true", "yes", "on"}

        database_url = os.getenv("DATABASE_URL")
        if database_url:
            self.SQLALCHEMY_DATABASE_URI = database_url
        else:
            db_engine = os.getenv("DB_ENGINE", "sqlite").lower()
            if db_engine == "sqlite":
                sqlite_path_raw = os.getenv("SQLITE_PATH", "gomapping.db")
                if sqlite_path_raw == ":memory:":
                    self.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
                else:
                    sqlite_path = Path(sqlite_path_raw)
                    if not sqlite_path.is_absolute():
                        sqlite_path = (Path.cwd() / sqlite_path).resolve()
                    self.SQLALCHEMY_DATABASE_URI = f"sqlite:///{sqlite_path.as_posix()}"
            elif db_engine == "mssql":
                db_name = os.getenv("DB_NAME", "gomapping")
                db_user = os.getenv("DB_USER", "demo")
                db_password = os.getenv("DB_PASSWORD", "Ocha19911219!")
                db_host = os.getenv("DB_HOST", r"OCHAL25109748\SQLEXPRESS")
                odbc_driver = os.getenv("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")
                trust_cert = os.getenv("DB_TRUST_CERT", "yes")
                driver_q = quote_plus(odbc_driver)
                password_q = quote_plus(db_password)
                self.SQLALCHEMY_DATABASE_URI = (
                    f"mssql+pyodbc://{db_user}:{password_q}@{db_host}/{db_name}"
                    f"?driver={driver_q}&TrustServerCertificate={trust_cert}"
                )
            else:
                raise ValueError("Unsupported DB_ENGINE. Use 'sqlite' or 'mssql'.")

        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        auto_create_raw = os.getenv("AUTO_CREATE_TABLES", "true").lower()
        self.AUTO_CREATE_TABLES = auto_create_raw in {"1", "true", "yes", "on"}

        cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
        self.CORS_ALLOWED_ORIGINS = (
            [item.strip() for item in cors_origins.split(",") if item.strip()]
            if cors_origins != "*"
            else "*"
        )

        self.ZHIPUAI_API_KEY = os.getenv(
            "ZHIPUAI_API_KEY",
            "c4d74482a5e64890a44fd5cd2e6af2c3.LouAL40edi1tZss8",
        )
        self.CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
