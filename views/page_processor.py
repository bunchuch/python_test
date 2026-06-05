import time

import streamlit as st

from core.processor import process_data
from ui import render_results


def render(uploaded_files: list, run: bool, db_available: bool, real_save_fn) -> None:
    action = st.session_state.get("busy_action", "")

    # ── Execute phase ─────────────────────────────────────────────────────────
    if st.session_state.get("busy"):
        if action == "process":
            _exec_process()
        elif action == "save":
            _exec_save(real_save_fn)
        return

    # ── Trigger phase ─────────────────────────────────────────────────────────
    if run and uploaded_files:
        n = len(uploaded_files)
        st.session_state.update({
            "busy":           True,
            "busy_action":    "process",
            "busy_msg":       f"Processing {n} file{'s' if n > 1 else ''}…",
            "_pending_files": uploaded_files,
            "last_action":    None,
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
            save_fn=_save_trigger,
        )
    else:
        _render_empty_state()


# ── Empty state ───────────────────────────────────────────────────────────────

def _render_empty_state() -> None:
    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    steps = [
        ("📁", "Upload Files",
         "Drop <code>.txt</code>, <code>.dat</code>, or <code>.log</code> "
         "Sabre export files in the left sidebar."),
        ("⚙️", "Process",
         "Click <b>Process Files</b>. The two-pass engine maps every record "
         "to the correct ticket row automatically."),
        ("📊", "Review",
         "Browse the <b>44-column</b> output table. Use the page controls "
         "to navigate large result sets."),
        ("⬇️", "Export / Save",
         "Download a formatted <b>Excel</b> file or push the data directly "
         "to the configured database."),
    ]

    cols = st.columns(4)
    for i, (emoji, title, desc) in enumerate(steps):
        with cols[i]:
            st.markdown(
                f"""
                <div style="border:1px solid #c8dff5;border-radius:12px;
                            padding:24px 18px;
                            background:linear-gradient(150deg,#eef6ff,#f8fcff);
                            text-align:center;min-height:170px;box-sizing:border-box;">
                  <div style="font-size:30px;margin-bottom:10px;">{emoji}</div>
                  <div style="font-size:10px;font-weight:700;color:#2E86C1;
                              letter-spacing:.8px;margin-bottom:6px;">STEP {i + 1}</div>
                  <div style="font-size:13px;font-weight:700;color:#1F4E79;
                              margin-bottom:10px;">{title}</div>
                  <div style="font-size:12px;color:#556;line-height:1.65;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.info(
        "Use the **sidebar on the left** to upload your Sabre files, "
        "then click **Process Files** to begin.",
        icon=":material/arrow_back:",
    )

    with st.expander(":material/lightbulb: Tips & Notes"):
        st.markdown("""
- **Multiple files** — upload several days of exports at once; the engine merges them into one result
- **Folder mode** — switch to *Folder* in the sidebar to select all files from a directory at once
- **Accepted formats** — `.txt`, `.dat`, and `.log` all work if they contain pipe-delimited Sabre records
- **File size** — up to **200 MB** per upload; 7 days of typical agency data processes in 2–10 seconds
- **Deduplication** — each 13-digit ticket number appears exactly once; data from multiple files is merged
- **Date format** — all dates are normalised to `YYYY-MM-DD` automatically for database compatibility
""")


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
        "tbl_page":     0,
    })
    try:
        from data.db import log_event
        username = st.session_state.get("_username", "")
        log_event("file_import", username, f"files={len(files)} rows={len(df)} elapsed={elapsed}s")
    except Exception:
        pass
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
        "busy":         False,
        "busy_action":  "",
        "last_action":  "save",
        "last_elapsed": elapsed,
        "save_result":  (ok, msg),
    })
    try:
        from data.db import log_event
        username = st.session_state.get("_username", "")
        log_event(
            "db_save", username,
            f"table={params.get('table')} mode={params.get('if_exists')} ok={ok}",
        )
    except Exception:
        pass
    st.rerun()


def _save_trigger(df, table, if_exists, batch_label) -> None:
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
    st.markdown(
        f"""
        <div style="border:1px solid #f5c842;border-radius:10px;
                    background:#fffbea;padding:20px 24px;
                    display:flex;align-items:center;gap:14px;margin-bottom:16px;">
          <span style="font-size:28px;">⏳</span>
          <div>
            <div style="font-size:14px;font-weight:700;color:#7a5800;">{msg}</div>
            <div style="font-size:12px;color:#9a7000;margin-top:2px;">
              Please wait — all actions are locked until this completes.
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_last_result_badge() -> None:
    last = st.session_state.get("last_action")
    t    = st.session_state.get("last_elapsed")
    if last is None or t is None:
        return

    if last == "process":
        rows = st.session_state.get("last_rows", 0)
        st.success(
            f"Processed **{rows:,}** rows in {t} s",
            icon=":material/check_circle:",
        )
    elif last == "save":
        ok, msg = st.session_state.get("save_result", (False, ""))
        if ok:
            st.success(f"{msg} — {t} s", icon=":material/save:")
        else:
            st.error(msg, icon=":material/error:")
