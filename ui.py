import pandas as pd
import streamlit as st
from io import BytesIO

from config import HEADERS_44
from excel_utils import apply_excel_styles
from handlers import is_valid_ticket


PAGE_CSS = """
<style>
/* Header gradient */
[data-testid="stHeader"] {
    background: linear-gradient(90deg, #1F4E79, #2E86C1);
}

/* Primary buttons */
div.stButton > button[kind="primary"] {
    background: #1F4E79;
    width: 100%;
}

/* Big upload drop zone */
[data-testid="stFileUploaderDropzone"] {
    border: 2.5px dashed #2E86C1 !important;
    border-radius: 16px !important;
    background: linear-gradient(145deg, #eaf4ff, #f5f9ff) !important;
    padding: 40px 20px !important;
    min-height: 180px !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span {
    font-size: 15px !important;
    color: #1F4E79 !important;
    font-weight: 600 !important;
}

/* ── Move top-level nav tab-list into the header bar ──────────────────────── */

/* 1. Lift the outer tab-list into the fixed header */
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] {
    position: fixed !important;
    top: 0 !important;
    right: 80px !important;
    height: 60px !important;
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
    z-index: 999999 !important;
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* 2. Style the nav tab buttons — white pill on gradient background */
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] button[data-baseweb="tab"] {
    height: 32px !important;
    padding: 0 18px !important;
    border-radius: 20px !important;
    background: rgba(255,255,255,0.15) !important;
    color: rgba(255,255,255,0.88) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    border: none !important;
    outline: none !important;
    transition: background 0.15s, color 0.15s !important;
}
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] button[data-baseweb="tab"]:hover {
    background: rgba(255,255,255,0.28) !important;
    color: #fff !important;
}
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] button[aria-selected="true"] {
    background: rgba(255,255,255,0.38) !important;
    color: #fff !important;
    font-weight: 700 !important;
}

/* 3. Hide the underline/highlight bar for the nav tabs */
div[data-testid="stTabs"] > div[data-baseweb="tab-border"],
div[data-testid="stTabs"] > div[data-baseweb="tab-highlight"] {
    display: none !important;
}

/* 4. Restore nested tab-lists (e.g. tabs inside Database page) to normal */
div[data-baseweb="tab-panel"] div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
    position: static !important;
    top: unset !important;
    right: unset !important;
    height: auto !important;
    z-index: 1 !important;
    background: transparent !important;
    border-bottom: 2px solid #eee !important;
    gap: 0 !important;
}
div[data-baseweb="tab-panel"] div[data-testid="stTabs"] button[data-baseweb="tab"] {
    height: auto !important;
    padding: 10px 20px !important;
    border-radius: 0 !important;
    background: transparent !important;
    color: #444 !important;
    font-size: 14px !important;
    font-weight: 400 !important;
}
div[data-baseweb="tab-panel"] div[data-testid="stTabs"] button[aria-selected="true"] {
    background: transparent !important;
    color: #1F4E79 !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #1F4E79 !important;
}
div[data-baseweb="tab-panel"] div[data-testid="stTabs"] div[data-baseweb="tab-border"],
div[data-baseweb="tab-panel"] div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {
    display: none !important;
}
</style>
"""


# ── Sidebar: upload form ──────────────────────────────────────────────────────
def render_upload_sidebar() -> tuple:
    """Big uploader + buttons. Returns (uploaded_files, run_clicked)."""
    with st.sidebar:
        st.markdown("## 📂 Upload Files")
        st.markdown(
            "<p style='font-size:12px;color:#888;margin-top:-10px;'>"
            "Supported: .txt · .dat · .log</p>",
            unsafe_allow_html=True,
        )

        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0

        uploaded_files = st.file_uploader(
            "Drop Sabre files here",
            accept_multiple_files=True,
            type=["txt", "dat", "log"],
            key=f"uploader_{st.session_state.uploader_key}",
            label_visibility="collapsed",
        )

        if uploaded_files:
            st.success(f"✅ **{len(uploaded_files)}** file(s) selected")
            with st.container(height=200):
                for f in uploaded_files:
                    size_kb = round(len(f.getvalue()) / 1024, 1)
                    st.caption(f"📄 **{f.name}** — `{size_kb} KB`")

        st.markdown("")

        run = st.button(
            "🚀 Process Files",
            type="primary",
            use_container_width=True,
            disabled=not bool(uploaded_files),
        )
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.uploader_key += 1
            st.session_state.pop("df", None)
            st.rerun()

    return uploaded_files or [], run


# ── Main panel: results ───────────────────────────────────────────────────────
def render_results(df: pd.DataFrame, db_available: bool = False, save_fn=None) -> None:

    ticket_rows = df[df.index.map(is_valid_ticket)]
    pnr_rows    = df[~df.index.map(is_valid_ticket)]
    filled      = df.notna().sum().sum()
    total_cells = len(df) * len(df.columns)
    pct         = filled / total_cells * 100 if total_cells > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Rows",     len(df))
    m2.metric("Ticket Rows",    len(ticket_rows))
    m3.metric("PNR-Only Rows",  len(pnr_rows))
    m4.metric("Field Coverage", f"{pct:.0f}%")

    st.markdown("---")
    st.markdown("### Mapped Data")
    st.dataframe(df, use_container_width=True, height=520)

    with st.expander("📊 Column coverage"):
        cov = [
            {
                "Column":   h,
                "Filled":   df[h].notna().sum(),
                "Total":    len(df),
                "Coverage": (
                    f"{df[h].notna().sum() / len(df) * 100:.0f}%"
                    if len(df) > 0 else "0%"
                ),
            }
            for h in HEADERS_44
        ]
        st.dataframe(pd.DataFrame(cov), use_container_width=True, hide_index=True)

    st.markdown("---")

    dl_col, db_col = st.columns([1, 2] if (db_available and save_fn) else [1, 3])

    with dl_col:
        st.markdown("#### 📥 Download")
        raw = BytesIO()
        df.to_excel(raw, index=False, engine="openpyxl")
        styled_xl = apply_excel_styles(raw, df)
        st.download_button(
            "📥 Download Excel",
            styled_xl.getvalue(),
            f"Sabre_Report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )

    if db_available and save_fn:
        with db_col:
            st.markdown("#### 🗄️ Save to SQL Server")
            sa, sb, sc = st.columns([2, 2, 1])
            with sa:
                table_name  = st.text_input("Table name", value="SabreReport")
            with sb:
                batch_label = st.text_input(
                    "Batch label",
                    value=pd.Timestamp.now().strftime("%Y-%m-%d"),
                    help="Tag added to every row to identify this import.",
                )
            with sc:
                write_mode = st.selectbox("If exists", ["append", "replace"])
            if st.button("💾 Save to SQL Server", use_container_width=True):
                with st.spinner("Saving..."):
                    ok, msg = save_fn(
                        df, table=table_name,
                        if_exists=write_mode, batch_label=batch_label,
                    )
                st.success(msg) if ok else st.error(msg)
