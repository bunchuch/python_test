"""Session auth helpers — backed by the users table via data.db.

Session persistence across browser refreshes:
  - On login  : token written to browser localStorage via the local_storage component.
  - On refresh: ls_get() returns None on the first render (component not yet ready),
                which signals "still loading" to main.py.  On the automatic second
                render the actual token is returned and the session is restored.
  - On logout : token removed from the server store and from localStorage.
"""

from core.crypto import verify_pw

_LS_KEY = "sabre_sid"


# ── Credential check ──────────────────────────────────────────────────────────

def check_credentials(username: str, password: str) -> tuple[bool, str]:
    """Returns (True, role) on success, (False, '') on failure."""
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


# ── Auth state ────────────────────────────────────────────────────────────────

def is_authenticated() -> bool | None:
    """
    Returns:
        True  – valid session exists
        False – no valid session
        None  – localStorage not yet read (first render); caller should show a
                loading screen and wait for the automatic rerun
    """
    import streamlit as st

    # Fast path: session already live in this Python process
    if st.session_state.get("_auth"):
        return True

    # Read token from browser localStorage (None = component not ready yet)
    from core.local_storage import ls_get
    token = ls_get(_LS_KEY)

    if token is None:
        return None  # still loading

    if token:
        from core.session_store import validate_session
        entry = validate_session(token)
        if entry:
            st.session_state["_auth"]     = True
            st.session_state["_username"] = entry["username"]
            st.session_state["_role"]     = entry["role"]
            st.session_state["_sid"]      = token
            return True
        # Token expired or server restarted — clear stale entry
        from core.local_storage import ls_del
        ls_del(_LS_KEY)

    return False


# ── Login / logout ────────────────────────────────────────────────────────────

def do_login(username: str, role: str) -> None:
    import streamlit as st
    from core.session_store import create_session
    from core.local_storage import ls_set

    token = create_session(username.strip(), role)
    st.session_state["_auth"]     = True
    st.session_state["_username"] = username.strip()
    st.session_state["_role"]     = role
    st.session_state["_sid"]      = token
    ls_set(_LS_KEY, token)

    try:
        from data.db import update_last_login, log_event
        update_last_login(username.strip())
        log_event("login", username.strip(), f"role={role}")
    except Exception:
        pass


def do_logout() -> None:
    import streamlit as st
    from core.session_store import delete_session
    from core.local_storage import ls_del

    token    = st.session_state.get("_sid", "")
    username = st.session_state.get("_username", "")

    if token:
        delete_session(token)

    ls_del(_LS_KEY)

    try:
        from data.db import log_event
        log_event("logout", username, "")
    except Exception:
        pass

    st.session_state.clear()
