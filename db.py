"""
Database helpers — supports SQLite (testing) and SQL Server (production).

Set DB_MODE = "sqlite"    → uses a local file, no driver needed.
Set DB_MODE = "sqlserver" → uses DB_CONFIG below, requires pyodbc.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# ── Mode switch ───────────────────────────────────────────────────────────────
DB_MODE = "sqlite"          # "sqlite" | "sqlserver"
SQLITE_PATH = "sabre_test.db"   # relative to the working directory

# ── SQL Server config (only used when DB_MODE = "sqlserver") ──────────────────
DB_CONFIG = {
    "server":   "localhost",
    "database": "SabreDB",
    "driver":   "ODBC Driver 17 for SQL Server",
    "username": "",          # blank = Windows Auth
    "password": "",
}
# ─────────────────────────────────────────────────────────────────────────────

_DATE_COLS = [
    "PNRCreateDate", "VCRCreateDate",
    "ServiceStartDate", "ServiceEndDate",
    "FlownServiceStartDate", "FlownFlightOrigDate",
]


# ── Dialect helpers ───────────────────────────────────────────────────────────

def _q(col: str) -> str:
    """Quote a column name for the active dialect."""
    return f'"{col}"' if DB_MODE == "sqlite" else f"[{col}]"


def _year_expr(col: str) -> str:
    return f"strftime('%Y', {_q(col)})" if DB_MODE == "sqlite" else f"YEAR({_q(col)})"


def _month_expr(col: str) -> str:
    if DB_MODE == "sqlite":
        return f"CAST(strftime('%m', {_q(col)}) AS INTEGER)"
    return f"MONTH({_q(col)})"


def _date_cast(col: str) -> str:
    return f"date({_q(col)})" if DB_MODE == "sqlite" else f"CAST({_q(col)} AS DATE)"


# ── Engine ────────────────────────────────────────────────────────────────────

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
    if DB_MODE == "sqlite":
        return create_engine(f"sqlite:///{SQLITE_PATH}")
    return create_engine(_conn_str(), fast_executemany=True)


# ── Public API ────────────────────────────────────────────────────────────────

def test_connection() -> tuple[bool, str]:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        if DB_MODE == "sqlite":
            return True, f"SQLite OK — {SQLITE_PATH}"
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
        kwargs: dict = dict(index=False, if_exists=if_exists, chunksize=500)
        if DB_MODE == "sqlserver":
            kwargs["schema"] = "dbo"

        out.to_sql(table, engine, **kwargs)
        return True, f"{len(out):,} rows saved to [{table}]"
    except SQLAlchemyError as e:
        return False, str(e)


def get_available_years(
    table: str = "SabreReport",
    date_col: str = "PNRCreateDate",
) -> list[int]:
    try:
        engine = get_engine()
        yr = _year_expr(date_col)
        col = _q(date_col)
        sql = text(
            f"SELECT DISTINCT {yr} AS yr "
            f"FROM {table} "
            f"WHERE {col} IS NOT NULL "
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
            conditions.append(f"{_year_expr(date_col)} = :yr")
            params["yr"] = str(year) if DB_MODE == "sqlite" else int(year)

        if months:
            placeholders = ", ".join(f":m{i}" for i in range(len(months)))
            conditions.append(f"{_month_expr(date_col)} IN ({placeholders})")
            for i, m in enumerate(months):
                params[f"m{i}"] = int(m)

        if date_from:
            conditions.append(f"{_date_cast(date_col)} >= :df")
            params["df"] = str(date_from)

        if date_to:
            conditions.append(f"{_date_cast(date_col)} <= :dt")
            params["dt"] = str(date_to)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        df = pd.read_sql(text(f"SELECT * FROM {table} {where}"), engine, params=params)
        return df, ""
    except SQLAlchemyError as e:
        return pd.DataFrame(), str(e)
