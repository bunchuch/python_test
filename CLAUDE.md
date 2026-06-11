# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```powershell
python -m streamlit run main.py
```

Opens at `http://localhost:8501`. No build step — Streamlit auto-reloads on file save.

If you see a `TypeError` about wrong number of arguments after editing a `views/page_*.py` `render()` signature, delete the stale cache:

```powershell
Remove-Item -Recurse -Force views\__pycache__
```

## Architecture Overview

### Request flow

```
main.py
  ├── st.set_page_config + PAGE_CSS injected
  ├── is_authenticated() → None (loading) | False → render_login() | True → continue
  ├── render_navbar(page)   # sidebar nav + top-right user/logout bar
  └── page routing → views/page_*.py render()
```

### Two-pass processing engine (`core/processor.py`)

The core of the app. Accepts a list of Streamlit `UploadedFile` objects.

- **Pass 1** — scan every line; for `rec18` / `rec19` lines build `pnr_to_tickets: dict[pnr, set[ticket_no]]`
- **Pass 2** — route each line through `HANDLERS[rtype]`. Ticket records (`TICKET_RECORD_TYPES`) update `master[ticket_no]`; PNR records (`PNR_RECORD_TYPES`) fan-out to all tickets linked to that PNR
- Output: a `pd.DataFrame` with exactly the 44 columns from `core/config.py::HEADERS_44`

Pipe-delimited format — `cols = line.split("|")`. Column indices per record type are documented in `CLAUDE_CODE_PROMPT_MSSQL.md` and in handler docstrings.

### Auth / session persistence

Sessions survive browser refresh via a custom Streamlit component (`components/local_storage/index.html`) that reads/writes the browser's `localStorage`. The key is `sabre_sid`.

- `core/local_storage.py` — thin wrapper; `ls_get` returns `None` on the first render (component not ready), `''` when key is absent, or the string value
- `core/session_store.py` — in-memory token → `{username, role}` map
- `core/auth.py` — `is_authenticated()` returns `True | False | None`; `main.py` shows a blank loading screen on `None` and waits for the automatic rerun

### RBAC (`core/rbac.py`)

Single source of truth for permissions and navigation. Roles: `user`, `admin`, `dev`.

- `has_perm(permission)` — gate any feature
- `allowed_nav()` — returns `[(key, label, icon), ...]` tuples for the current role; used by `render_navbar()`
- `user` role sees only the Query page; `admin`/`dev` see all pages

### Database layer (`data/db.py`)

SQL Server via `mssql+pyodbc`. Connection details in `DB_CONFIG` dict at the top of the file; all values can be overridden with env vars (`DB_SERVER`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_DRIVER`). Blank `username` → Windows Authentication.

`save_to_db(df, table, if_exists, batch_label)` writes the 44-column DataFrame using `fast_executemany=True` in 500-row chunks.

`ensure_schema()` is called once on startup in `main.py` (idempotent) to create the users/sessions/audit tables.

### UI layer

- `ui.py` — `PAGE_CSS` (full CSS overrides for Forsight design system), `render_navbar()`, `render_results()`
- Design system: primary blue `#1a6fff`, sidebar bg `#f0f2f5`, main bg `#ffffff`, gradient cards via `.fs-metrics` / `.fs-card` CSS classes
- `render_navbar()` renders sidebar nav items and a top-right user/logout bar via `st.columns` in main content — the user bar appears *before* the page title, so page content starts below it
- `views/page_processor.py` owns file upload (drag-and-drop panel in main content, not sidebar)

### Key constants (`core/config.py`)

- `HEADERS_44` — the exact 44-column output schema; all DataFrames must use `.reindex(columns=HEADERS_44)`
- `TICKET_RECORD_TYPES` / `PNR_RECORD_TYPES` — routing sets used in the processor
- `AIRLINE_PREFIX` — 3-digit ticket prefix → 2-letter IATA code
- `AIRPORT_CITY`, `COUNTRY_MAP`, `REGION_MAP`, `NAT_MAP` — lookup dicts for enrichment

## Non-Negotiable Processing Rules

1. **Two-pass only** — Pass 1 must complete before any row is written
2. **`booking_code` = `rec01[5]`** — single RBD letter. Never the 6-char PNR
3. **`agent_sine` = `rec18[9]`** — ticketing agent. `rec00[9]` is PCC position code (different field)
4. **`airline_prefix` = `ticket_no[:3]`** — look up in `AIRLINE_PREFIX`; `iata_office_no` is an 8-digit number from `rec18[6]`
5. **Fare** stored as `DECIMAL(12,2)` + `CHAR(3)` currency; display as `"N.NN CUR"`
