import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from io import BytesIO

from config import HEADERS_44
from excel_utils import apply_excel_styles
from handlers import is_valid_ticket

# Injects webkitdirectory onto the LAST file input rendered in the page.
# Runs once on load, then again on every DOM mutation so it survives Streamlit rerenders.
_FOLDER_INJECT = """
<script>
(function () {
  function patch() {
    try {
      var inputs = window.parent.document.querySelectorAll('input[type="file"]');
      if (inputs.length < 1) return;
      var last = inputs[inputs.length - 1];
      if (!last.hasAttribute('webkitdirectory')) {
        last.setAttribute('webkitdirectory', '');
        last.setAttribute('multiple', '');
      }
    } catch (e) {}
  }
  patch();
  if (!window.parent.__folderPatchObserver) {
    window.parent.__folderPatchObserver = new MutationObserver(patch);
    window.parent.__folderPatchObserver.observe(
      window.parent.document.body,
      { childList: true, subtree: true }
    );
  }
})();
</script>
"""


PAGE_CSS = """
<style>
/* White header bar */
[data-testid="stHeader"] {
    background: #ffffff !important;
    border-bottom: 1px solid #e8eaed;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

/* Nav buttons — shared base */
div[data-testid="stHorizontalBlock"] div.stButton button {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    white-space: nowrap !important;
    font-size: 13px !important;
    height: 34px !important;
    padding: 6px 10px !important;
}

/* Inactive */
div[data-testid="stHorizontalBlock"] div.stButton button[kind="secondary"] {
    color: #666 !important;
    font-weight: 500 !important;
}
div[data-testid="stHorizontalBlock"] div.stButton button[kind="secondary"]:hover {
    color: #1F4E79 !important;
}

/* Active — text highlight only, no fill */
div[data-testid="stHorizontalBlock"] div.stButton button[kind="primary"] {
    color: #1F4E79 !important;
    font-weight: 700 !important;
    border-bottom: 2px solid #1F4E79 !important;
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

/* Nested tabs inside pages (Database config tabs, etc.) */
div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
    border-bottom: 2px solid #eee;
}
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    color: #1F4E79 !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #1F4E79 !important;
}

/* ── Toolbar action buttons: Excel download + Save popover ─────────────────── */
/* Force horizontal layout (icon left, text right), 12 px */
[data-testid="stDownloadButton"] button,
[data-testid="stPopover"] > div > button {
    display: inline-flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 5px !important;
    height: 30px !important;
    padding: 0 10px !important;
    white-space: nowrap !important;
    font-size: 12px !important;
    border-radius: 6px !important;
}
[data-testid="stDownloadButton"] button > div,
[data-testid="stPopover"] > div > button > div {
    display: inline-flex !important;
    flex-direction: row !important;
    align-items: center !important;
    gap: 5px !important;
}
[data-testid="stDownloadButton"] button p,
[data-testid="stPopover"] > div > button p {
    font-size: 12px !important;
    margin: 0 !important;
    line-height: 1 !important;
    white-space: nowrap !important;
}
</style>
"""


# ── Navbar ─────────────────────────────────────────────────────────────────────
def render_navbar(active_page: str) -> None:
    nav_pages = [
        ("processor", "✈️  Processor"),
        ("query",     "🔍  Query"),
        ("guide",     "📖  Guide"),
        ("database",  "🗄️  Database"),
    ]
    # Columns: one per nav item + spacer on the right
    cols = st.columns([1.2, 1.0, 1.0, 1.2, 5.6])
    for i, (key, label) in enumerate(nav_pages):
        with cols[i]:
            btn_type = "primary" if key == active_page else "secondary"
            if st.button(label, key=f"nav_{key}", use_container_width=True, type=btn_type):
                st.session_state["page"] = key
                st.rerun()
    st.markdown(
        "<hr style='margin:4px 0 20px 0;border:none;border-top:1px solid #e8eaed;'>",
        unsafe_allow_html=True,
    )


# ── Sidebar: upload form ───────────────────────────────────────────────────────
def render_upload_sidebar() -> tuple:
    """Two uploaders (files + folder). Returns (all_unique_files, run_clicked)."""
    with st.sidebar:
        st.markdown("## 📂 Upload Files")
        st.markdown(
            "<p style='font-size:12px;color:#888;margin-top:-10px;'>"
            "Supported: .txt · .dat · .log</p>",
            unsafe_allow_html=True,
        )

        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0

        # ── Mode selector ─────────────────────────────────────────────────────
        mode = st.radio(
            "Import mode",
            ["📄 Files", "📁 Folder"],
            horizontal=True,
            label_visibility="collapsed",
        )

        # Key encodes both the reset counter and the mode so switching clears
        # any previously uploaded content automatically.
        k = f"{st.session_state.uploader_key}_{mode}"

        # ── Single uploader, behaviour depends on mode ─────────────────────────
        uploaded = st.file_uploader(
            "Drop here",
            accept_multiple_files=True,
            type=["txt", "dat", "log"],
            key=f"uploader_{k}",
            label_visibility="collapsed",
        )

        if mode == "📁 Folder":
            # Inject webkitdirectory onto the last file input after render
            components.html(_FOLDER_INJECT, height=0)

        # ── File list ─────────────────────────────────────────────────────────
        all_files = uploaded or []
        if all_files:
            st.success(f"✅ **{len(all_files)}** file(s) ready")
            with st.container(height=180):
                for f in all_files:
                    size_kb = round(len(f.getvalue()) / 1024, 1)
                    st.caption(f"📄 **{f.name}** — `{size_kb} KB`")

        st.markdown("")

        run = st.button(
            "🚀 Process Files",
            type="primary",
            use_container_width=True,
            disabled=not bool(all_files),
        )
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.uploader_key += 1
            st.session_state.pop("df", None)
            st.rerun()

    return all_files, run


# ── Main panel: results ────────────────────────────────────────────────────────
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

    # ── Prepare Excel once so the download button works in the toolbar ─────────
    raw = BytesIO()
    df.to_excel(raw, index=False, engine="openpyxl")
    styled_xl = apply_excel_styles(raw, df)
    fname = f"Sabre_Report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx"

    # ── Compact action toolbar above the table ─────────────────────────────────
    title_col, spacer_col, dl_col, db_col = st.columns([5, 1.5, 1.2, 1.2])

    with title_col:
        st.markdown("### Mapped Data")

    with dl_col:
        st.download_button(
            "📥 Excel",
            styled_xl.getvalue(),
            fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="Download as formatted Excel file",
        )

    if db_available and save_fn:
        with db_col:
            with st.popover("💾 Save", use_container_width=True):
                st.markdown("**Save to SQL Server**")
                table_name  = st.text_input("Table", value="SabreReport")
                batch_label = st.text_input(
                    "Batch label",
                    value=pd.Timestamp.now().strftime("%Y-%m-%d"),
                    help="Tag added to every row to identify this import.",
                )
                write_mode = st.selectbox("If exists", ["append", "replace"])
                if st.button("💾 Save", type="primary", use_container_width=True):
                    with st.spinner("Saving…"):
                        ok, msg = save_fn(
                            df, table=table_name,
                            if_exists=write_mode, batch_label=batch_label,
                        )
                    st.success(msg) if ok else st.error(msg)

    # ── Table ──────────────────────────────────────────────────────────────────
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
