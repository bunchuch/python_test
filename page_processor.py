import streamlit as st
from processor import process_data
from ui import render_results


def render(uploaded_files: list, run: bool, db_available: bool, save_fn) -> None:
    st.title("✈️ Sabre Master Processor")
    st.markdown("Upload Sabre `.txt` files → auto-map to **44 columns** → download Excel or save to SQL Server.")

    if run and uploaded_files:
        with st.spinner("Processing files..."):
            st.session_state["df"] = process_data(uploaded_files)
        st.success(f"Done — **{len(st.session_state['df']):,}** rows mapped.")

    if "df" in st.session_state:
        render_results(
            df=st.session_state["df"],
            db_available=db_available,
            save_fn=save_fn,
        )
    else:
        st.info("Upload one or more Sabre files on the left, then click **Process Files**.")
