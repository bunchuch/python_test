import streamlit as st

from views import page_processor, page_guide, page_database, page_query, page_users
from views.page_login import render as render_login
from ui import PAGE_CSS, render_navbar
from core.auth import is_authenticated

try:
    from data.db import (
        save_to_db, test_connection,
        query_data, get_available_years,
    )
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    save_to_db = test_connection = None
    query_data = get_available_years = None

st.set_page_config(page_title="Sabre Mapper", page_icon="✈️", layout="wide")
st.markdown(PAGE_CSS, unsafe_allow_html=True)

# ── Bootstrap DB schema (idempotent — safe to run on every startup) ───────────
# Must run BEFORE the auth gate so the users table exists when the login form
# calls check_credentials().
if DB_AVAILABLE:
    try:
        from data.db import ensure_schema
        ensure_schema()
    except Exception:
        pass

# ── Auth gate ─────────────────────────────────────────────────────────────────
# is_authenticated() returns:
#   True  – valid session
#   False – not logged in
#   None  – localStorage component not yet ready (first render after refresh)
_auth = is_authenticated()

if _auth is None:
    # Component is loading localStorage — show a blank screen and wait for the
    # automatic rerun that fires once the component returns the stored token.
    st.markdown(
        "<div style='height:100vh;display:flex;align-items:center;"
        "justify-content:center;color:#aaa;font-size:14px;'>Loading…</div>",
        unsafe_allow_html=True,
    )
    st.stop()

if not _auth:
    render_login()
    st.stop()

# ── Mobile blocker ────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class='mobile-block'>
        <div style='font-size:56px;margin-bottom:16px;'>🖥️</div>
        <div style='font-size:22px;font-weight:800;color:#1F4E79;margin-bottom:10px;'>
            Desktop Only
        </div>
        <div style='font-size:14px;color:#64748B;max-width:280px;line-height:1.6;'>
            This application is designed for desktop use.<br>
            Please open it on a <strong>laptop or desktop computer</strong>
            for the full experience.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Startup spinner — runs once per session after login ───────────────────────
if "_app_ready" not in st.session_state:
    with st.spinner("Starting Sabre Master Processor…"):
        if DB_AVAILABLE and test_connection:
            try:
                test_connection()
            except Exception:
                pass
        st.session_state["_app_ready"] = True
    st.rerun()

# ── Page routing ──────────────────────────────────────────────────────────────
from core.rbac import allowed_nav, default_page

if "page" not in st.session_state:
    st.session_state["page"] = default_page()

page = st.session_state["page"]

# Page-access guard — redirect to the role's default page if the stored key is
# no longer in the allowed set (e.g. after a role change or direct URL manipulation).
allowed_keys = {p[0] for p in allowed_nav()}
if page not in allowed_keys:
    st.session_state["page"] = default_page()
    page = st.session_state["page"]
    st.rerun()

render_navbar(page)

if page == "guide":
    page_guide.render()
elif page == "database":
    page_database.render(DB_AVAILABLE, test_connection)
elif page == "query":
    page_query.render(DB_AVAILABLE, query_data, get_available_years)
elif page == "users":
    page_users.render()
else:
    page_processor.render(DB_AVAILABLE, save_to_db)
