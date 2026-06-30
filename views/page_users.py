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
                         delete_user, change_password, change_role, next_user_code)

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

    # ── Top-level tabs ────────────────────────────────────────────────────────
    tab_all, tab_add, tab_role, tab_pw, tab_account = st.tabs([
        ":material/badge: All Users",
        ":material/person_add: Add User",
        ":material/swap_horiz: Change Role",
        ":material/key: Reset Password",
        ":material/settings: Account",
    ])

    # ── Tab: All Users ────────────────────────────────────────────────────────
    with tab_all:
        if not users:
            st.info("No users found.", icon=":material/info:")
        else:
            rows = [
                {
                    "User ID":    f"K6-{u['id']:03d}",
                    "Username":   u["username"] + (" (you)" if u["username"] == current_username else ""),
                    "Role":       u["role"].capitalize(),
                    "Status":     "Active" if u["is_active"] else "Inactive",
                    "Created":    str(u.get("created_at") or "")[:10] or "—",
                    "Last Login": str(u.get("last_login")  or "")[:16] or "—",
                }
                for u in users
            ]
            df = pd.DataFrame(rows)

            def _style(data: pd.DataFrame) -> pd.DataFrame:
                role_fg = {"User": "#1e3a8a", "Admin": "#1a7a44", "Dev": "#5c2d8a"}
                stat_fg = {"Active": "#1a7a44", "Inactive": "#c0392b"}

                out = pd.DataFrame("", index=data.index, columns=data.columns)
                for i, val in enumerate(data["Role"]):
                    out.at[i, "Role"] = f"color:{role_fg.get(val,'')};font-weight:700;"
                for i, val in enumerate(data["Status"]):
                    out.at[i, "Status"] = f"color:{stat_fg.get(val,'')};font-weight:700;"
                return out

            _PAGE_SIZES = [10, 25, 50]
            total_rows  = len(df)

            if "usr_page" not in st.session_state:
                st.session_state["usr_page"] = 0
            if "usr_size" not in st.session_state:
                st.session_state["usr_size"] = 10

            usr_sig = str((total_rows,))
            if st.session_state.get("_usr_sig") != usr_sig:
                st.session_state["usr_page"] = 0
                st.session_state["_usr_sig"] = usr_sig

            page_size   = st.session_state["usr_size"]
            total_pages = max(1, (total_rows + page_size - 1) // page_size)
            page        = min(st.session_state["usr_page"], total_pages - 1)
            st.session_state["usr_page"] = page

            start_idx = page * page_size
            end_idx   = min(start_idx + page_size, total_rows)
            page_df   = df.iloc[start_idx:end_idx]

            st.dataframe(
                page_df.style.apply(_style, axis=None),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "User ID":    st.column_config.TextColumn("User ID", width="small"),
                    "Username":   st.column_config.TextColumn("Username"),
                    "Role":       st.column_config.TextColumn("Role"),
                    "Status":     st.column_config.TextColumn("Status"),
                    "Created":    st.column_config.TextColumn("Created"),
                    "Last Login": st.column_config.TextColumn("Last Login"),
                },
            )

            sz_col, prev_col, info_col, next_col, rows_col = st.columns(
                [1.4, 0.5, 2, 0.5, 2], gap="small"
            )
            with sz_col:
                def _reset_usr_page():
                    st.session_state["usr_page"] = 0
                st.selectbox(
                    "Rows/page",
                    _PAGE_SIZES,
                    index=_PAGE_SIZES.index(page_size) if page_size in _PAGE_SIZES else 0,
                    key="usr_size",
                    on_change=_reset_usr_page,
                    label_visibility="collapsed",
                )
            with prev_col:
                if st.button("", icon=":material/chevron_left:",
                             use_container_width=True, key="usr_prev",
                             disabled=(page == 0)):
                    st.session_state["usr_page"] -= 1
                    st.rerun()
            with info_col:
                st.markdown(
                    f"<p style='text-align:center;margin:0;padding-top:7px;"
                    f"font-size:13px;color:#444;'>"
                    f"Page <b>{page + 1}</b> / <b>{total_pages}</b></p>",
                    unsafe_allow_html=True,
                )
            with next_col:
                if st.button("", icon=":material/chevron_right:",
                             use_container_width=True, key="usr_next",
                             disabled=(page >= total_pages - 1)):
                    st.session_state["usr_page"] += 1
                    st.rerun()
            with rows_col:
                st.markdown(
                    f"<p style='text-align:right;margin:0;padding-top:7px;"
                    f"font-size:12px;color:#888;'>"
                    f"Rows {start_idx + 1:,} – {end_idx:,} of {total_rows:,}</p>",
                    unsafe_allow_html=True,
                )

    # ── Tab: Add User ─────────────────────────────────────────────────────────
    with tab_add:
        auto_id = next_user_code()
        with st.container(border=True):
            st.markdown("#### :material/person_add: New User")
            id_col, un_col, pw_col = st.columns([1, 2, 2], gap="small")
            id_col.text_input(
                "User ID",
                value=auto_id,
                disabled=True,
                help="Auto-generated ID — assigned when account is created.",
            )
            new_un = un_col.text_input("Username", key="new_un", placeholder="username")
            new_pw = pw_col.text_input("Password", key="new_pw",
                                       type="password", placeholder="password")
            c3, c4 = st.columns(2, gap="small")
            new_role = c3.selectbox("Role", key="new_role",
                                    options=["user", "admin", "dev"])
            c3.caption(_ROLE_DESC.get(new_role, ""))
            c4.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if c4.button("Create User", type="primary",
                         use_container_width=True, key="save_new_user"):
                if new_un and new_pw:
                    ok, msg = create_user(new_un, new_pw, new_role)
                    if ok:
                        st.success(msg, icon=":material/check_circle:")
                        st.rerun()
                    else:
                        st.error(msg, icon=":material/error:")
                else:
                    st.warning("Username and password are required.")

    # ── Shared user selector for manage tabs ─────────────────────────────────
    other_users = [u for u in users if u["username"] != current_username]

    # ── Tab: Change Role ──────────────────────────────────────────────────────
    with tab_role:
        if not other_users:
            st.info("No other users to manage.", icon=":material/info:")
        else:
            sel_col, _ = st.columns([2, 3], gap="small")
            sel_role_user = sel_col.selectbox(
                "Select user",
                [u["username"] for u in other_users],
                key="sel_role_user",
                label_visibility="collapsed",
            )
            sel_r = next((u for u in other_users if u["username"] == sel_role_user), None)
            if sel_r:
                st.markdown(f"Current role: **{sel_r['role'].capitalize()}**")
                other_roles = [r for r in ("user", "admin", "dev") if r != sel_r["role"]]
                new_role_sel = st.selectbox(
                    "New role",
                    other_roles,
                    key="mgmt_role",
                    label_visibility="collapsed",
                )
                st.caption(_ROLE_DESC.get(new_role_sel, ""))
                st.markdown("")
                if st.button("Apply Role", type="primary", key="apply_role"):
                    ok, msg = change_role(sel_r["id"], new_role_sel)
                    st.success(msg, icon=":material/check_circle:") if ok else st.error(msg)
                    if ok:
                        st.rerun()

    # ── Tab: Reset Password ───────────────────────────────────────────────────
    with tab_pw:
        if not other_users:
            st.info("No other users to manage.", icon=":material/info:")
        else:
            sel_col2, _ = st.columns([2, 3], gap="small")
            sel_pw_user = sel_col2.selectbox(
                "Select user",
                [u["username"] for u in other_users],
                key="sel_pw_user",
                label_visibility="collapsed",
            )
            st.markdown(f"Reset password for **{sel_pw_user}**")
            with st.form("reset_pw_form", clear_on_submit=True):
                new_pw2 = st.text_input(
                    "New password",
                    type="password",
                    placeholder="Enter new password",
                )
                confirm_pw = st.text_input(
                    "Confirm password",
                    type="password",
                    placeholder="Confirm new password",
                )
                if st.form_submit_button("Update Password", type="primary"):
                    if not new_pw2:
                        st.warning("Password cannot be empty.")
                    elif new_pw2 != confirm_pw:
                        st.error("Passwords do not match.", icon=":material/error:")
                    else:
                        ok, msg = change_password(sel_pw_user, new_pw2)
                        st.success(msg, icon=":material/check_circle:") if ok else st.error(msg)

    # ── Tab: Account ──────────────────────────────────────────────────────────
    with tab_account:
        if not other_users:
            st.info("No other users to manage.", icon=":material/info:")
        else:
            sel_col3, _ = st.columns([2, 3], gap="small")
            sel_acc_user = sel_col3.selectbox(
                "Select user",
                [u["username"] for u in other_users],
                key="sel_acc_user",
                label_visibility="collapsed",
            )
            sel_a = next((u for u in other_users if u["username"] == sel_acc_user), None)
            if sel_a:
                status_label = "Active" if sel_a["is_active"] else "Inactive"
                status_color = "#27ae60" if sel_a["is_active"] else "#e74c3c"
                st.markdown(
                    f"Account status: <span style='color:{status_color};font-weight:700;'>"
                    f"{status_label}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown("")

                tog_col, del_col = st.columns(2, gap="small")
                with tog_col:
                    if sel_a["is_active"]:
                        if st.button(
                            "Disable Account",
                            icon=":material/block:",
                            use_container_width=True,
                            key="toggle_active",
                        ):
                            ok, msg = toggle_user_active(sel_a["id"], False)
                            st.success(msg, icon=":material/check_circle:") if ok else st.error(msg)
                            if ok:
                                st.rerun()
                    else:
                        if st.button(
                            "Enable Account",
                            icon=":material/check_circle:",
                            type="primary",
                            use_container_width=True,
                            key="toggle_active",
                        ):
                            ok, msg = toggle_user_active(sel_a["id"], True)
                            st.success(msg, icon=":material/check_circle:") if ok else st.error(msg)
                            if ok:
                                st.rerun()

                with del_col:
                    if st.button(
                        "Delete User",
                        icon=":material/delete:",
                        use_container_width=True,
                        key="delete_user",
                    ):
                        ok, msg = delete_user(sel_a["id"])
                        st.success(msg, icon=":material/check_circle:") if ok else st.error(msg)
                        if ok:
                            st.rerun()
