from datetime import date, timedelta
from io import BytesIO
import time

import pandas as pd
import streamlit as st

from data.excel_utils import apply_excel_styles

_DATE_COL_OPTIONS = [
    "PNRCreateDate",
    "ServiceStartDate",
    "VCRCreateDate",
    "ServiceEndDate",
    "ImportedAt",
]

_MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

_PAGE_SIZES = [50, 100, 200, 500]

# Label style matching the screenshot's blue-gray labels
_LBL = (
    "font-size:12px;font-weight:600;color:#1a6fff;"
    "letter-spacing:.3px;margin-bottom:4px;display:block;"
)


def render(
    db_available: bool,
    query_fn,
    get_years_fn,
) -> None:
    st.title(":material/search: Query Data")

    if not db_available:
        st.error(
            "Database is not available. Install SQLAlchemy and configure a connection.",
            icon=":material/error:",
        )
        st.code("pip install sqlalchemy", language="bash")
        return

    querying = st.session_state.get("q_querying", False)

    # ── Filter card ────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### :material/tune: Filter Settings")
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

        # Row 1 — table name + date column
        r1_left, r1_right = st.columns([1, 1], gap="large")
        with r1_left:
            st.markdown(f"<span style='{_LBL}'>Table name</span>",
                        unsafe_allow_html=True)
            table = st.text_input(
                "table", value="SabreReport", placeholder="e.g. SabreReport",
                label_visibility="collapsed",
                help="The database table to query.",
            )
        with r1_right:
            st.markdown(
                f"<span style='{_LBL}'>Date field to filter on</span>",
                unsafe_allow_html=True,
            )
            date_col = st.selectbox(
                "datecol", _DATE_COL_OPTIONS,
                label_visibility="collapsed",
                help="Which date column the filter applies to.",
            )

        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

        # Row 2 — filter mode segmented control
        st.markdown(f"<span style='{_LBL}'>Filter by</span>",
                    unsafe_allow_html=True)
        mode = st.segmented_control(
            "mode",
            options=["Year / Month", "Date Range", "All records"],
            default="Year / Month",
            label_visibility="collapsed",
        )

        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

        # Row 3 — dynamic filter inputs
        year = months = date_from = date_to = None

        if mode == "Year / Month":
            yr_col, mo_col = st.columns([1, 2], gap="large")
            with yr_col:
                st.markdown(f"<span style='{_LBL}'>Year</span>",
                            unsafe_allow_html=True)
                years = (
                    get_years_fn(table=table, date_col=date_col) if get_years_fn else []
                )
                if years:
                    year = st.selectbox("yr", years, label_visibility="collapsed")
                else:
                    year = st.number_input(
                        "yr", min_value=2000, max_value=date.today().year,
                        value=date.today().year, label_visibility="collapsed",
                    )
            with mo_col:
                st.markdown(f"<span style='{_LBL}'>Month(s)</span>",
                            unsafe_allow_html=True)
                selected = st.multiselect(
                    "mo",
                    options=list(range(1, 13)),
                    format_func=lambda m: _MONTH_NAMES[m],
                    default=[],
                    placeholder="Leave empty for all months",
                    label_visibility="collapsed",
                )
                months = selected if selected else None

        elif mode == "Date Range":
            from_col, to_col = st.columns([1, 1], gap="large")
            with from_col:
                st.markdown(f"<span style='{_LBL}'>From</span>",
                            unsafe_allow_html=True)
                date_from = st.date_input(
                    "from", value=date.today() - timedelta(days=30),
                    format="YYYY-MM-DD", label_visibility="collapsed",
                )
            with to_col:
                st.markdown(f"<span style='{_LBL}'>To</span>",
                            unsafe_allow_html=True)
                date_to = st.date_input(
                    "to", value=date.today(),
                    format="YYYY-MM-DD", label_visibility="collapsed",
                )

        else:
            st.caption(":material/info: All rows in the table will be returned.")

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        # Run / loading button
        if querying:
            st.button(
                "Processing data…",
                icon=":material/hourglass_top:",
                type="primary",
                disabled=True,
                use_container_width=True,
            )
        else:
            if st.button(
                "Run Query",
                icon=":material/search:",
                type="primary",
                use_container_width=True,
            ):
                st.session_state["q_querying"] = True
                st.session_state["q_params"] = {
                    "table": table, "date_col": date_col,
                    "year": year, "months": months,
                    "date_from": date_from, "date_to": date_to,
                }
                st.rerun()

    # ── Phase 2: execute query ─────────────────────────────────────────────────
    if querying:
        params = st.session_state.get("q_params", {})
        with st.spinner("Querying database, please wait…"):
            t0 = time.perf_counter()
            df, err = query_fn(**params)
            elapsed = time.perf_counter() - t0
        st.session_state["q_querying"] = False
        if err:
            st.error(f"Query failed: {err}", icon=":material/error:")
            st.session_state.pop("query_df", None)
            st.session_state.pop("query_elapsed", None)
        else:
            st.session_state["query_df"]      = df
            st.session_state["query_elapsed"] = elapsed
            st.session_state["q_page"]        = 0
            st.session_state["query_meta"]    = {
                "table":     params.get("table"),
                "date_col":  params.get("date_col"),
                "mode":      mode,
                "year":      params.get("year"),
                "months":    params.get("months"),
                "date_from": str(params.get("date_from") or ""),
                "date_to":   str(params.get("date_to")   or ""),
            }
            try:
                from data.db import log_event
                log_event(
                    "query_run",
                    st.session_state.get("_username", ""),
                    f"table={params.get('table')} mode={mode} rows={len(df)}",
                )
            except Exception:
                pass
        st.rerun()

    # ── Results ────────────────────────────────────────────────────────────────
    if "query_df" not in st.session_state:
        return

    df      = st.session_state["query_df"]
    meta    = st.session_state.get("query_meta", {})
    elapsed = st.session_state.get("query_elapsed")

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

    # Gradient metric cards
    elapsed_str = f"{elapsed:.2f} s" if elapsed is not None else "—"
    st.markdown(
        f"""
        <div class="fs-metrics">
            <div class="fs-card">
                <div class="fs-lbl">Rows Returned</div>
                <div class="fs-val">{len(df):,}</div>
            </div>
            <div class="fs-card">
                <div class="fs-lbl">Columns</div>
                <div class="fs-val">{len(df.columns)}</div>
            </div>
            <div class="fs-card"
                 style="background:linear-gradient(135deg,#1a7a44 0%,#27ae60 100%);">
                <div class="fs-lbl">Table</div>
                <div class="fs-val" style="font-size:18px;margin-top:4px;">
                    {meta.get("table", "—")}
                </div>
            </div>
            <div class="fs-card"
                 style="background:linear-gradient(135deg,#5c2d8a 0%,#8e44ad 100%);">
                <div class="fs-lbl">Filtered by</div>
                <div class="fs-val" style="font-size:14px;margin-top:6px;">
                    {meta.get("date_col", "—")}
                </div>
            </div>
            <div class="fs-card"
                 style="background:linear-gradient(135deg,#1050c8 0%,#3b82f6 100%);">
                <div class="fs-lbl">Query Time</div>
                <div class="fs-val">{elapsed_str}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df.empty:
        st.warning(
            "No records matched the filter. Try a different date range or filter mode.",
            icon=":material/filter_alt_off:",
        )
        return

    # ── Excel prep ────────────────────────────────────────────────────────────
    from core.config import HEADERS_44
    raw      = BytesIO()
    style_df = df[[c for c in HEADERS_44 if c in df.columns]]
    style_df.to_excel(raw, index=False, engine="openpyxl")
    styled_xl = apply_excel_styles(raw, style_df)
    fname     = _build_filename(meta)

    # ── Toolbar ───────────────────────────────────────────────────────────────
    title_col, _, dl_col = st.columns([5, 2, 1.2])
    with title_col:
        st.markdown("### Results")
    with dl_col:
        st.download_button(
            "Excel",
            styled_xl.getvalue(),
            fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            icon=":material/download:",
            use_container_width=True,
            help="Download full result set as formatted Excel",
        )

    # ── Pagination ────────────────────────────────────────────────────────────
    total_rows = len(df)

    if "q_page" not in st.session_state:
        st.session_state["q_page"] = 0
    if "q_size" not in st.session_state:
        st.session_state["q_size"] = 100

    df_sig = str((total_rows, list(df.columns)))
    if st.session_state.get("_q_sig") != df_sig:
        st.session_state["q_page"] = 0
        st.session_state["_q_sig"] = df_sig

    page_size   = st.session_state["q_size"]
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page        = min(st.session_state["q_page"], total_pages - 1)
    st.session_state["q_page"] = page

    start_idx = page * page_size
    end_idx   = min(start_idx + page_size, total_rows)
    page_df   = df.iloc[start_idx:end_idx]

    sz_col, prev_col, info_col, next_col, rows_col = st.columns(
        [1.6, 0.55, 2.2, 0.55, 2.2]
    )

    with sz_col:
        def _reset_q_page():
            st.session_state["q_page"] = 0
        st.selectbox(
            "Rows/page", _PAGE_SIZES,
            index=_PAGE_SIZES.index(page_size) if page_size in _PAGE_SIZES else 1,
            key="q_size", on_change=_reset_q_page,
            label_visibility="collapsed",
        )

    with prev_col:
        if st.button("", icon=":material/chevron_left:", key="q_prev",
                     use_container_width=True, disabled=(page == 0)):
            st.session_state["q_page"] -= 1
            st.rerun()

    with info_col:
        st.markdown(
            f"<p style='text-align:center;margin:0;padding-top:7px;"
            f"font-size:13px;color:#444;'>"
            f"Page <b>{page + 1}</b> / <b>{total_pages}</b></p>",
            unsafe_allow_html=True,
        )

    with next_col:
        if st.button("", icon=":material/chevron_right:", key="q_next",
                     use_container_width=True, disabled=(page >= total_pages - 1)):
            st.session_state["q_page"] += 1
            st.rerun()

    with rows_col:
        st.markdown(
            f"<p style='text-align:right;margin:0;padding-top:7px;"
            f"font-size:12px;color:#888;'>"
            f"Rows {start_idx + 1:,} – {end_idx:,} of {total_rows:,}</p>",
            unsafe_allow_html=True,
        )

    st.dataframe(page_df, use_container_width=True, height=500)


def _build_filename(meta: dict) -> str:
    mode = meta.get("mode", "")
    ts   = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
    if mode == "Year / Month":
        yr  = meta.get("year", "")
        mo  = "".join(_MONTH_NAMES.get(m, "") for m in (meta.get("months") or []))
        tag = f"{yr}{'_' + mo if mo else ''}"
    elif mode == "Date Range":
        tag = (
            f"{(meta.get('date_from') or '').replace('-', '')}"
            f"_{(meta.get('date_to') or '').replace('-', '')}"
        )
    else:
        tag = "all"
    return f"Sabre_Query_{tag}_{ts}.xlsx"
