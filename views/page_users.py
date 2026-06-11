import pandas as pd
import streamlit as st
from core.rbac import has_perm

_ROLE_DESC = {
    "user":  "Query tab only — execute queries and export data.",
    "admin": "Full access — import, query, export, save, manage users.",
    "dev":   "All admin capabilities plus system log access.",
}


def render() -> None:
    st.title(":material/group: Users")

    if not has_perm("manage_users"):
        st.error(
            "Access denied — your account does not have permission to view this page.",
            icon=":material/block:",
        )
        return

    from data.db import (list_users, create_user, toggle_user_active,
                         delete_user, change_password, change_role)

    users            = list_users()
    current_username = st.session_state.get("_username", "")

    # ── Summary stats — gradient cards ────────────────────────────────────────
    total   = len(users)
    active  = sum(1 for u in users if u["is_active"])
    by_role = {r: sum(1 for u in users if u["role"] == r)
               for r in ("user", "admin", "dev")}

    st.markdown(
        f"""
        <div class="fs-metrics">
            <div class="fs-card">
                <div class="fs-lbl">Total Users</div>
                <div class="fs-val">{total}</div>
            </div>
            <div class="fs-card">
                <div class="fs-lbl">Active</div>
                <div class="fs-val">{active}</div>
            </div>
            <div class="fs-card"
                 style="background:linear-gradient(135deg,#c0392b 0%,#e74c3c 100%);">
                <div class="fs-lbl">Inactive</div>
                <div class="fs-val">{total - active}</div>
            </div>
            <div class="fs-card"
                 style="background:linear-gradient(135deg,#1a7a44 0%,#27ae60 100%);">
                <div class="fs-lbl">Admin</div>
                <div class="fs-val">{by_role.get("admin", 0)}</div>
            </div>
            <div class="fs-card"
                 style="background:linear-gradient(135deg,#5c2d8a 0%,#8e44ad 100%);">
                <div class="fs-lbl">Dev</div>
                <div class="fs-val">{by_role.get("dev", 0)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Header + Add User button ──────────────────────────────────────────────
    hdr, add_col = st.columns([5, 1], gap="small")
    with hdr:
        st.markdown("### :material/badge: All Users")
    with add_col:
        show_create = st.button(
            "Add User",
            icon=":material/person_add:",
            type="primary",
            use_container_width=True,
        )

    # ── Create user form ──────────────────────────────────────────────────────
    if show_create or st.session_state.get("_show_create_user"):
        st.session_state["_show_create_user"] = True
        with st.container(border=True):
            st.markdown("#### :material/person_add: New User")
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1], gap="small")
            new_un   = c1.text_input("Username", key="new_un", placeholder="username")
            new_pw   = c2.text_input("Password", key="new_pw",
                                     type="password", placeholder="password")
            new_role = c3.selectbox("Role", key="new_role",
                                    options=["user", "admin", "dev"])
            c4.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            b1, b2 = c4.columns(2)
            if b1.button("Save", type="primary",
                         use_container_width=True, key="save_new_user"):
                if new_un and new_pw:
                    ok, msg = create_user(new_un, new_pw, new_role)
                    if ok:
                        st.success(msg, icon=":material/check_circle:")
                        st.session_state.pop("_show_create_user", None)
                        st.rerun()
                    else:
                        st.error(msg, icon=":material/error:")
                else:
                    st.warning("Username and password are required.")
            if b2.button("Cancel", use_container_width=True, key="cancel_new_user"):
                st.session_state.pop("_show_create_user", None)
                st.rerun()

    # ── Users table ───────────────────────────────────────────────────────────
    if not users:
        st.info("No users found.", icon=":material/info:")
        return

    rows = [
        {
            "Username":   u["username"] + (" (you)" if u["username"] == current_username else ""),
            "Role":       u["role"].capitalize(),
            "Status":     "Active" if u["is_active"] else "Inactive",
            "ID":         u["id"],
            "Created":    str(u.get("created_at") or "")[:10] or "—",
            "Last Login": str(u.get("last_login")  or "")[:16] or "—",
        }
        for u in users
    ]
    df = pd.DataFrame(rows)

    def _style(data: pd.DataFrame) -> pd.DataFrame:
        role_bg = {"User": "#dbeeff", "Admin": "#d4f5e2", "Dev": "#eedcff"}
        role_fg = {"User": "#1a5a9a", "Admin": "#1a5a33", "Dev": "#5c2d8a"}
        stat_bg = {"Active": "#d4f5e2", "Inactive": "#fdecea"}
        stat_fg = {"Active": "#1a5a33", "Inactive": "#a31515"}

        out = pd.DataFrame("", index=data.index, columns=data.columns)
        for i, val in enumerate(data["Role"]):
            out.at[i, "Role"] = (
                f"background-color:{role_bg.get(val,'')};color:{role_fg.get(val,'')};font-weight:700;"
            )
        for i, val in enumerate(data["Status"]):
            out.at[i, "Status"] = (
                f"background-color:{stat_bg.get(val,'')};color:{stat_fg.get(val,'')};font-weight:700;"
            )
        return out

    st.dataframe(
        df.style.apply(_style, axis=None),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Username":   st.column_config.TextColumn("Username"),
            "Role":       st.column_config.TextColumn("Role"),
            "Status":     st.column_config.TextColumn("Status"),
            "ID":         st.column_config.NumberColumn("ID", width="small"),
            "Created":    st.column_config.TextColumn("Created"),
            "Last Login": st.column_config.TextColumn("Last Login"),
        },
    )

    # ── Manage panel ─────────────────────────────────────────────────────────
    other_users = [u for u in users if u["username"] != current_username]
    if not other_users:
        return

    st.markdown("---")
    st.markdown("### :material/manage_accounts: Manage User")

    sel_col, _ = st.columns([2, 3], gap="small")
    with sel_col:
        sel_username = st.selectbox(
            "Select user",
            [u["username"] for u in other_users],
            label_visibility="collapsed",
        )
    sel = next((u for u in other_users if u["username"] == sel_username), None)
    if not sel:
        return

    a1, a2, a3 = st.columns(3, gap="small")

    # ── Change Role ───────────────────────────────────────────────────────────
    with a1:
        with st.container(border=True):
            st.markdown("**:material/swap_horiz: Change Role**")
            new_role_sel = st.selectbox(
                "New role",
                [r for r in ("user", "admin", "dev") if r != sel["role"]],
                key="mgmt_role",
                label_visibility="collapsed",
            )
            st.caption(_ROLE_DESC.get(new_role_sel, ""))
            if st.button("Apply Role", type="primary",
                         use_container_width=True, key="apply_role"):
                ok, msg = change_role(sel["id"], new_role_sel)
                st.success(msg, icon=":material/check_circle:") if ok else st.error(msg)
                if ok:
                    st.rerun()

    # ── Reset Password ────────────────────────────────────────────────────────
    with a2:
        with st.container(border=True):
            st.markdown("**:material/key: Reset Password**")
            with st.form("reset_pw_form", clear_on_submit=True):
                new_pw2 = st.text_input(
                    "New password", type="password",
                    placeholder="Enter new password",
                    label_visibility="collapsed",
                )
                if st.form_submit_button("Update Password", type="primary",
                                         use_container_width=True):
                    if new_pw2:
                        ok, msg = change_password(sel_username, new_pw2)
                        st.success(msg) if ok else st.error(msg)
                    else:
                        st.warning("Password cannot be empty.")

    # ── Status & Delete ───────────────────────────────────────────────────────
    with a3:
        with st.container(border=True):
            st.markdown("**:material/settings: Account**")
            if sel["is_active"]:
                if st.button("Disable Account", icon=":material/block:",
                             use_container_width=True, key="toggle_active"):
                    ok, msg = toggle_user_active(sel["id"], False)
                    st.success(msg) if ok else st.error(msg)
                    st.rerun()
            else:
                if st.button("Enable Account", icon=":material/check_circle:",
                             type="primary", use_container_width=True,
                             key="toggle_active"):
                    ok, msg = toggle_user_active(sel["id"], True)
                    st.success(msg) if ok else st.error(msg)
                    st.rerun()

            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

            if st.button("Delete User", icon=":material/delete:",
                         use_container_width=True, key="delete_user"):
                ok, msg = delete_user(sel["id"])
                st.success(msg) if ok else st.error(msg)
                st.rerun()
