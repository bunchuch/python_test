import streamlit as st

import page_processor
import page_guide
import page_database
import page_query
from ui import PAGE_CSS, render_navbar, render_upload_sidebar

try:
    from db import save_to_db, test_connection, query_data, get_available_years
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    save_to_db = test_connection = query_data = get_available_years = None

st.set_page_config(page_title="Sabre Mapper", page_icon="✈️", layout="wide")
st.markdown(PAGE_CSS, unsafe_allow_html=True)

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
