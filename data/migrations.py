"""
DDL migration statements for the users and system_logs tables.

These are idempotent (IF NOT EXISTS guard) so they can be run on every
startup without side-effects.
"""

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


def get_ddl() -> list[str]:
    return _MSSQL


# ── Normalized star-schema DDL ─────────────────────────────────────────────────
# No FK constraints — ordering in save_normalized_batch() ensures referential
# integrity without the risk of FK violations from partial dimension coverage.
_NORMALIZED_MSSQL: list[str] = [
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'dim_airline' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[dim_airline] (
            airline_prefix  CHAR(3)        NOT NULL PRIMARY KEY,
            iata_code       VARCHAR(3)     NOT NULL,
            airline_name    NVARCHAR(100)  NULL
        );
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'dim_country' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[dim_country] (
            country_code   CHAR(2)        NOT NULL PRIMARY KEY,
            country_name   NVARCHAR(100)  NULL,
            region_name    NVARCHAR(50)   NULL,
            national_name  NVARCHAR(50)   NULL
        );
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'dim_airport' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[dim_airport] (
            airport_code  CHAR(3)        NOT NULL PRIMARY KEY,
            city_name     NVARCHAR(100)  NULL,
            country_code  CHAR(2)        NULL
        );
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'fact_pnr' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[fact_pnr] (
            pnr            VARCHAR(10)   NOT NULL PRIMARY KEY,
            create_date    DATE          NULL,
            vcr_date       DATETIME2     NULL,
            airline        VARCHAR(3)    NULL,
            pcc            VARCHAR(10)   NULL,
            agent_sine     VARCHAR(20)   NULL,
            iata_office_no VARCHAR(10)   NULL,
            tty_code       VARCHAR(10)   NULL,
            import_ts      DATETIME2     DEFAULT GETDATE()
        );
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'fact_ticket' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[fact_ticket] (
            ticket_no      CHAR(13)       NOT NULL PRIMARY KEY,
            pnr            VARCHAR(10)    NULL,
            airline_prefix CHAR(3)        NULL,
            agent_sine     VARCHAR(30)    NULL,
            pcc            VARCHAR(10)    NULL,
            pax_name       NVARCHAR(100)  NULL,
            fare_amount    DECIMAL(12,2)  NULL,
            fare_currency  CHAR(3)        NULL,
            iata_office_no VARCHAR(10)    NULL,
            kind           VARCHAR(10)    NULL,
            tty_airline    VARCHAR(10)    NULL,
            batch_label    NVARCHAR(100)  NULL,
            import_ts      DATETIME2      DEFAULT GETDATE()
        );
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'fact_coupon' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[fact_coupon] (
            coupon_id        INT IDENTITY(1,1) PRIMARY KEY,
            ticket_no        CHAR(13)     NULL,
            coupon_seq       TINYINT      NULL,
            coupon_status    VARCHAR(10)  NULL,
            class_of_service CHAR(1)      NULL,
            flight_no        VARCHAR(10)  NULL,
            mkt_airline      VARCHAR(3)   NULL,
            op_airline       VARCHAR(3)   NULL,
            dep_airport      CHAR(3)      NULL,
            arr_airport      CHAR(3)      NULL,
            dep_date         DATE         NULL,
            dep_time         TIME         NULL,
            arr_date         DATE         NULL,
            arr_time         TIME         NULL,
            fare_basis       VARCHAR(20)  NULL,
            booking_code     CHAR(1)      NULL,
            segment_type     VARCHAR(5)   NULL,
            sector           VARCHAR(10)  NULL,
            import_ts        DATETIME2    DEFAULT GETDATE()
        );
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'dim_passenger' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[dim_passenger] (
            pax_id       INT IDENTITY(1,1) PRIMARY KEY,
            pnr          VARCHAR(10)    NULL,
            pax_seq      TINYINT        NULL,
            first_name   NVARCHAR(50)   NULL,
            last_name    NVARCHAR(50)   NULL,
            full_name    NVARCHAR(100)  NULL,
            doc_number   VARCHAR(20)    NULL,
            doc_type     CHAR(2)        NULL,
            nationality  CHAR(2)        NULL,
            gender       CHAR(1)        NULL,
            dob          DATE           NULL,
            import_ts    DATETIME2      DEFAULT GETDATE()
        );
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'fact_od' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[fact_od] (
            od_id        INT IDENTITY(1,1) PRIMARY KEY,
            pnr          VARCHAR(10)  NULL,
            seq          TINYINT      NULL,
            origin       CHAR(3)      NULL,
            destination  CHAR(3)      NULL,
            board_nation CHAR(2)      NULL,
            import_ts    DATETIME2    DEFAULT GETDATE()
        );
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'fact_ticket_history' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[fact_ticket_history] (
            history_id  INT IDENTITY(1,1) PRIMARY KEY,
            ticket_no   CHAR(13)    NULL,
            action      VARCHAR(10) NULL,
            agent_sine  VARCHAR(30) NULL,
            action_date DATETIME2   NULL,
            import_ts   DATETIME2   DEFAULT GETDATE()
        );
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'fact_payment' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[fact_payment] (
            payment_id    INT IDENTITY(1,1) PRIMARY KEY,
            ticket_no     CHAR(13)      NULL,
            payment_code  VARCHAR(5)    NULL,
            amount        DECIMAL(12,2) NULL,
            currency      CHAR(3)       NULL,
            payment_type  VARCHAR(10)   NULL,
            import_ts     DATETIME2     DEFAULT GETDATE()
        );
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.tables
        WHERE name = 'fact_tax' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        CREATE TABLE [dbo].[fact_tax] (
            tax_id      INT IDENTITY(1,1) PRIMARY KEY,
            ticket_no   CHAR(13)      NULL,
            tax_amount  DECIMAL(12,2) NULL,
            tax_code    VARCHAR(5)    NULL,
            currency    CHAR(3)       NULL,
            import_ts   DATETIME2     DEFAULT GETDATE()
        );
    END
    """,
    # Indexes
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes
                   WHERE name = 'ix_ticket_pnr'
                   AND object_id = OBJECT_ID('dbo.fact_ticket'))
        CREATE INDEX ix_ticket_pnr ON [dbo].[fact_ticket](pnr);
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes
                   WHERE name = 'ix_coupon_ticket'
                   AND object_id = OBJECT_ID('dbo.fact_coupon'))
        CREATE INDEX ix_coupon_ticket ON [dbo].[fact_coupon](ticket_no);
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes
                   WHERE name = 'ix_coupon_status'
                   AND object_id = OBJECT_ID('dbo.fact_coupon'))
        CREATE INDEX ix_coupon_status ON [dbo].[fact_coupon](coupon_status);
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes
                   WHERE name = 'ix_pax_pnr'
                   AND object_id = OBJECT_ID('dbo.dim_passenger'))
        CREATE INDEX ix_pax_pnr ON [dbo].[dim_passenger](pnr);
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM sys.indexes
                   WHERE name = 'ix_od_pnr'
                   AND object_id = OBJECT_ID('dbo.fact_od'))
        CREATE INDEX ix_od_pnr ON [dbo].[fact_od](pnr);
    """,
]


def get_normalized_ddl() -> list[str]:
    return _NORMALIZED_MSSQL
