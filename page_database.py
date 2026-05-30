import streamlit as st


def render(db_available: bool, test_connection_fn) -> None:
    st.title("🗄️ Database Connection")
    st.markdown("Configure and test the SQL Server connection used to save processed data.")

    if not db_available:
        st.error("SQL Server packages are not installed.")
        st.code("pip install sqlalchemy pyodbc", language="bash")
        return

    from db import DB_CONFIG

    # ── Connection status ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## Connection Status")
    status_col, info_col = st.columns([1, 2])
    with status_col:
        if st.button("🔌 Test Connection", type="primary", use_container_width=True):
            with st.spinner("Connecting..."):
                ok, msg = test_connection_fn()
            st.session_state["db_status"] = (ok, msg)

    if "db_status" in st.session_state:
        ok, msg = st.session_state["db_status"]
        with info_col:
            if ok:
                st.success(f"🟢 **Connected** — {msg}")
            else:
                st.error(f"🔴 **Failed** — {msg}")

    # ── Current config ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## Current Configuration")
    st.markdown("Edit **`db.py`** → `DB_CONFIG` to change these values, then restart the app.")

    auth = "SQL Server Auth" if DB_CONFIG.get("username") else "Windows Auth"
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Server",   DB_CONFIG.get("server",   "—"))
    c2.metric("Database", DB_CONFIG.get("database", "—"))
    c3.metric("Driver",   DB_CONFIG.get("driver", "—")[:22] + "…")
    c4.metric("Auth",     auth)

    # ── Config examples ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## How to Configure")
    tab1, tab2 = st.tabs(["Windows Auth", "SQL Server Auth"])
    with tab1:
        st.markdown("Use this when the app runs on a Windows machine with domain access.")
        st.code("""
DB_CONFIG = {
    "server":   "YOUR_SERVER",          # e.g. "192.168.1.10" or "SERVER\\\\INSTANCE"
    "database": "SabreDB",
    "driver":   "ODBC Driver 17 for SQL Server",
    "username": "",                     # blank = Windows Auth
    "password": "",
}
""", language="python")
    with tab2:
        st.markdown("Use this when connecting with a SQL Server login.")
        st.code("""
DB_CONFIG = {
    "server":   "YOUR_SERVER",
    "database": "SabreDB",
    "driver":   "ODBC Driver 17 for SQL Server",
    "username": "sa",
    "password": "your_password",
}
""", language="python")

    st.markdown("---")
    st.info(
        "**ODBC Driver required** — download from Microsoft if not installed:  \n"
        "https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server"
    )
