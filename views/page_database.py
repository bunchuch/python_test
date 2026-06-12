import pandas as pd
import streamlit as st

from core.rbac import has_perm


def render(db_available: bool, test_connection_fn) -> None:
    st.title(":material/storage: Database")

    if not db_available:
        st.error(
            "SQLAlchemy is not installed. Run the command below, then restart the app.",
            icon=":material/error:",
        )
        st.code("pip install sqlalchemy pyodbc", language="bash")
        return

    # ── Role gate ─────────────────────────────────────────────────────────────
    if not has_perm("access_database"):
        st.error(
            "Access denied — your account does not have permission to view this page.",
            icon=":material/block:",
        )
        return

    from data.db import DB_CONFIG

    db  = DB_CONFIG.get("database", "—")
    srv = DB_CONFIG.get("server",   "—")
    st.markdown(
        f"""
        <div style="border:1px solid #a8d5b5;border-radius:12px;
                    background:linear-gradient(135deg,#e8f8ee,#f4fff7);
                    padding:20px 24px;display:flex;align-items:center;gap:16px;
                    margin-bottom:4px;">
          <span style="font-size:36px;">🏭</span>
          <div>
            <div style="font-size:14px;font-weight:700;color:#1a4731;">
              SQL Server
            </div>
            <div style="font-size:12px;color:#333;margin-top:4px;line-height:1.6;">
              Database <b>{db}</b> on server <b>{srv}</b>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── Build tab list dynamically based on role ──────────────────────────────
    tab_labels = ["⚡  Connection & Config"]
    if has_perm("view_logs"):
        tab_labels.append("📋  System Logs")

    tabs    = st.tabs(tab_labels)
    tab_idx = 0

    # ── Tab: Connection & Config ──────────────────────────────────────────────
    with tabs[tab_idx]:
        _render_connection_tab(test_connection_fn, DB_CONFIG)
    tab_idx += 1

    # ── Tab: System Logs (dev only) ───────────────────────────────────────────
    if has_perm("view_logs"):
        with tabs[tab_idx]:
            _render_logs_tab()


# ─────────────────────────────────────────────────────────────────────────────
# Connection & Config
# ─────────────────────────────────────────────────────────────────────────────

def _render_connection_tab(test_fn, db_config) -> None:
    st.markdown("### :material/power: Connection")

    btn_col, result_col = st.columns([1, 3])
    with btn_col:
        test_clicked = st.button(
            "Test Connection",
            icon=":material/refresh:",
            type="primary",
            use_container_width=True,
        )

    if test_clicked:
        with st.spinner("Connecting…"):
            ok, msg = test_fn()
        st.session_state["db_status"] = (ok, msg)

    if "db_status" in st.session_state:
        ok, msg = st.session_state["db_status"]
        with result_col:
            if ok:
                st.success(msg, icon=":material/check_circle:")
            else:
                st.error(msg, icon=":material/error:")

    st.markdown("---")
    st.markdown("### :material/settings: Current Configuration")

    auth = "SQL Server Auth" if db_config.get("username") else "Windows Auth"
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mode",     "SQL Server")
    c2.metric("Server",   db_config.get("server",   "—"))
    c3.metric("Database", db_config.get("database", "—"))
    c4.metric("Auth",     auth)

    st.markdown("---")
    st.markdown("### :material/settings_ethernet: Connection Details")
    st.caption("Override any value via environment variables before starting the app.")

    with st.container(border=True):
        st.markdown("**Environment variables**")
        st.code(
            "DB_SERVER=YOUR_SERVER\\INSTANCE\n"
            "DB_NAME=SabreDB\n"
            "DB_DRIVER=ODBC Driver 17 for SQL Server\n"
            "DB_USER=        # leave blank for Windows Authentication\n"
            "DB_PASSWORD=",
            language="bash",
        )
        st.info(
            "Download the ODBC driver from Microsoft: "
            "https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server",
            icon=":material/open_in_new:",
        )


# ─────────────────────────────────────────────────────────────────────────────
# System Logs tab
# ─────────────────────────────────────────────────────────────────────────────

def _render_logs_tab() -> None:
    from data.db import get_logs

    st.markdown("### :material/list_alt: System Logs")

    hdr_col, refresh_col = st.columns([4, 1])
    with hdr_col:
        st.caption("Last 200 events, newest first.")
    with refresh_col:
        if st.button("Refresh", icon=":material/refresh:", use_container_width=True):
            st.rerun()

    logs = get_logs(200)
    if not logs:
        st.info("No log entries yet.", icon=":material/info:")
        return

    df_logs = pd.DataFrame(logs)
    df_logs.columns = ["Timestamp", "Event", "User", "Detail"]
    st.dataframe(df_logs, use_container_width=True, hide_index=True, height=450)
