"""
DDL migration statements for the users and system_logs tables.

These are idempotent (CREATE IF NOT EXISTS / IF NOT EXISTS guard) so they can
be run on every startup without side-effects.
"""

# ── SQLite dialect ─────────────────────────────────────────────────────────────
_SQLITE: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT    NOT NULL UNIQUE,
        password_hash TEXT    NOT NULL,
        role          TEXT    NOT NULL DEFAULT 'user',
        is_active     INTEGER NOT NULL DEFAULT 1,
        created_at    TEXT    DEFAULT (datetime('now')),
        last_login    TEXT    NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS system_logs (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        ts         TEXT    DEFAULT (datetime('now')),
        event_type TEXT    NULL,
        username   TEXT    NULL,
        detail     TEXT    NULL
    );
    """,
]

# ── SQL Server dialect ─────────────────────────────────────────────────────────
_MSSQL: list[str] = [
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'users' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[users] (
            id            INT           IDENTITY(1,1) PRIMARY KEY,
            username      NVARCHAR(64)  NOT NULL UNIQUE,
            password_hash NVARCHAR(256) NOT NULL,
            role          NVARCHAR(20)  NOT NULL DEFAULT 'user',
            is_active     BIT           NOT NULL DEFAULT 1,
            created_at    DATETIME2     DEFAULT GETUTCDATE(),
            last_login    DATETIME2     NULL
        );
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'system_logs' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[system_logs] (
            id         INT           IDENTITY(1,1) PRIMARY KEY,
            ts         DATETIME2     DEFAULT GETUTCDATE(),
            event_type NVARCHAR(50)  NULL,
            username   NVARCHAR(64)  NULL,
            detail     NVARCHAR(500) NULL
        );
    END
    """,
]


def get_ddl(db_mode: str) -> list[str]:
    """Return the list of DDL statements for *db_mode* ('sqlite' | 'sqlserver')."""
    return _SQLITE if db_mode == "sqlite" else _MSSQL
