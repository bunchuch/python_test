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
    """Create users/system_logs + normalized star-schema tables if absent."""
    from data.migrations import get_ddl, get_normalized_ddl
    from core.crypto import hash_pw

    engine = get_engine()
    with engine.begin() as conn:
        for stmt in get_ddl() + get_normalized_ddl():
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


def next_user_code() -> str:
    """Return the next available K6-NNN user code based on current max id."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            max_id = conn.execute(text("SELECT ISNULL(MAX(id), 0) FROM users")).scalar() or 0
        return f"K6-{int(max_id) + 1:03d}"
    except SQLAlchemyError:
        return "K6-001"


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


# ── Normalized star-schema save ───────────────────────────────────────────────

def save_normalized_batch(
    data: dict,
    batch_label: str = "",
) -> tuple[bool, str]:
    """
    Save a normalized batch (from process_normalized()) to the star schema tables.

    Insertion order:
      dim_country / dim_airport / dim_airline  (dimensions, upserted)
      fact_pnr                                 (skip existing PKs)
      fact_ticket                              (skip existing PKs)
      fact_coupon / dim_passenger / fact_od    (delete-then-insert for this batch)
      fact_ticket_history / fact_payment / fact_tax  (same)
    """
    try:
        engine = get_engine()
        _seed_dim_tables(engine)
        _upsert_dim_from_data(engine, data)

        # fact_pnr
        pnr_rows = [r for r in data.get("pnr", []) if r.get("pnr")]
        if pnr_rows:
            df_pnr = pd.DataFrame(pnr_rows)
            existing = _get_existing_pks(engine, "fact_pnr", "pnr")
            new_pnr = df_pnr[~df_pnr["pnr"].isin(existing)]
            if not new_pnr.empty:
                new_pnr.to_sql("fact_pnr", engine, index=False,
                                if_exists="append", schema="dbo", chunksize=500)

        # fact_ticket
        ticket_rows = [r for r in data.get("ticket", []) if r.get("ticket_no")]
        for r in ticket_rows:
            r["batch_label"] = batch_label or None
        ticket_nos: list[str] = []
        if ticket_rows:
            df_tkt = pd.DataFrame(ticket_rows)
            existing = _get_existing_pks(engine, "fact_ticket", "ticket_no")
            new_tkt = df_tkt[~df_tkt["ticket_no"].isin(existing)]
            ticket_nos = df_tkt["ticket_no"].tolist()
            if not new_tkt.empty:
                new_tkt.to_sql("fact_ticket", engine, index=False,
                                if_exists="append", schema="dbo", chunksize=500)

        pnr_vals: list[str] = [r["pnr"] for r in pnr_rows]

        # Child ticket tables: delete-then-insert
        for table, fk_col, key in [
            ("fact_coupon",         "ticket_no", "coupon"),
            ("fact_ticket_history", "ticket_no", "history"),
            ("fact_payment",        "ticket_no", "payment"),
            ("fact_tax",            "ticket_no", "tax"),
        ]:
            rows = [r for r in data.get(key, []) if r.get("ticket_no")]
            if rows:
                _delete_by_fk(engine, table, fk_col, ticket_nos)
                pd.DataFrame(rows).to_sql(
                    table, engine, index=False,
                    if_exists="append", schema="dbo", chunksize=500,
                )

        # Child PNR tables: delete-then-insert
        for table, fk_col, key in [
            ("dim_passenger", "pnr", "passenger"),
            ("fact_od",       "pnr", "od"),
        ]:
            rows = [r for r in data.get(key, []) if r.get("pnr")]
            if rows:
                _delete_by_fk(engine, table, fk_col, pnr_vals)
                pd.DataFrame(rows).to_sql(
                    table, engine, index=False,
                    if_exists="append", schema="dbo", chunksize=500,
                )

        return True, (
            f"{len(ticket_rows):,} tickets, {len(pnr_rows):,} PNRs "
            f"saved to normalized schema"
        )
    except SQLAlchemyError as e:
        return False, str(e)


# ── Normalized flat-export query ──────────────────────────────────────────────

# Column name → SQL expression in the flat export query
_NORM_DATE_MAP = {
    "PNRCreateDate":  "pnr.create_date",
    "VCRCreateDate":  "pnr.vcr_date",
    "ServiceStartDate": "c.dep_date",
    "ServiceEndDate":   "c.arr_date",
    "ImportedAt":       "t.import_ts",
}

_FLAT_EXPORT_SQL = """
SELECT
    t.ticket_no          AS PrimaryDocNbr,
    pnr.create_date      AS PNRCreateDate,
    pnr.vcr_date         AS VCRCreateDate,
    a.iata_code          AS Airline,
    cty_od.country_code  AS Country,
    dep_ap.city_name     AS City,
    t.pcc                AS PCC,
    t.agent_sine         AS AgentSine,
    c.coupon_status      AS CouponStatus,
    c.class_of_service   AS ClassOfService,
    c.flight_no          AS FltNo,
    c.flight_no          AS OperatingFlightNbr,
    c.mkt_airline        AS MarketingAirlineCode,
    c.op_airline         AS OperatingAirlineCode,
    c.sector             AS Sector,
    CASE WHEN t.fare_amount IS NOT NULL
         THEN CAST(t.fare_amount AS NVARCHAR(20)) + ' ' + ISNULL(t.fare_currency,'')
         ELSE '' END     AS Fare,
    t.iata_office_no     AS CreateIATANr,
    COALESCE(t.pax_name, p.full_name) AS CustomerFullName,
    c.booking_code       AS BookingCode,
    c.fare_basis         AS FareBasisCode,
    NULL                 AS TourCode,
    c.coupon_seq         AS CouponSeqNbr,
    c.segment_type       AS SegmentTypeCode,
    c.dep_date           AS ServiceStartDate,
    CAST(c.dep_time AS NVARCHAR(8)) AS ServiceStartTime,
    c.arr_date           AS ServiceEndDate,
    CAST(c.arr_time AS NVARCHAR(8)) AS ServiceEndTime,
    NULL                 AS FlownFlightNbr,
    NULL                 AS FlownServiceStartDate,
    NULL                 AS FlownServiceStartCity,
    NULL                 AS FlownServiceEndCity,
    NULL                 AS FlownClassOfService,
    NULL                 AS FlownFlightOrigDate,
    c.dep_airport        AS ServiceStartCity,
    c.arr_airport        AS ServiceEndCity,
    ISNULL(od.origin,'') + ISNULL(od.destination,'') AS OD,
    t.kind               AS Kind,
    od.origin            AS Origin,
    od.destination       AS Destination,
    cty_od.country_name  AS CountryName,
    cty_od.region_name   AS RegionName,
    p.nationality        AS Nationality,
    cty_nat.national_name AS NationalName,
    t.tty_airline        AS TTYAirlineCode
FROM       [dbo].[fact_ticket]    t
LEFT JOIN  [dbo].[fact_coupon]    c   ON c.ticket_no  = t.ticket_no
LEFT JOIN  [dbo].[fact_pnr]       pnr ON pnr.pnr      = t.pnr
LEFT JOIN  [dbo].[dim_passenger]  p   ON p.pnr         = t.pnr AND p.pax_seq = 1
LEFT JOIN  [dbo].[dim_airline]    a   ON a.airline_prefix = LEFT(t.ticket_no, 3)
LEFT JOIN  [dbo].[dim_airport]    dep_ap ON dep_ap.airport_code = c.dep_airport
LEFT JOIN  [dbo].[fact_od]        od  ON od.pnr = t.pnr AND od.seq = 1
LEFT JOIN  [dbo].[dim_country]    cty_od  ON cty_od.country_code  = od.board_nation
LEFT JOIN  [dbo].[dim_country]    cty_nat ON cty_nat.country_code = p.nationality
"""


def query_normalized(
    date_col:  str = "PNRCreateDate",
    year:      int | None = None,
    months:    list[int] | None = None,
    date_from=None,
    date_to=None,
) -> tuple[pd.DataFrame, str]:
    try:
        engine = get_engine()
        col_expr = _NORM_DATE_MAP.get(date_col, "pnr.create_date")
        conditions: list[str] = []
        params: dict = {}

        if year:
            conditions.append(f"YEAR({col_expr}) = :yr")
            params["yr"] = int(year)
        if months:
            placeholders = ", ".join(f":m{i}" for i in range(len(months)))
            conditions.append(f"MONTH({col_expr}) IN ({placeholders})")
            for i, m in enumerate(months):
                params[f"m{i}"] = int(m)
        if date_from:
            conditions.append(f"CAST({col_expr} AS DATE) >= :df")
            params["df"] = str(date_from)
        if date_to:
            conditions.append(f"CAST({col_expr} AS DATE) <= :dt")
            params["dt"] = str(date_to)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        order = "ORDER BY t.ticket_no, c.coupon_seq"
        sql   = text(f"{_FLAT_EXPORT_SQL} {where} {order}")

        df = pd.read_sql(sql, engine, params=params)
        return df, ""
    except SQLAlchemyError as e:
        return pd.DataFrame(), str(e)


def get_available_years_normalized(
    date_col: str = "PNRCreateDate",
) -> list[int]:
    col_expr = _NORM_DATE_MAP.get(date_col, "pnr.create_date")
    table_alias = col_expr.split(".")[0]
    # Map alias to actual table for a simpler sub-query
    _alias_table = {
        "pnr": "[dbo].[fact_pnr]",
        "c":   "[dbo].[fact_coupon]",
        "t":   "[dbo].[fact_ticket]",
    }
    tbl = _alias_table.get(table_alias, "[dbo].[fact_pnr]")
    col = col_expr.split(".")[1]
    try:
        engine = get_engine()
        sql = text(
            f"SELECT DISTINCT YEAR([{col}]) AS yr FROM {tbl} "
            f"WHERE [{col}] IS NOT NULL ORDER BY yr DESC"
        )
        with engine.connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [int(r[0]) for r in rows if r[0] is not None]
    except SQLAlchemyError:
        return []


# ── Private helpers ───────────────────────────────────────────────────────────

def _get_existing_pks(engine, table: str, pk_col: str) -> set:
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(f"SELECT [{pk_col}] FROM [dbo].[{table}]")
            ).fetchall()
        return {str(r[0]).strip() for r in rows}
    except SQLAlchemyError:
        return set()


def _delete_by_fk(engine, table: str, fk_col: str, vals: list) -> None:
    if not vals:
        return
    # MSSQL IN clause limit: chunk at 900 to stay under 1000-parameter limit
    for i in range(0, len(vals), 900):
        chunk = vals[i : i + 900]
        placeholders = ", ".join(f":v{j}" for j in range(len(chunk)))
        params = {f"v{j}": v for j, v in enumerate(chunk)}
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(f"DELETE FROM [dbo].[{table}] "
                         f"WHERE [{fk_col}] IN ({placeholders})"),
                    params,
                )
        except SQLAlchemyError:
            pass


def _seed_dim_tables(engine) -> None:
    """Populate dim_airline / dim_country / dim_airport from config on first use."""
    from core.config import AIRLINE_PREFIX, COUNTRY_MAP, REGION_MAP, NAT_MAP, AIRPORT_CITY

    try:
        with engine.connect() as conn:
            cnt = conn.execute(text("SELECT COUNT(*) FROM [dbo].[dim_airline]")).scalar() or 0
        if cnt == 0:
            rows = [{"airline_prefix": k, "iata_code": v, "airline_name": None}
                    for k, v in AIRLINE_PREFIX.items()]
            pd.DataFrame(rows).to_sql(
                "dim_airline", engine, index=False, if_exists="append", schema="dbo")
    except SQLAlchemyError:
        pass

    try:
        with engine.connect() as conn:
            cnt = conn.execute(text("SELECT COUNT(*) FROM [dbo].[dim_country]")).scalar() or 0
        if cnt == 0:
            # Only 2-char codes — CHAR(2) column rejects longer codes
            rows = [
                {
                    "country_code":  k,
                    "country_name":  COUNTRY_MAP.get(k),
                    "region_name":   REGION_MAP.get(k),
                    "national_name": NAT_MAP.get(k),
                }
                for k in COUNTRY_MAP if len(k) == 2
            ]
            pd.DataFrame(rows).to_sql(
                "dim_country", engine, index=False, if_exists="append", schema="dbo")
    except SQLAlchemyError:
        pass

    try:
        with engine.connect() as conn:
            cnt = conn.execute(text("SELECT COUNT(*) FROM [dbo].[dim_airport]")).scalar() or 0
        if cnt == 0:
            rows = [{"airport_code": k, "city_name": v, "country_code": None}
                    for k, v in AIRPORT_CITY.items()]
            pd.DataFrame(rows).to_sql(
                "dim_airport", engine, index=False, if_exists="append", schema="dbo")
    except SQLAlchemyError:
        pass


def _upsert_dim_from_data(engine, data: dict) -> None:
    """Insert any new airports / airlines / countries found in this batch."""
    from core.config import AIRLINE_PREFIX, COUNTRY_MAP, REGION_MAP, NAT_MAP, AIRPORT_CITY

    # New airports from coupons
    airports = set()
    for r in data.get("coupon", []):
        if r.get("dep_airport"):
            airports.add(r["dep_airport"])
        if r.get("arr_airport"):
            airports.add(r["arr_airport"])
    if airports:
        try:
            existing = _get_existing_pks(engine, "dim_airport", "airport_code")
            new = [{"airport_code": a, "city_name": AIRPORT_CITY.get(a), "country_code": None}
                   for a in airports if len(a) == 3 and a not in existing]
            if new:
                pd.DataFrame(new).to_sql(
                    "dim_airport", engine, index=False, if_exists="append", schema="dbo")
        except SQLAlchemyError:
            pass

    # New airline prefixes from tickets
    prefixes = {r["airline_prefix"] for r in data.get("ticket", []) if r.get("airline_prefix")}
    if prefixes:
        try:
            existing = _get_existing_pks(engine, "dim_airline", "airline_prefix")
            new = [{"airline_prefix": p, "iata_code": AIRLINE_PREFIX.get(p, p), "airline_name": None}
                   for p in prefixes if p not in existing]
            if new:
                pd.DataFrame(new).to_sql(
                    "dim_airline", engine, index=False, if_exists="append", schema="dbo")
        except SQLAlchemyError:
            pass

    # New countries from OD + passengers
    nations: set[str] = set()
    for r in data.get("od", []):
        if r.get("board_nation"):
            nations.add(r["board_nation"])
    for r in data.get("passenger", []):
        if r.get("nationality"):
            nations.add(r["nationality"])
    if nations:
        try:
            existing = _get_existing_pks(engine, "dim_country", "country_code")
            new = [
                {
                    "country_code":  n,
                    "country_name":  COUNTRY_MAP.get(n),
                    "region_name":   REGION_MAP.get(n),
                    "national_name": NAT_MAP.get(n),
                }
                for n in nations if len(n) == 2 and n not in existing
            ]
            if new:
                pd.DataFrame(new).to_sql(
                    "dim_country", engine, index=False, if_exists="append", schema="dbo")
        except SQLAlchemyError:
            pass
