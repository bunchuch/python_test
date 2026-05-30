import streamlit as st


def render(db_available: bool, test_connection_fn) -> None:
    st.title(":material/storage: Database Connection")

    if not db_available:
        st.error("SQLAlchemy is not installed.", icon=":material/error:")
        st.code("pip install sqlalchemy", language="bash")
        return

    from data.db import DB_MODE, SQLITE_PATH, DB_CONFIG

    # ── Active mode banner ─────────────────────────────────────────────────────
    if DB_MODE == "sqlite":
        st.info(
            f"**Mode: SQLite (testing)** — data is stored in `{SQLITE_PATH}` "
            "in the project folder. No driver or server required.",
            icon=":material/science:",
        )
    else:
        st.success(
            f"**Mode: SQL Server (production)** — "
            f"`{DB_CONFIG.get('database')}` on `{DB_CONFIG.get('server')}`",
            icon=":material/factory:",
        )

    # ── Test connection ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## Connection Status")
    col_btn, col_result = st.columns([1, 3])
    with col_btn:
        if st.button("Test Connection", icon=":material/power:",
                     type="primary", use_container_width=True):
            with st.spinner("Connecting…"):
                ok, msg = test_connection_fn()
            st.session_state["db_status"] = (ok, msg)

    if "db_status" in st.session_state:
        ok, msg = st.session_state["db_status"]
        with col_result:
            if ok:
                st.success(msg, icon=":material/check_circle:")
            else:
                st.error(msg, icon=":material/error:")

    # ── Current config ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## Current Configuration")

    if DB_MODE == "sqlite":
        c1, c2 = st.columns(2)
        c1.metric("Mode", "SQLite")
        c2.metric("File", SQLITE_PATH)
    else:
        auth = "SQL Server Auth" if DB_CONFIG.get("username") else "Windows Auth"
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mode",     "SQL Server")
        c2.metric("Server",   DB_CONFIG.get("server", "—"))
        c3.metric("Database", DB_CONFIG.get("database", "—"))
        c4.metric("Auth",     auth)

    # ── How to switch ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## How to Switch Mode")
    st.markdown("Edit **`db.py`** → change `DB_MODE`, then restart the app.")

    tab_sqlite, tab_sql = st.tabs([
        ":material/science: SQLite (testing)",
        ":material/factory: SQL Server (production)",
    ])

    with tab_sqlite:
        st.markdown("Zero setup — perfect for local development and testing.")
        st.code(
            'DB_MODE = "sqlite"\n'
            'SQLITE_PATH = "sabre_test.db"   # file created automatically',
            language="python",
        )

    with tab_sql:
        st.markdown("Requires `pyodbc` and the Microsoft ODBC Driver.")
        st.code("pip install pyodbc", language="bash")
        st.code(
            'DB_MODE = "sqlserver"\n\n'
            'DB_CONFIG = {\n'
            '    "server":   "YOUR_SERVER",\n'
            '    "database": "SabreDB",\n'
            '    "driver":   "ODBC Driver 17 for SQL Server",\n'
            '    "username": "",   # blank = Windows Auth\n'
            '    "password": "",\n'
            '}',
            language="python",
        )
        st.info(
            "ODBC Driver download: "
            "https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server",
            icon=":material/info:",
        )
