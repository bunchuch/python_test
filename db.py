"""
SQL Server connection and save helpers.

Edit DB_CONFIG below to match your environment, then restart the app.
Supports both Windows Authentication (leave username/password blank)
and SQL Server Authentication (fill in username + password).
"""

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# ── Edit these values ─────────────────────────────────────────────────────────
DB_CONFIG = {
    "server":   "localhost",                    # e.g. "192.168.1.10" or "SERVER\\INSTANCE"
    "database": "SabreDB",                      # target database name
    "driver":   "ODBC Driver 17 for SQL Server",# or "ODBC Driver 18 for SQL Server"
    "username": "",                             # blank = Windows Authentication
    "password": "",
}
# ─────────────────────────────────────────────────────────────────────────────


def _conn_str() -> str:
    cfg = DB_CONFIG
    driver = cfg["driver"].replace(" ", "+")
    if cfg["username"]:
        return (
            f"mssql+pyodbc://{cfg['username']}:{cfg['password']}"
            f"@{cfg['server']}/{cfg['database']}?driver={driver}"
        )
    return (
        f"mssql+pyodbc://@{cfg['server']}/{cfg['database']}"
        f"?driver={driver}&trusted_connection=yes"
    )


def get_engine():
    return create_engine(_conn_str(), fast_executemany=True)


def test_connection() -> tuple[bool, str]:
    """Return (success, message)."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, f"Connected to [{DB_CONFIG['database']}] on {DB_CONFIG['server']}"
    except SQLAlchemyError as e:
        return False, str(e)


def save_to_db(
    df: pd.DataFrame,
    table: str = "SabreReport",
    if_exists: str = "append",   # "append" | "replace" | "fail"
    batch_label: str = "",
) -> tuple[bool, str]:
    """
    Write df to SQL Server.
    Adds a BatchLabel column so you can tell each import apart.
    Returns (success, message).
    """
    try:
        out = df.copy()
        if batch_label:
            out.insert(0, "BatchLabel", batch_label)

        engine = get_engine()
        out.to_sql(
            table,
            engine,
            index=False,
            if_exists=if_exists,
            chunksize=500,
            schema="dbo",
        )
        return True, f"{len(out):,} rows saved to [dbo].[{table}]"
    except SQLAlchemyError as e:
        return False, str(e)
