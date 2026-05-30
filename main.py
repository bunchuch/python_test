import streamlit as st

import page_processor
import page_guide
import page_database
from ui import PAGE_CSS, render_upload_sidebar

try:
    from db import save_to_db, test_connection
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    save_to_db = test_connection = None

st.set_page_config(page_title="Sabre Mapper", page_icon="✈️", layout="wide")
st.markdown(PAGE_CSS, unsafe_allow_html=True)

uploaded_files, run = render_upload_sidebar()

tab1, tab2, tab3 = st.tabs(["✈️  Processor", "📖  Guide", "🗄️  Database"])

with tab1:
    page_processor.render(uploaded_files, run, DB_AVAILABLE, save_to_db)

with tab2:
    page_guide.render()

with tab3:
    page_database.render(DB_AVAILABLE, test_connection)
