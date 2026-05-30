import time

import streamlit as st

from processor import process_data
from ui import render_results


# ── Public entry point ────────────────────────────────────────────────────────

def render(uploaded_files: list, run: bool, db_available: bool, real_save_fn) -> None:
    action = st.session_state.get("busy_action", "")

    # ── Execute phase: do the heavy work FIRST, before any other UI ───────────
    if st.session_state.get("busy"):
        if action == "process":
            _exec_process()
        elif action == "save":
            _exec_save(real_save_fn)
        return  # nothing else renders while busy

    # ── Trigger phase: capture button click, rerun into execute phase ─────────
    if run and uploaded_files:
        n = len(uploaded_files)
        st.session_state.update({
            "busy":            True,
            "busy_action":     "process",
            "busy_msg":        f"Processing {n} file{'s' if n > 1 else ''}…",
            "_pending_files":  uploaded_files,
            "last_action":     None,   # clear previous badge
        })
        st.rerun()
        return

    # ── Normal render ─────────────────────────────────────────────────────────
    st.title(":material/flight: Sabre Master Processor")
    st.markdown(
        "Upload Sabre `.txt` files → auto-map to **44 columns** "
        "→ download Excel or save to the database."
    )

    _render_last_result_badge()

    if "df" in st.session_state:
        render_results(
            df=st.session_state["df"],
            db_available=db_available,
            save_fn=_save_trigger,   # triggers phase instead of calling DB directly
        )
    else:
        st.info("Upload one or more Sabre files on the left, then click **Process Files**.",
                icon=":material/info:")


# ── Execute helpers ───────────────────────────────────────────────────────────

def _exec_process() -> None:
    _busy_banner()
    files = st.session_state.get("_pending_files", [])
    t0 = time.perf_counter()
    with st.spinner(""):
        df = process_data(files)
    elapsed = round(time.perf_counter() - t0, 1)
    st.session_state.update({
        "df":           df,
        "busy":         False,
        "busy_action":  "",
        "last_action":  "process",
        "last_elapsed": elapsed,
        "last_rows":    len(df),
        "tbl_page":     0,        # always start at page 1 for fresh data
    })
    st.rerun()


def _exec_save(real_save_fn) -> None:
    _busy_banner()
    params = st.session_state.get("_pending_save_params", {})
    t0 = time.perf_counter()
    with st.spinner(""):
        ok, msg = real_save_fn(
            st.session_state["df"],
            table=params.get("table", "SabreReport"),
            if_exists=params.get("if_exists", "append"),
            batch_label=params.get("batch_label", ""),
        )
    elapsed = round(time.perf_counter() - t0, 1)
    st.session_state.update({
        "busy":        False,
        "busy_action": "",
        "last_action": "save",
        "last_elapsed": elapsed,
        "save_result": (ok, msg),
    })
    st.rerun()


# ── Save trigger (passed as save_fn to render_results) ────────────────────────

def _save_trigger(df, table, if_exists, batch_label) -> None:
    """Sets up the execute phase for saving; called by the Save button in the UI."""
    st.session_state.update({
        "busy":        True,
        "busy_action": "save",
        "busy_msg":    f"Saving to [{table}]…",
        "_pending_save_params": {
            "table":       table,
            "if_exists":   if_exists,
            "batch_label": batch_label,
        },
        "last_action": None,
    })
    st.rerun()


# ── UI helpers ────────────────────────────────────────────────────────────────

def _busy_banner() -> None:
    msg = st.session_state.get("busy_msg", "Working…")
    st.warning(
        f"**{msg}**  \nPlease wait — all actions are locked until this completes.",
        icon=":material/hourglass_empty:",
    )


def _render_last_result_badge() -> None:
    last = st.session_state.get("last_action")
    t    = st.session_state.get("last_elapsed")
    if last is None or t is None:
        return

    if last == "process":
        rows = st.session_state.get("last_rows", 0)
        st.success(f"Processed **{rows:,}** rows — :material/timer: {t} s",
                   icon=":material/check_circle:")

    elif last == "save":
        ok, msg = st.session_state.get("save_result", (False, ""))
        if ok:
            st.success(f"{msg} — :material/timer: {t} s", icon=":material/save:")
        else:
            st.error(msg, icon=":material/error:")
