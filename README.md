# Sabre Master Processor

A Streamlit web app that parses raw Sabre `.txt` data files, maps them to a flat 44-column structure, exports a formatted Excel report, and saves results to SQL Server.

---

## Project Structure

```
sabre-mapper/
├── main.py                  # Streamlit entry point
├── ui.py                    # Shared UI: navbar, sidebar, results panel
│
├── core/                    # Business logic
│   ├── config.py            # Column headers, record types, lookup maps
│   ├── handlers.py          # Record parsers (handle_00 … handle_25)
│   └── processor.py         # Two-pass processing engine
│
├── data/                    # Data layer
│   ├── db.py                # SQLite / SQL Server connection + helpers
│   └── excel_utils.py       # Excel styling: header, stripes, auto-fit
│
├── views/                   # Page modules (routed by main.py)
│   ├── page_processor.py    # Processor page
│   ├── page_query.py        # Query & export page
│   ├── page_database.py     # Database config page
│   └── page_guide.py        # Guide / reference page
│
├── assets/                  # Static files (logo, images)
│   └── K6.png
│
├── docs/                    # Documentation
│   └── SABRE_DATA_MAPPING.md
│
├── .streamlit/
│   └── config.toml          # Theme, upload size, usage stats
├── requirements.txt
└── .gitignore
```

---

## Requirements

- Python 3.9 or higher
- Microsoft ODBC Driver 17 (or 18) for SQL Server — [download here](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

---

## Installation

**1. Clone or download the project**

```bash
git clone <repo-url>
cd python_test
```

**2. (Optional) Create a virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install streamlit pandas openpyxl sqlalchemy pyodbc
```

---

## Running the App

```bash
python -m streamlit run main.py
```

Opens automatically at `http://localhost:8501`.

---

## SQL Server Setup

**1. Edit `db.py` — set your connection details:**

```python
DB_CONFIG = {
    "server":   "localhost",          # your server or IP\INSTANCE
    "database": "SabreDB",            # database name
    "driver":   "ODBC Driver 17 for SQL Server",
    "username": "",                   # blank = Windows Authentication
    "password": "",
}
```

**2. Test the connection** — click **Test Connection** in the sidebar.

**3. Save data** — after processing files, scroll to **Save to SQL Server**, choose a table name and write mode (`append` or `replace`), then click **Save**.

The table is created automatically on first save. A `BatchLabel` column is added to every row so you can track which import each record came from.

---

## 7-Day Data Analysis

### Expected data volume

| Metric | Estimate |
|--------|----------|
| Lines per day (mid-size agency) | 5,000 – 20,000 |
| Lines for 7 days | 35,000 – 140,000 |
| Unique tickets (output rows) | 1,000 – 10,000 |
| Raw memory for parsed lines | ~50 – 200 MB |
| Excel file size | ~2 – 8 MB |

### How the engine handles it

```
Pass 1  O(n)          Build PNR→Ticket map — linear scan, fast at any scale
Pass 2  O(n × t)      t = avg tickets per PNR (typically 1–4) — still fast
Post    O(rows)        Airline derivation, TKT strip — negligible
Excel   O(44)          Header styled cell-by-cell (44 ops only)
                       Data rows use an openpyxl Table style — no per-cell loop
DB save O(rows/500)    Chunked INSERT with fast_executemany — ~2–5 s for 5 k rows
```

### Known bottleneck (fixed)

The original `apply_excel_styles` looped over every cell (`rows × 44 cols`).
For 5,000 rows that was **220,000 openpyxl cell writes** — ~30–60 seconds.

**Fix applied:** data rows now use an openpyxl `Table` with `TableStyleMedium9`
(blue header + alternating stripes). The per-cell loop is gone; styling is instant
regardless of row count.

### Memory note

All lines from all 7 files are held in `all_lines` simultaneously during processing.
For 140,000 lines this is roughly 100–200 MB. If you see memory pressure, process
files day-by-day and use **append** mode in the DB save to accumulate results.

---

## How It Works

| Step | What happens |
|------|-------------|
| **Upload** | Drop one or more Sabre `.txt` / `.dat` / `.log` files |
| **Pass 1** | Scans `rec18` / `rec19` lines to build a PNR ↔ Ticket mapping |
| **Pass 2** | Routes every record to the correct ticket row via the dispatch table |
| **Enrich** | PNR data (flights, passengers, documents) is merged into linked ticket rows |
| **Export** | Download a styled Excel file with 44 columns, frozen header, and table stripes |
| **Save** | Optionally push the result to SQL Server (`append` or `replace`) |

---

## Output Columns (44)

`PrimaryDocNbr` · `PNRCreateDate` · `VCRCreateDate` · `Airline` · `Country` · `City` · `PCC` · `AgentSine` · `CouponStatus` · `ClassOfService` · `FltNo` · `OperatingFlightNbr` · `MarketingAirlineCode` · `OperatingAirlineCode` · `Sector` · `Fare` · `CreateIATANr` · `CustomerFullName` · `BookingCode` · `FareBasisCode` · `TourCode` · `CouponSeqNbr` · `SegmentTypeCode` · `ServiceStartDate` · `ServiceStartTime` · `ServiceEndDate` · `ServiceEndTime` · `FlownFlightNbr` · `FlownServiceStartDate` · `FlownServiceStartCity` · `FlownServiceEndCity` · `FlownClassOfService` · `FlownFlightOrigDate` · `ServiceStartCity` · `ServiceEndCity` · `OD` · `Kind` · `Origin` · `Destination` · `CountryName` · `RegionName` · `Nationality` · `NationalName` · `TTYAirlineCode`

---

## Supported Record Types

| Code | Name | Key |
|------|------|-----|
| `18` | TkDocument | Ticket No. |
| `19` | TkCoupon | Ticket No. |
| `20–29` | Tax / Payment / History | Ticket No. |
| `00` | Res (PNR header) | PNR |
| `01` | ResFlight | PNR |
| `07` | ResPaxDoc | PNR |
| `11` | ResPassenger | PNR |
| `16` | ResODFlight | PNR |
| `08` | ResSuspDocAgmt | PNR |
