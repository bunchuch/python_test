import streamlit as st

from views import page_processor, page_guide, page_database, page_query
from ui import PAGE_CSS, render_navbar, render_upload_sidebar

try:
    from data.db import save_to_db, test_connection, query_data, get_available_years
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    save_to_db = test_connection = query_data = get_available_years = None

st.set_page_config(page_title="Sabre Mapper", page_icon="✈️", layout="wide")
st.markdown(PAGE_CSS, unsafe_allow_html=True)
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

if "page" not in st.session_state:
    st.session_state["page"] = "processor"
page = st.session_state["page"]

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
