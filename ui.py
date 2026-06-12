import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from io import BytesIO

from core.config import HEADERS_44
from data.excel_utils import apply_excel_styles
from core.handlers import is_valid_ticket

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
/* ── Mobile blocker ────────────────────────────────────────────────────────── */
.mobile-block { display: none; }
@media (max-width: 900px) {
    .mobile-block {
        display: flex !important;
        position: fixed; inset: 0; z-index: 999999;
        background: #ffffff; flex-direction: column;
        align-items: center; justify-content: center;
        text-align: center; padding: 32px 24px; pointer-events: all;
    }
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    section[data-testid="stSidebar"] { visibility: hidden !important; }
}

/* ── Global ────────────────────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"],
[data-testid="stMain"] { background: #ffffff !important; }

/* Hide Streamlit's top header bar — nav lives in the sidebar now */
[data-testid="stHeader"] { display: none !important; }

/* ── Page headings ─────────────────────────────────────────────────────────── */
h1 { font-size: clamp(18px, 1.5vw, 24px) !important; color: #1a2535 !important; }
h2 { font-size: clamp(15px, 1.2vw, 20px) !important; }
h3 { font-size: clamp(13px, 1.1vw, 17px) !important; }

/* ── Sidebar — gray panel ──────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #f0f2f5 !important;
    border-right: 1px solid #e2e5ea !important;
    box-shadow: 2px 0 12px rgba(0,0,0,.04) !important;
    min-width: 235px !important;
    max-width: 265px !important;
}
[data-testid="stSidebarContent"] { padding: 20px 14px !important; }

/* ── Sidebar buttons — nav items ───────────────────────────────────────────── */
section[data-testid="stSidebar"] .stButton button {
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 10px !important;
    border: none !important;
    box-shadow: none !important;
    height: 44px !important;
    padding: 0 16px !important;
    font-size: 14px !important;
    width: 100% !important;
    transition: background .15s, color .15s !important;
}

/* Inactive nav item */
section[data-testid="stSidebar"] .stButton button[kind="secondary"] {
    background: transparent !important;
    color: #6b7280 !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {
    background: #e4e7ec !important;
    color: #1a2535 !important;
}

/* Active nav item */
section[data-testid="stSidebar"] .stButton button[kind="primary"] {
    background: #eef2ff !important;
    color: #1a6fff !important;
    font-weight: 700 !important;
}
section[data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
    background: #e0e8ff !important;
}

/* ── Upload drop zone ──────────────────────────────────────────────────────── */
[data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed #1a6fff !important;
    border-radius: 10px !important;
    background: #f8faff !important;
    padding: clamp(16px, 2vh, 32px) 16px !important;
    min-height: clamp(100px, 12vh, 160px) !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span {
    font-size: clamp(11px, 0.9vw, 13px) !important;
    color: #1a6fff !important;
    font-weight: 600 !important;
}
[data-testid="stFileUploaderDropzone"] button { display: none !important; }

/* ── Main content area ─────────────────────────────────────────────────────── */
[data-testid="stAppViewBlockContainer"] {
    padding: 6px clamp(16px, 2.5vw, 36px) 24px !important;
    max-width: 100% !important;
}

/* ── Gradient metric cards ─────────────────────────────────────────────────── */
.fs-metrics { display: flex; gap: 14px; margin-bottom: 22px; flex-wrap: wrap; }
.fs-card {
    flex: 1; min-width: 140px;
    background: linear-gradient(135deg, #1a6fff 0%, #52a5ff 100%);
    border-radius: 14px; padding: 20px 22px; color: #fff;
}
.fs-card .fs-lbl {
    font-size: 11px; font-weight: 600; letter-spacing: .6px;
    text-transform: uppercase; opacity: .82; margin-bottom: 8px;
}
.fs-card .fs-val {
    font-size: 30px; font-weight: 800; line-height: 1;
}
.fs-card .fs-sub { font-size: 11px; opacity: .7; margin-top: 5px; }

/* ── Segmented control (Filter by buttons) ─────────────────────────────────── */
[data-testid="stSegmentedControl"] {
    background: #f5f7fa !important;
    border-radius: 10px !important;
    padding: 3px !important;
    gap: 2px !important;
}
[data-testid="stSegmentedControl"] label {
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 18px !important;
    color: #6b7280 !important;
    transition: all .15s !important;
}
[data-testid="stSegmentedControl"] input:checked + div,
[data-testid="stSegmentedControl"] [aria-checked="true"] {
    background: #ffffff !important;
    color: #1a2535 !important;
    font-weight: 700 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.12) !important;
}

/* ── Tabs ──────────────────────────────────────────────────────────────────── */
div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
    border-bottom: 2px solid #eaedf3;
}
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    color: #1a6fff !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #1a6fff !important;
}

/* ── Toolbar buttons ────────────────────────────────────────────────────────── */
[data-testid="stDownloadButton"] button,
[data-testid="stPopover"] > div > button {
    display: inline-flex !important; flex-direction: row !important;
    align-items: center !important; justify-content: center !important;
    gap: 5px !important; height: 34px !important; padding: 0 14px !important;
    white-space: nowrap !important; font-size: 13px !important; border-radius: 8px !important;
}
[data-testid="stDownloadButton"] button > div,
[data-testid="stPopover"] > div > button > div {
    display: inline-flex !important; flex-direction: row !important;
    align-items: center !important; gap: 5px !important;
}
[data-testid="stDownloadButton"] button p,
[data-testid="stPopover"] > div > button p {
    font-size: 13px !important; margin: 0 !important;
    line-height: 1 !important; white-space: nowrap !important;
}

/* ── Primary buttons in main content — Forsight blue gradient ──────────────── */
[data-testid="stMain"] .stButton button[kind="primary"] {
    background: linear-gradient(135deg, #1a6fff 0%, #4a9fff 100%) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    box-shadow: 0 3px 14px rgba(26,111,255,.22) !important;
    transition: box-shadow .2s !important;
}
[data-testid="stMain"] .stButton button[kind="primary"]:hover {
    box-shadow: 0 6px 22px rgba(26,111,255,.36) !important;
}
[data-testid="stMain"] .stButton button[kind="primary"]:disabled {
    background: #c4d4ee !important;
    box-shadow: none !important;
}

/* ── Responsive ─────────────────────────────────────────────────────────────── */
@media (max-width: 1280px) {
    section[data-testid="stSidebar"] { min-width: 215px !important; max-width: 245px !important; }
    [data-testid="stAppViewBlockContainer"] { padding: 6px 16px 20px !important; }
}
@media (min-width: 1920px) {
    section[data-testid="stSidebar"] { min-width: 260px !important; max-width: 300px !important; }
    h1 { font-size: 26px !important; }
    h2 { font-size: 22px !important; }
    h3 { font-size: 19px !important; }
}
</style>
"""


# ── Navbar (sidebar) ───────────────────────────────────────────────────────────
def render_navbar(active_page: str) -> None:
    from core.rbac import allowed_nav, current_role, ROLE_BADGE
    from core.auth import do_logout

    nav          = allowed_nav()
    role         = current_role()
    badge_label, badge_color = ROLE_BADGE.get(role, ("User", "#2E86C1"))
    username     = st.session_state.get("_username", "")

    with st.sidebar:
        # Logo
        try:
            st.image("assets/K6.png", use_container_width=True)
        except Exception:
            st.markdown(
                "<div style='font-size:20px;font-weight:800;color:#1a2535;"
                "padding:6px 2px 10px;'>✈ Sabre Mapper</div>",
                unsafe_allow_html=True,
            )

        st.divider()

        # Vertical nav items
        for key, label, icon in nav:
            btn_type = "primary" if key == active_page else "secondary"
            if st.button(label, icon=icon, key=f"nav_{key}",
                         use_container_width=True, type=btn_type):
                st.session_state["page"] = key
                st.rerun()


    # ── Top-right user bar (main content) ──────────────────────────────────────
    _, info_col, btn_col = st.columns([7.5, 1.8, 0.5])
    with info_col:
        st.markdown(
            f"<div style='text-align:right;padding-top:4px;'>"
            f"<span style='font-size:13px;font-weight:600;color:#1a2535;'>"
            f"👤 {username}</span>"
            f"&nbsp;&nbsp;<span style='background:{badge_color};color:#fff;"
            f"border-radius:5px;padding:2px 9px;font-size:11px;font-weight:700;'>"
            f"{badge_label}</span></div>",
            unsafe_allow_html=True,
        )
    with btn_col:
        if st.button("", icon=":material/logout:", key="nav_logout",
                     use_container_width=True, help="Sign out"):
            do_logout()
            st.rerun()


# ── Sidebar: upload form ───────────────────────────────────────────────────────
def render_upload_sidebar() -> tuple:
    """Two uploaders (files + folder). Returns (all_unique_files, run_clicked)."""
    with st.sidebar:
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
def render_results(
    df: pd.DataFrame,
    db_available: bool = False,
    save_fn=None,
) -> None:

    ticket_rows = df[df.index.map(is_valid_ticket)]
    pnr_rows    = df[~df.index.map(is_valid_ticket)]
    filled      = df.notna().sum().sum()
    total_cells = len(df) * len(df.columns)
    pct         = filled / total_cells * 100 if total_cells > 0 else 0

    st.markdown(
        f"""
        <div class="fs-metrics">
            <div class="fs-card">
                <div class="fs-lbl">Total Rows</div>
                <div class="fs-val">{len(df):,}</div>
            </div>
            <div class="fs-card">
                <div class="fs-lbl">Ticket Rows</div>
                <div class="fs-val">{len(ticket_rows):,}</div>
            </div>
            <div class="fs-card">
                <div class="fs-lbl">PNR-Only Rows</div>
                <div class="fs-val">{len(pnr_rows):,}</div>
            </div>
            <div class="fs-card" style="background:linear-gradient(135deg,#1050c8 0%,#3b82f6 100%);">
                <div class="fs-lbl">Field Coverage</div>
                <div class="fs-val">{pct:.0f}%</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Prepare Excel once so the download button works in the toolbar ─────────
    raw = BytesIO()
    df.to_excel(raw, index=False, engine="openpyxl")
    styled_xl = apply_excel_styles(raw, df)
    fname = f"Sabre_Report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx"

    # ── Compact action toolbar above the table ─────────────────────────────────
    busy = st.session_state.get("busy", False)
    title_col, _, dl_col, db_col = st.columns([5, 1.5, 1.2, 1.2])

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

                    batch_label = st.text_input(
                        "Batch label",
                        value=pd.Timestamp.now().strftime("%Y-%m-%d"),
                        help="Tag added to every row to identify this import.",
                    )
                    table_name = st.text_input("Table", value="SabreReport")
                    write_mode = st.selectbox("If exists", ["append", "replace"])
                    if st.button("Save", icon=":material/save:",
                                 type="primary", use_container_width=True,
                                 key="save_flat_btn"):
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
