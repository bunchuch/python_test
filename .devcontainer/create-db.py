#!/usr/bin/env python3
"""Wait for SQL Server and create SabreDB if it does not exist."""
import os, sys, time
import pyodbc

server   = os.environ.get("DB_SERVER", "mssql")
password = os.environ.get("DB_PASSWORD", "Sabre@2025!")
driver   = os.environ.get("DB_DRIVER", "ODBC Driver 17 for SQL Server")
db_name  = os.environ.get("DB_NAME", "SabreDB")

conn_str = (
    f"DRIVER={{{driver}}};SERVER={server};UID=sa;PWD={password};"
    "DATABASE=master;TrustServerCertificate=yes"
)

for attempt in range(1, 31):
    try:
        conn = pyodbc.connect(conn_str, autocommit=True, timeout=5)
        conn.execute(
            f"IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'{db_name}') "
            f"CREATE DATABASE [{db_name}]"
        )
        conn.close()
        print(f"[create-db] '{db_name}' is ready.")
        sys.exit(0)
    except Exception as exc:
        print(f"[create-db] waiting for SQL Server ({attempt}/30): {exc}")
        time.sleep(5)

print("[create-db] SQL Server did not become ready in time.", file=sys.stderr)
sys.exit(1)
