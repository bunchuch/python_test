from datetime import date, timedelta
from io import BytesIO

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


def render(db_available: bool, query_fn, get_years_fn) -> None:
    st.title(":material/search: Query Data")
    st.markdown("Filter records saved in the database and export the results to Excel.")

    if not db_available:
        st.error("SQLAlchemy is not installed.", icon=":material/error:")
        st.code("pip install sqlalchemy", language="bash")
        return

    # ── Filter controls ────────────────────────────────────────────────────────
    st.markdown("---")
    fc1, fc2, fc3 = st.columns([1.8, 1.8, 4.4])

    with fc1:
        table = st.text_input("Table name", value="SabreReport")
        date_col = st.selectbox("Date column", _DATE_COL_OPTIONS)

    with fc2:
        mode = st.radio(
            "Filter mode",
            ["Year / Month", "Date Range", "All records"],
            help="Choose how to slice the data.",
        )

    year = months = date_from = date_to = None

    if mode == "Year / Month":
        with fc3:
            yr_col, mo_col = st.columns(2)
            with yr_col:
                # Try to load available years from DB; fall back to a number input
                years = get_years_fn(table=table, date_col=date_col) if get_years_fn else []
                if years:
                    year = st.selectbox("Year", years)
                else:
                    year = st.number_input(
                        "Year", min_value=2000, max_value=date.today().year,
                        value=date.today().year,
                    )
            with mo_col:
                selected = st.multiselect(
                    "Month(s)",
                    options=list(range(1, 13)),
                    format_func=lambda m: _MONTH_NAMES[m],
                    default=[],
                    placeholder="All months",
                )
                months = selected if selected else None

    elif mode == "Date Range":
        with fc3:
            default_from = date.today() - timedelta(days=30)
            dr = st.date_input(
                "Date range",
                value=(default_from, date.today()),
                format="YYYY-MM-DD",
            )
            if isinstance(dr, (list, tuple)) and len(dr) == 2:
                date_from, date_to = dr

    # ── Query button ───────────────────────────────────────────────────────────
    st.markdown("")
    run_query = st.button("Run Query", icon=":material/search:", type="primary")

    if run_query:
        with st.spinner("Querying SQL Server…"):
            df, err = query_fn(
                table=table,
                date_col=date_col,
                year=year,
                months=months,
                date_from=date_from,
                date_to=date_to,
            )
        if err:
            st.error(f"Query failed: {err}", icon=":material/error:")
            st.session_state.pop("query_df", None)
        else:
            st.session_state["query_df"] = df
            st.session_state["query_meta"] = {
                "table": table, "date_col": date_col,
                "mode": mode, "year": year, "months": months,
                "date_from": str(date_from) if date_from else None,
                "date_to":   str(date_to)   if date_to   else None,
            }

    # ── Results ────────────────────────────────────────────────────────────────
    if "query_df" in st.session_state:
        df = st.session_state["query_df"]
        meta = st.session_state.get("query_meta", {})

        st.markdown("---")

        # Summary metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rows returned", f"{len(df):,}")
        m2.metric("Columns", len(df.columns))
        m3.metric("Table", meta.get("table", "—"))
        m4.metric("Filtered by", meta.get("date_col", "—"))

        if df.empty:
            st.warning("Query returned 0 rows. Try adjusting the filters.",
                       icon=":material/filter_alt_off:")
            return

        st.markdown("### Results")
        st.dataframe(df, use_container_width=True, height=500)

        # ── Export ─────────────────────────────────────────────────────────────
        st.markdown("---")
        xl_col, _ = st.columns([1, 3])
        with xl_col:
            st.markdown("#### Export")
            raw = BytesIO()
            from core.config import HEADERS_44
            style_df = df[[c for c in HEADERS_44 if c in df.columns]]
            style_df.to_excel(raw, index=False, engine="openpyxl")
            styled_xl = apply_excel_styles(raw, style_df)

            fname = _build_filename(meta)
            st.download_button(
                "Download Excel",
                styled_xl.getvalue(),
                fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                icon=":material/download:",
                type="primary",
                use_container_width=True,
            )


def _build_filename(meta: dict) -> str:
    mode = meta.get("mode", "")
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
    if mode == "Year / Month":
        yr = meta.get("year", "")
        mo = "".join(_MONTH_NAMES.get(m, "") for m in (meta.get("months") or []))
        tag = f"{yr}{'_' + mo if mo else ''}"
    elif mode == "Date Range":
        tag = f"{(meta.get('date_from') or '').replace('-','')}_{(meta.get('date_to') or '').replace('-','')}"
    else:
        tag = "all"
    return f"Sabre_Query_{tag}_{ts}.xlsx"
