import pandas as pd
import streamlit as st

from core.rbac import has_perm, ROLE_BADGE


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
    if has_perm("manage_users"):
        tab_labels.append("👥  Users")
    if has_perm("view_logs"):
        tab_labels.append("📋  System Logs")

    tabs    = st.tabs(tab_labels)
    tab_idx = 0

    # ── Tab: Connection & Config ──────────────────────────────────────────────
    with tabs[tab_idx]:
        _render_connection_tab(test_connection_fn, DB_CONFIG)
    tab_idx += 1

    # ── Tab: User Management (admin + dev) ────────────────────────────────────
    if has_perm("manage_users"):
        with tabs[tab_idx]:
            _render_users_tab()
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
# User Management tab
# ─────────────────────────────────────────────────────────────────────────────

def _render_users_tab() -> None:
    from data.db import (list_users, create_user, toggle_user_active,
                         delete_user, change_password, change_role)

    st.markdown("### :material/group: User Management")

    _ROLE_COLORS = {"user": "#2E86C1", "admin": "#1a7a44", "dev": "#7d3c98"}
    current_username = st.session_state.get("_username", "")
    users = list_users()

    # ── Summary cards ─────────────────────────────────────────────────────────
    total   = len(users)
    active  = sum(1 for u in users if u["is_active"])
    by_role = {r: sum(1 for u in users if u["role"] == r) for r in ("user", "admin", "dev")}
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("Total Users",  total)
    mc2.metric("Active",       active)
    mc3.metric("User",         by_role.get("user",  0))
    mc4.metric("Admin",        by_role.get("admin", 0))
    mc5.metric("Dev",          by_role.get("dev",   0))

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

    # ── User table with inline role badges ────────────────────────────────────
    if users:
        rows_html = ""
        for u in users:
            rc = _ROLE_COLORS.get(u["role"], "#888")
            badge = (
                f"<span style='background:{rc};color:#fff;border-radius:4px;"
                f"padding:2px 9px;font-size:11px;font-weight:700;'>"
                f"{u['role'].capitalize()}</span>"
            )
            active_icon = "✅" if u["is_active"] else "❌"
            self_tag = " (you)" if u["username"] == current_username else ""
            rows_html += (
                f"<tr style='border-bottom:1px solid #f0f3f7;'>"
                f"<td style='padding:8px 10px;color:#666;font-size:12px;'>{u['id']}</td>"
                f"<td style='padding:8px 10px;font-weight:600;color:#1a2d45;'>"
                f"{u['username']}{self_tag}</td>"
                f"<td style='padding:8px 10px;'>{badge}</td>"
                f"<td style='padding:8px 10px;text-align:center;'>{active_icon}</td>"
                f"<td style='padding:8px 10px;font-size:12px;color:#666;'>"
                f"{str(u['created_at'] or '')[:16]}</td>"
                f"<td style='padding:8px 10px;font-size:12px;color:#666;'>"
                f"{str(u['last_login'] or '—')[:16]}</td>"
                f"</tr>"
            )
        st.markdown(
            f"""
            <div style="border:1px solid #e8edf4;border-radius:10px;
                        overflow:hidden;margin-bottom:4px;">
              <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <thead>
                  <tr style="background:#f5f8fd;border-bottom:1.5px solid #e2e8f0;">
                    <th style="padding:9px 10px;text-align:left;color:#7a8a9a;
                               font-size:11px;letter-spacing:.5px;">ID</th>
                    <th style="padding:9px 10px;text-align:left;color:#7a8a9a;
                               font-size:11px;letter-spacing:.5px;">USERNAME</th>
                    <th style="padding:9px 10px;text-align:left;color:#7a8a9a;
                               font-size:11px;letter-spacing:.5px;">ROLE</th>
                    <th style="padding:9px 10px;text-align:center;color:#7a8a9a;
                               font-size:11px;letter-spacing:.5px;">ACTIVE</th>
                    <th style="padding:9px 10px;text-align:left;color:#7a8a9a;
                               font-size:11px;letter-spacing:.5px;">CREATED</th>
                    <th style="padding:9px 10px;text-align:left;color:#7a8a9a;
                               font-size:11px;letter-spacing:.5px;">LAST LOGIN</th>
                  </tr>
                </thead>
                <tbody>{rows_html}</tbody>
              </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No users found.", icon=":material/info:")

    st.markdown("---")

    # ── Create new user ───────────────────────────────────────────────────────
    with st.expander(":material/person_add: Create New User", expanded=False):
        with st.form("create_user_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            new_un   = c1.text_input("Username")
            new_pw   = c2.text_input("Password", type="password")
            new_role = c3.selectbox("Role", ["user", "admin", "dev"],
                                    help="user = query only | admin = full access | dev = admin + logs")
            if st.form_submit_button(
                "Create User", icon=":material/person_add:", type="primary"
            ):
                if new_un and new_pw:
                    ok, msg = create_user(new_un, new_pw, new_role)
                    if ok:
                        st.success(msg, icon=":material/check_circle:")
                        st.rerun()
                    else:
                        st.error(msg, icon=":material/error:")
                else:
                    st.warning("Username and password are required.")

    # ── Manage existing user ──────────────────────────────────────────────────
    other_users = [u for u in users if u["username"] != current_username]
    if not other_users:
        st.info(
            "No other users to manage — you cannot modify your own account here.",
            icon=":material/info:",
        )
        return

    with st.expander(":material/manage_accounts: Manage Existing User", expanded=False):
        sel_username = st.selectbox(
            "Select user to manage",
            [u["username"] for u in other_users],
        )
        sel = next((u for u in other_users if u["username"] == sel_username), None)
        if not sel:
            return

        rc = _ROLE_COLORS.get(sel["role"], "#888")
        st.markdown(
            f"Current role: <span style='background:{rc};color:#fff;border-radius:4px;"
            f"padding:2px 10px;font-size:12px;font-weight:700;'>"
            f"{sel['role'].capitalize()}</span>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        # ── Row 1: Role change ─────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("**:material/swap_horiz: Change Role**")
            role_col, role_btn_col = st.columns([2, 1])
            with role_col:
                new_role_sel = st.selectbox(
                    "New role",
                    [r for r in ("user", "admin", "dev") if r != sel["role"]],
                    label_visibility="collapsed",
                )
            with role_btn_col:
                if st.button(
                    "Apply", icon=":material/check:", type="primary",
                    use_container_width=True, key="role_apply"
                ):
                    ok, msg = change_role(sel["id"], new_role_sel)
                    if ok:
                        st.success(
                            f"**{sel['username']}** is now **{new_role_sel}**.",
                            icon=":material/check_circle:",
                        )
                        st.rerun()
                    else:
                        st.error(msg, icon=":material/error:")
            _desc = {
                "user":  "Query tab only — execute queries and export data.",
                "admin": "Full access — import, query, export, save, manage users.",
                "dev":   "All admin capabilities plus system log access.",
            }
            st.caption(f"ℹ️ {_desc.get(new_role_sel, '')}")

        # ── Row 2: Status toggle + delete ─────────────────────────────────────
        with st.container(border=True):
            st.markdown("**:material/settings: Account Status**")
            toggle_col, del_col = st.columns(2)
            with toggle_col:
                if sel["is_active"]:
                    if st.button(
                        "Disable Account", icon=":material/block:",
                        use_container_width=True,
                    ):
                        ok, msg = toggle_user_active(sel["id"], False)
                        st.success(msg) if ok else st.error(msg)
                        st.rerun()
                else:
                    if st.button(
                        "Enable Account", icon=":material/check_circle:",
                        use_container_width=True, type="primary",
                    ):
                        ok, msg = toggle_user_active(sel["id"], True)
                        st.success(msg) if ok else st.error(msg)
                        st.rerun()
            with del_col:
                if st.button(
                    "Delete User", icon=":material/delete:",
                    use_container_width=True,
                ):
                    ok, msg = delete_user(sel["id"])
                    st.success(msg) if ok else st.error(msg)
                    st.rerun()

        # ── Row 3: Password reset ──────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("**:material/key: Reset Password**")
            with st.form("change_pw_form", clear_on_submit=True):
                pw_col, btn_col = st.columns([3, 1])
                new_pw2 = pw_col.text_input("New password", type="password",
                                            label_visibility="collapsed",
                                            placeholder="Enter new password")
                with btn_col:
                    if st.form_submit_button(
                        "Update", icon=":material/save:", type="primary",
                        use_container_width=True
                    ):
                        if new_pw2:
                            ok, msg = change_password(sel_username, new_pw2)
                            st.success(msg) if ok else st.error(msg)
                        else:
                            st.warning("Password cannot be empty.")


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
