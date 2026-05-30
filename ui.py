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
/* Page titles — slightly smaller than Streamlit default */
h1 {
    font-size: 20px !important;
}

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
    font-size: 12px !important;
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
    font-size: 12px;
}

/* Big upload drop zone */
[data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed #2E86C1 !important;
    border-radius: 10px !important;
    # background: linear-gradient(145deg, #eaf4ff, #f5f9ff) !important;
    padding: 40px 20px !important;
    min-height: 180px !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span {
    font-size: 12px !important;
    color: #1F4E79 !important;
    font-weight: 600 !important;
}

/* Hide the Upload browse button — dropzone area stays clickable */
[data-testid="stFileUploaderDropzone"] button {
    display: none !important;
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
        ("processor", "Processor", ":material/flight:"),
        ("query",     "Query",     ":material/search:"),
        ("guide",     "Guide",     ":material/menu_book:"),
        ("database",  "Database",  ":material/storage:"),
    ]
    cols = st.columns([1.2, 1.0, 1.0, 1.2, 5.6])
    for i, (key, label, icon) in enumerate(nav_pages):
        with cols[i]:
            btn_type = "primary" if key == active_page else "secondary"
            if st.button(label, icon=icon, key=f"nav_{key}",
                         use_container_width=True, type=btn_type):
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
        st.image("assets/K6.png", use_container_width=True)
        st.markdown("## :material/folder: Upload Files")
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
            [":material/description:  Files", ":material/folder_open:  Folder"],
            horizontal=True,
            label_visibility="collapsed",
        )

        k = f"{st.session_state.uploader_key}_{mode}"

        # ── Single uploader, behaviour depends on mode ─────────────────────────
        uploaded = st.file_uploader(
            "Drop here",
            accept_multiple_files=True,
            type=["txt", "dat", "log"],
            key=f"uploader_{k}",
            label_visibility="collapsed",
        )

        if "Folder" in mode:
            components.html(_FOLDER_INJECT, height=0)

        # ── File list ─────────────────────────────────────────────────────────
        all_files = uploaded or []
        if all_files:
            st.success(f"**{len(all_files)}** file(s) ready", icon=":material/check_circle:")
            with st.container(height=180):
                for f in all_files:
                    size_kb = round(len(f.getvalue()) / 1024, 1)
                    st.caption(f":material/description: **{f.name}** — `{size_kb} KB`")

        st.markdown("")

        busy = st.session_state.get("busy", False)

        run = st.button(
            "Process Files",
            icon=":material/rocket_launch:",
            type="primary",
            use_container_width=True,
            disabled=busy or not bool(all_files),
        )
        if st.button("Clear All", icon=":material/delete:",
                     use_container_width=True, disabled=busy):
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
    busy = st.session_state.get("busy", False)
    title_col, spacer_col, dl_col, db_col = st.columns([5, 1.5, 1.2, 1.2])

    with title_col:
        st.markdown("### Mapped Data")

    with dl_col:
        st.download_button(
            "Excel",
            styled_xl.getvalue(),
            fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            icon=":material/download:",
            use_container_width=True,
            help="Download as formatted Excel file",
            disabled=busy,
        )

    if db_available and save_fn:
        with db_col:
            if busy:
                st.button("Save", icon=":material/save:",
                          use_container_width=True, disabled=True)
            else:
                with st.popover(":material/save: Save", use_container_width=True):
                    st.markdown("**Save to database**")
                    table_name  = st.text_input("Table", value="SabreReport")
                    batch_label = st.text_input(
                        "Batch label",
                        value=pd.Timestamp.now().strftime("%Y-%m-%d"),
                        help="Tag added to every row to identify this import.",
                    )
                    write_mode = st.selectbox("If exists", ["append", "replace"])
                    if st.button("Save", icon=":material/save:",
                                 type="primary", use_container_width=True):
                        save_fn(
                            df, table=table_name,
                            if_exists=write_mode, batch_label=batch_label,
                        )

    # ── Pagination ─────────────────────────────────────────────────────────────
    _PAGE_SIZES = [50, 100, 200, 500]
    total_rows  = len(df)

    # Initialise state
    if "tbl_page" not in st.session_state:
        st.session_state["tbl_page"] = 0
    if "tbl_size" not in st.session_state:
        st.session_state["tbl_size"] = 100

    # Reset to page 0 whenever the dataset changes
    df_sig = (total_rows, list(df.columns))
    if st.session_state.get("_tbl_sig") != str(df_sig):
        st.session_state["tbl_page"] = 0
        st.session_state["_tbl_sig"] = str(df_sig)

    page_size   = st.session_state["tbl_size"]
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page        = min(st.session_state["tbl_page"], total_pages - 1)
    st.session_state["tbl_page"] = page

    start_idx = page * page_size
    end_idx   = min(start_idx + page_size, total_rows)
    page_df   = df.iloc[start_idx:end_idx]

    # Controls bar
    sz_col, prev_col, info_col, next_col, rows_col = st.columns([1.6, 0.55, 2.2, 0.55, 2.2])

    with sz_col:
        def _reset_page():
            st.session_state["tbl_page"] = 0
        st.selectbox(
            "Rows/page",
            _PAGE_SIZES,
            index=_PAGE_SIZES.index(page_size) if page_size in _PAGE_SIZES else 1,
            key="tbl_size",
            on_change=_reset_page,
            label_visibility="collapsed",
        )

    with prev_col:
        if st.button("", icon=":material/chevron_left:",
                     use_container_width=True, disabled=(page == 0)):
            st.session_state["tbl_page"] -= 1
            st.rerun()

    with info_col:
        st.markdown(
            f"<p style='text-align:center;margin:0;padding-top:7px;"
            f"font-size:13px;color:#444;'>"
            f"Page <b>{page + 1}</b> / <b>{total_pages}</b></p>",
            unsafe_allow_html=True,
        )

    with next_col:
        if st.button("", icon=":material/chevron_right:",
                     use_container_width=True, disabled=(page >= total_pages - 1)):
            st.session_state["tbl_page"] += 1
            st.rerun()

    with rows_col:
        st.markdown(
            f"<p style='text-align:right;margin:0;padding-top:7px;"
            f"font-size:12px;color:#888;'>"
            f"Rows {start_idx + 1:,} – {end_idx:,} of {total_rows:,}</p>",
            unsafe_allow_html=True,
        )

    # ── Table (current page only) ───────────────────────────────────────────────
    st.dataframe(page_df, use_container_width=True, height=520)

    with st.expander("Column coverage", icon=":material/bar_chart:"):
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
