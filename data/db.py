"""
Database helpers — SQL Server via pyodbc.
"""

import os
import urllib.parse

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# ── SQL Server config ─────────────────────────────────────────────────────────
# All values can be overridden via environment variables (set in docker-compose).
DB_CONFIG = {
    "server":   os.environ.get("DB_SERVER", r"DESKTOP-59TH5MU\K6_SQLEXPRESS"),
    "database": os.environ.get("DB_NAME", "SabreDB"),
    "driver":   os.environ.get("DB_DRIVER", "ODBC Driver 17 for SQL Server"),
    "username": os.environ.get("DB_USER", ""),    # blank = Windows Auth
    "password": os.environ.get("DB_PASSWORD", ""),
}
# ─────────────────────────────────────────────────────────────────────────────

_DATE_COLS = [
    "PNRCreateDate", "VCRCreateDate",
    "ServiceStartDate", "ServiceEndDate",
    "FlownServiceStartDate", "FlownFlightOrigDate",
]


# ── Engine ────────────────────────────────────────────────────────────────────

def _conn_str() -> str:
    cfg = DB_CONFIG
    if cfg["username"]:
        odbc = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE={cfg['database']};"
            f"UID={cfg['username']};"
            f"PWD={cfg['password']};"
            "Encrypt=yes;TrustServerCertificate=yes;"
        )
    else:
        odbc = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE={cfg['database']};"
            "Trusted_Connection=yes;"
            "Encrypt=yes;TrustServerCertificate=yes;"
        )
    return f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc)}"


def get_engine():
    return create_engine(_conn_str(), fast_executemany=True)


# ── Public API ────────────────────────────────────────────────────────────────

def test_connection() -> tuple[bool, str]:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, f"Connected to [{DB_CONFIG['database']}] on {DB_CONFIG['server']}"
    except SQLAlchemyError as e:
        return False, str(e)


def save_to_db(
    df: pd.DataFrame,
    table: str = "SabreReport",
    if_exists: str = "append",
    batch_label: str = "",
) -> tuple[bool, str]:
    try:
        out = df.copy()
        for col in _DATE_COLS:
            if col in out.columns:
                out[col] = pd.to_datetime(out[col], errors="coerce")

        out.insert(0, "ImportedAt", pd.Timestamp.now())
        if batch_label:
            out.insert(1, "BatchLabel", batch_label)

        engine = get_engine()
        out.to_sql(table, engine, index=False, if_exists=if_exists,
                   chunksize=500, schema="dbo")
        return True, f"{len(out):,} rows saved to [{table}]"
    except SQLAlchemyError as e:
        return False, str(e)


def get_available_years(
    table: str = "SabreReport",
    date_col: str = "PNRCreateDate",
) -> list[int]:
    try:
        engine = get_engine()
        sql = text(
            f"SELECT DISTINCT YEAR([{date_col}]) AS yr "
            f"FROM {table} "
            f"WHERE [{date_col}] IS NOT NULL "
            f"ORDER BY yr DESC"
        )
        with engine.connect() as conn:
            rows = [row[0] for row in conn.execute(sql) if row[0] is not None]
        return [int(r) for r in rows]
    except SQLAlchemyError:
        return []


def query_data(
    table: str = "SabreReport",
    date_col: str = "PNRCreateDate",
    year: int | None = None,
    months: list[int] | None = None,
    date_from=None,
    date_to=None,
) -> tuple[pd.DataFrame, str]:
    try:
        engine = get_engine()
        conditions: list[str] = []
        params: dict = {}

        if year:
            conditions.append(f"YEAR([{date_col}]) = :yr")
            params["yr"] = int(year)

        if months:
            placeholders = ", ".join(f":m{i}" for i in range(len(months)))
            conditions.append(f"MONTH([{date_col}]) IN ({placeholders})")
            for i, m in enumerate(months):
                params[f"m{i}"] = int(m)

        if date_from:
            conditions.append(f"CAST([{date_col}] AS DATE) >= :df")
            params["df"] = str(date_from)

        if date_to:
            conditions.append(f"CAST([{date_col}] AS DATE) <= :dt")
            params["dt"] = str(date_to)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        df = pd.read_sql(text(f"SELECT * FROM {table} {where}"), engine, params=params)
        return df, ""
    except SQLAlchemyError as e:
        return pd.DataFrame(), str(e)


# ── Schema bootstrap ──────────────────────────────────────────────────────────

def ensure_schema() -> None:
    """Create users/system_logs tables if absent; seed one admin if table is empty."""
    from data.migrations import get_ddl
    from core.crypto import hash_pw

    engine = get_engine()
    with engine.begin() as conn:
        for stmt in get_ddl():
            conn.execute(text(stmt))

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0

    if count == 0:
        pw_hash = hash_pw("sabre2025")
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (username, password_hash, role) VALUES (:u, :p, :r)"),
                {"u": "admin", "p": pw_hash, "r": "admin"},
            )


# ── User CRUD ─────────────────────────────────────────────────────────────────

def get_user(username: str) -> dict | None:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id, username, password_hash, role, is_active "
                     "FROM users WHERE username = :u"),
                {"u": username},
            ).fetchone()
        if row:
            return {
                "id": row[0], "username": row[1], "password_hash": row[2],
                "role": row[3], "is_active": bool(row[4]),
            }
        return None
    except SQLAlchemyError:
        return None


def update_last_login(username: str) -> None:
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE users SET last_login = GETUTCDATE() WHERE username = :u"),
                {"u": username},
            )
    except SQLAlchemyError:
        pass


def list_users() -> list[dict]:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, username, role, is_active, created_at, last_login "
                     "FROM users ORDER BY id")
            ).fetchall()
        return [
            {
                "id": r[0], "username": r[1], "role": r[2],
                "is_active": bool(r[3]), "created_at": r[4], "last_login": r[5],
            }
            for r in rows
        ]
    except SQLAlchemyError:
        return []


def create_user(username: str, password: str, role: str) -> tuple[bool, str]:
    from core.crypto import hash_pw
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (username, password_hash, role) VALUES (:u, :p, :r)"),
                {"u": username.strip(), "p": hash_pw(password), "r": role},
            )
        return True, f"User '{username.strip()}' created successfully."
    except SQLAlchemyError as e:
        return False, str(e)


def toggle_user_active(user_id: int, active: bool) -> tuple[bool, str]:
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE users SET is_active = :v WHERE id = :id"),
                {"v": 1 if active else 0, "id": user_id},
            )
        return True, "User " + ("enabled." if active else "disabled.")
    except SQLAlchemyError as e:
        return False, str(e)


def delete_user(user_id: int) -> tuple[bool, str]:
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        return True, "User deleted."
    except SQLAlchemyError as e:
        return False, str(e)


def change_password(username: str, new_password: str) -> tuple[bool, str]:
    from core.crypto import hash_pw
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE users SET password_hash = :p WHERE username = :u"),
                {"p": hash_pw(new_password), "u": username},
            )
        return True, f"Password for '{username}' updated."
    except SQLAlchemyError as e:
        return False, str(e)


def change_role(user_id: int, new_role: str) -> tuple[bool, str]:
    if new_role not in ("user", "admin", "dev"):
        return False, f"Invalid role '{new_role}'."
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE users SET role = :r WHERE id = :id"),
                {"r": new_role, "id": user_id},
            )
        return True, f"Role updated to '{new_role}'."
    except SQLAlchemyError as e:
        return False, str(e)


# ── System logs ───────────────────────────────────────────────────────────────

def log_event(event_type: str, username: str = "", detail: str = "") -> None:
    """Append a row to system_logs. Silent on failure so it never blocks the UI."""
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO system_logs (event_type, username, detail) "
                     "VALUES (:e, :u, :d)"),
                {"e": event_type[:50], "u": username[:64], "d": detail[:500]},
            )
    except SQLAlchemyError:
        pass


def get_logs(limit: int = 200) -> list[dict]:
    try:
        engine = get_engine()
        sql = text(
            "SELECT TOP(:n) ts, event_type, username, detail "
            "FROM system_logs ORDER BY id DESC"
        )
        with engine.connect() as conn:
            rows = conn.execute(sql, {"n": limit}).fetchall()
        return [{"ts": r[0], "event": r[1], "user": r[2], "detail": r[3]} for r in rows]
    except SQLAlchemyError:
        return []
