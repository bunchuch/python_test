import streamlit as st

from views import page_processor, page_guide, page_database, page_query
from views.page_login import render as render_login
from ui import PAGE_CSS, render_navbar, render_upload_sidebar
from core.auth import is_authenticated

try:
    from data.db import save_to_db, test_connection, query_data, get_available_years
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    save_to_db = test_connection = query_data = get_available_years = None

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

# ── Auth gate — show login page and stop if not signed in ─────────────────────
if not is_authenticated():
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

# Sidebar uploader is only needed on the Processor page
if page == "processor":
    uploaded_files, run = render_upload_sidebar()
else:
    uploaded_files, run = [], False

if page == "guide":
    page_guide.render()
elif page == "database":
    page_database.render(DB_AVAILABLE, test_connection)
elif page == "query":
    page_query.render(DB_AVAILABLE, query_data, get_available_years)
else:
    page_processor.render(uploaded_files, run, DB_AVAILABLE, save_to_db)
