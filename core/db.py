"""Conexión a MySQL y utilidades de acceso a datos (SQLAlchemy + PyMySQL)."""
import logging
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine

from core.config import get_section

log = logging.getLogger("enercontrol.db")
_KEYS = ["host", "port", "user", "password", "database", "ssl_ca"]
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "database" / "schema.sql"


@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    cfg = get_section("mysql", _KEYS)
    missing = [k for k in ("host", "user", "password", "database") if k not in cfg]
    if missing:
        raise RuntimeError(
            "Falta configuración de MySQL: " + ", ".join(missing)
            + ". Define [mysql] en .streamlit/secrets.toml o variables MYSQL_*."
        )
    url = URL.create(
        "mysql+pymysql",
        username=cfg["user"],
        password=str(cfg["password"]),
        host=cfg["host"],
        port=int(cfg.get("port", 3306)),
        database=cfg["database"],
        query={"charset": "utf8mb4"},
    )
    connect_args = {}
    if cfg.get("ssl_ca"):
        connect_args["ssl"] = {"ca": cfg["ssl_ca"]}
    return create_engine(url, pool_pre_ping=True, pool_recycle=280, connect_args=connect_args)


def check_connection():
    """Devuelve (ok, mensaje)."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Conexión exitosa"
    except Exception as exc:  # noqa: BLE001
        log.error("Fallo de conexión: %s", exc)
        return False, str(exc)


def init_schema() -> None:
    """Crea las tablas si no existen, leyendo database/schema.sql."""
    lines = [l for l in SCHEMA_PATH.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")]
    statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
    with get_engine().begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def fetch_one(sql: str, params: dict | None = None):
    with get_engine().connect() as conn:
        row = conn.execute(text(sql), params or {}).mappings().first()
        return dict(row) if row else None


def execute(sql: str, params: dict | None = None) -> int:
    """Ejecuta INSERT/UPDATE/DELETE y devuelve filas afectadas."""
    with get_engine().begin() as conn:
        return conn.execute(text(sql), params or {}).rowcount


def insert(sql: str, params: dict | None = None) -> int:
    """Ejecuta un INSERT y devuelve el id generado."""
    with get_engine().begin() as conn:
        return int(conn.execute(text(sql), params or {}).lastrowid)


def count_users() -> int:
    row = fetch_one("SELECT COUNT(*) AS n FROM usuarios")
    return int(row["n"])
