"""Session auth helpers — backed by the users table via data.db."""

from core.crypto import verify_pw


def check_credentials(username: str, password: str) -> tuple[bool, str]:
    """
    Verify username/password against the users table.
    Returns (True, role) on success, (False, "") on failure.
    """
    if not username:
        return False, ""
    try:
        from data.db import get_user
        user = get_user(username.strip())
        if user and user["is_active"] and verify_pw(password, user["password_hash"]):
            return True, user["role"]
    except Exception:
        pass
    return False, ""


def is_authenticated() -> bool:
    import streamlit as st
    return st.session_state.get("_auth", False)


def do_login(username: str, role: str) -> None:
    import streamlit as st
    st.session_state["_auth"]     = True
    st.session_state["_username"] = username.strip()
    st.session_state["_role"]     = role
    try:
        from data.db import update_last_login, log_event
        update_last_login(username.strip())
        log_event("login", username.strip(), f"role={role}")
    except Exception:
        pass


def do_logout() -> None:
    import streamlit as st
    username = st.session_state.get("_username", "")
    try:
        from data.db import log_event
        log_event("logout", username, "")
    except Exception:
        pass
    st.session_state.clear()
