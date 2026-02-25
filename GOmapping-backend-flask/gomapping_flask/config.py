import os
from urllib.parse import quote_plus


class Config:
    def __init__(self) -> None:
        debug_raw = os.getenv("FLASK_DEBUG", "true").lower()
        self.DEBUG = debug_raw in {"1", "true", "yes", "on"}

        db_name = os.getenv("DB_NAME", "gomapping")
        db_user = os.getenv("DB_USER", "demo")
        db_password = os.getenv("DB_PASSWORD", "Ocha19911219!")
        db_host = os.getenv("DB_HOST", r"OCHAL25109748\SQLEXPRESS")
        odbc_driver = os.getenv("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")
        trust_cert = os.getenv("DB_TRUST_CERT", "yes")

        # Example:
        # mssql+pyodbc://user:pass@host/db?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes
        driver_q = quote_plus(odbc_driver)
        password_q = quote_plus(db_password)
        self.SQLALCHEMY_DATABASE_URI = (
            f"mssql+pyodbc://{db_user}:{password_q}@{db_host}/{db_name}"
            f"?driver={driver_q}&TrustServerCertificate={trust_cert}"
        )
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False

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
