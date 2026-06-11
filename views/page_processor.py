import time

import streamlit as st
import streamlit.components.v1 as components

from core.processor import process_data
from ui import render_results

# Injects webkitdirectory so the last file input becomes a folder picker.
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


def render(db_available: bool, real_save_fn) -> None:
    action = st.session_state.get("busy_action", "")

    # ── Execute phase ─────────────────────────────────────────────────────────
    if st.session_state.get("busy"):
        if action == "process":
            _exec_process()
        elif action == "save":
            _exec_save(real_save_fn)
        return

    # ── Page header ───────────────────────────────────────────────────────────
    has_results = "df" in st.session_state
    h_left, h_right = st.columns([5, 1])
    with h_left:
        st.title(":material/flight: Processor")
    if has_results:
        with h_right:
            st.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
            if st.button("New Upload", icon=":material/upload_file:",
                         use_container_width=True):
                st.session_state.pop("df", None)
                st.session_state["uploader_key"] = (
                    st.session_state.get("uploader_key", 0) + 1
                )
                st.rerun()

    _render_last_result_badge()

    # ── Route ────────────────────────────────────────────────────────────────
    if has_results:
        render_results(
            df=st.session_state["df"],
            db_available=db_available,
            save_fn=_save_trigger,
        )
    else:
        _render_upload_panel()
        _render_steps()


# ── Upload panel ──────────────────────────────────────────────────────────────

def _render_upload_panel() -> None:
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    # Mode selector
    mode = st.radio(
        "mode",
        [":material/description:  Files", ":material/folder_open:  Folder"],
        horizontal=True,
        key="proc_mode",
        label_visibility="collapsed",
    )
    folder_mode = "Folder" in mode
    k = f"proc_{st.session_state.uploader_key}_{mode}"

    # Hero text above drop zone
    st.markdown(
        """
        <div style='text-align:center;padding:22px 0 8px;'>
            <div style='font-size:48px;line-height:1;margin-bottom:12px;'>☁️</div>
            <div style='font-size:16px;font-weight:700;color:#1a2535;'>
                Drag &amp; drop your Sabre export files here
            </div>
            <div style='font-size:12.5px;color:#9ca3af;margin-top:6px;'>
                Accepted: &nbsp;<b>.txt</b>&nbsp;·&nbsp;<b>.dat</b>&nbsp;·&nbsp;<b>.log</b>
                &emsp;—&emsp; up to 200 MB per file
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "files",
        accept_multiple_files=True,
        type=["txt", "dat", "log"],
        key=k,
        label_visibility="collapsed",
    )

    if folder_mode:
        components.html(_FOLDER_INJECT, height=0)

    all_files = uploaded or []

    # File list card
    if all_files:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        file_rows = "".join(
            f"<div style='display:flex;align-items:center;justify-content:space-between;"
            f"padding:8px 16px;border-bottom:1px solid #f3f4f6;'>"
            f"<span style='font-size:13px;'>📄 <b>{f.name}</b></span>"
            f"<span style='font-size:12px;color:#9ca3af;'>"
            f"{round(len(f.getvalue()) / 1024, 1):,} KB</span></div>"
            for f in all_files
        )
        st.markdown(
            f"""
            <div style='border:1px solid #dbe7ff;border-radius:12px;
                        overflow:hidden;background:#fff;margin-bottom:6px;'>
                <div style='display:flex;align-items:center;gap:8px;
                            padding:10px 16px;
                            background:linear-gradient(90deg,#eef4ff,#f8fbff);
                            border-bottom:1px solid #dbe7ff;'>
                    <span style='font-size:13px;font-weight:700;color:#1a6fff;'>
                        ✓ &nbsp;{len(all_files)} file{"s" if len(all_files) != 1 else ""} ready
                    </span>
                </div>
                <div style='max-height:200px;overflow-y:auto;'>{file_rows}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Action buttons
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    btn_proc, btn_clr = st.columns([4, 1])
    with btn_proc:
        if st.button(
            "Process Files",
            icon=":material/rocket_launch:",
            type="primary",
            use_container_width=True,
            disabled=not bool(all_files),
            key="proc_run",
        ):
            n = len(all_files)
            st.session_state.update({
                "busy":           True,
                "busy_action":    "process",
                "busy_msg":       f"Processing {n} file{'s' if n > 1 else ''}…",
                "_pending_files": all_files,
                "last_action":    None,
            })
            st.rerun()
    with btn_clr:
        if st.button("Clear", icon=":material/delete:", use_container_width=True,
                     key="proc_clr"):
            st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
            st.rerun()


def _render_steps() -> None:
    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

    steps = [
        ("📁", "Upload",
         "Drop <code>.txt</code>, <code>.dat</code>, or <code>.log</code> "
         "Sabre export files above."),
        ("⚙️", "Process",
         "Click <b>Process Files</b>. The engine maps every record to the "
         "correct ticket row automatically."),
        ("📊", "Review",
         "Browse the <b>44-column</b> output table with pagination and "
         "column-coverage stats."),
        ("⬇️", "Export / Save",
         "Download a formatted <b>Excel</b> file or push the data directly "
         "to the configured database."),
    ]

    cols = st.columns(4)
    for i, (emoji, title, desc) in enumerate(steps):
        with cols[i]:
            st.markdown(
                f"""
                <div style="border:1px solid #dbe7ff;border-radius:14px;
                            padding:24px 18px;
                            background:linear-gradient(150deg,#eef4ff,#f8fbff);
                            text-align:center;min-height:170px;box-sizing:border-box;">
                  <div style="font-size:9.5px;font-weight:700;color:#1a6fff;
                              letter-spacing:.9px;margin-bottom:8px;">STEP {i + 1}</div>
                  <div style="font-size:26px;margin-bottom:8px;">{emoji}</div>
                  <div style="font-size:13px;font-weight:700;color:#1a2535;
                              margin-bottom:8px;">{title}</div>
                  <div style="font-size:12px;color:#6b7280;line-height:1.65;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander(":material/lightbulb: Tips & Notes"):
        st.markdown("""
- **Multiple files** — upload several days of exports at once; the engine merges them into one result
- **Folder mode** — switch to *Folder* to select all files from a directory at once
- **Accepted formats** — `.txt`, `.dat`, and `.log` all work if they contain pipe-delimited Sabre records
- **File size** — up to **200 MB** per upload; 7 days of typical agency data processes in 2–10 seconds
- **Deduplication** — each 13-digit ticket number appears exactly once; data from multiple files is merged
- **Date format** — all dates are normalised to `YYYY-MM-DD` automatically
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
        log_event("file_import", username,
                  f"files={len(files)} rows={len(df)} elapsed={elapsed}s")
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
        "busy":        False,
        "busy_action": "",
        "last_action": "save",
        "last_elapsed": elapsed,
        "save_result": (ok, msg),
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
        <div style="border:1px solid #dbe7ff;border-radius:12px;
                    background:linear-gradient(135deg,#eef4ff,#f0f8ff);
                    padding:22px 28px;
                    display:flex;align-items:center;gap:16px;margin-bottom:16px;">
          <span style="font-size:32px;">⏳</span>
          <div>
            <div style="font-size:15px;font-weight:700;color:#1a2535;">{msg}</div>
            <div style="font-size:12px;color:#6b7280;margin-top:3px;">
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
