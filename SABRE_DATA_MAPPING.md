# Sabre Raw Data — Mapping & Processing Guide

This document describes how Sabre raw text files (`.txt`) are parsed, mapped
to the 44-column output schema, and exported as a formatted Excel file.

---

## Table of Contents

1. [Input File Format](#1-input-file-format)
2. [Record Types](#2-record-types)
3. [Two-Pass Processing Algorithm](#3-two-pass-processing-algorithm)
4. [Column Mapping by Record Type](#4-column-mapping-by-record-type)
5. [Lookup Tables & Enrichment](#5-lookup-tables--enrichment)
6. [Post-Processing Rules](#6-post-processing-rules)
7. [Output: 44 Columns](#7-output-44-columns)
8. [Excel Export Formatting](#8-excel-export-formatting)

---

## 1. Input File Format

### Structure

Each Sabre export file is a **plain text file** (`.txt`, `.dat`, or `.log`)
where every line is one record. Fields within a record are separated by the
pipe character `|` and may have leading/trailing spaces.

```
<RecordType> | <PNR> | <field2> | <field3> | ... | <fieldN>
```

**Example lines:**

```
18 | ABC123 | 20260101 | 1881234567890 | ... | SMITH/JOHN | ...
19 | ABC123 | 1 | 1881234567890 | ... | CTRL | ... | BKK | PNH | ...
00 | ABC123 | 20260101 | 20260101 | K6 | ...
01 | ABC123 | 0 | 0 | 0 | Y | ... | BKK | 20260101 | 0800 | PNH | ...
```

### Parsing Rules

| Rule | Detail |
|------|--------|
| Encoding | UTF-8 (invalid bytes replaced) |
| Skip line if | blank, or no `\|` character present |
| Skip line if | fewer than 2 pipe-separated fields |
| Column index | 0-based after split on `\|` and `.strip()` |

---

## 2. Record Types

Records are divided into two categories based on column 0.

### Ticket Records *(key = 13-digit e-ticket number)*

| Code | Name | Description |
|------|------|-------------|
| `18` | TkDocument | Primary ticket document — ticket number, dates, fare, agent |
| `19` | TkCoupon | Coupon detail — flight segment, coupon status, routing |
| `20` | TkTax | Tax total |
| `21` | TkTaxDetail | Individual tax breakdown |
| `22` | TkPayment | Payment form |
| `23` | TktRemark | Free-text remark attached to ticket |
| `25` | TkDocumentHistory | Ticket lifecycle action (void, refund, exchange) |
| `26` | TktCouponHistory | Coupon-level history |
| `27` | TkEndorsement | Endorsement/restriction text |
| `29` | TkProRation | Proration data |

> Only records **18** and **19** currently have active field mappings.
> Records 20–29 are recognised and routed to their ticket row but produce
> no additional column output unless a handler is added.

### PNR Records *(key = PNR → merged into linked ticket rows)*

| Code | Name | Description |
|------|------|-------------|
| `00` | Res | PNR header — booking creation date, PCC, TTY airline |
| `01` | ResFlight | Flight segment — routing, schedule, class of service |
| `04` | ResPassengerFT | Frequent-flyer membership |
| `05` | ResRemarks | Free-text remarks (scanned for VOID/REFUND/EXCH keywords) |
| `07` | ResPaxDoc | Passport/document — nationality, name |
| `08` | ResSuspDocAgmt | Suspended document agreement — links alternate ticket numbers |
| `11` | ResPassenger | Passenger name record |
| `16` | ResODFlight | Origin-destination pair — used for OD, Country, Region |
| `25` | TkDocumentHistory | Document history action code |
| `28` | ResDataIndex | Index record (no column output) |

---

## 3. Two-Pass Processing Algorithm

The processor (`processor.py`) uses two sequential passes over all input lines.

### Pass 1 — Build PNR ↔ Ticket Map

```
for every line in all files:
    if record type is 18 or 19:
        pnr   = cols[1]
        ticket = cols[3]
        if ticket is a valid 13-digit number:
            pnr_to_tickets[pnr].add(ticket)
```

This map is used in Pass 2 to know which ticket row(s) PNR data belongs to.
A single PNR can be linked to multiple tickets (e.g., multi-passenger booking).

### Pass 2 — Route Each Record

```
for every line:
    if record type is a TICKET type:
        key = cols[3]  ← the 13-digit ticket number
        create row in master[key] if not exists
        call handler(cols, master[key])

    if record type is a PNR type:
        key = cols[1]  ← the PNR
        store in pnr_data[key]
        for every ticket linked to this PNR:
            call handler(cols, master[ticket])   ← copy into ticket row
```

### PNR-Only Rows

If a PNR has **no linked ticket** at all (no rec18/rec19 found for it),
the PNR data becomes its own standalone row in the output, keyed by PNR.

### Merge Priority (`safe_set`)

All PNR field writes use `safe_set(row, field, value)`:

```python
def safe_set(row, field, value):
    if value and not row.get(field):   # write only if field is still empty
        row[field] = value
```

Ticket record handlers (18, 19) write directly (`row[field] = value`) for
their own primary fields, so ticket data is never overwritten by PNR data.

---

## 4. Column Mapping by Record Type

### rec18 — TkDocument (Ticket Record)

*Primary source for ticket identity, fare, and agent information.*

| Output Column | Source | cols[] index |
|---|---|---|
| `PrimaryDocNbr` | Direct assignment | `cols[3]` |
| `PNRCreateDate` | safe_set | `cols[2]` |
| `VCRCreateDate` | safe_set | `cols[5]` |
| `Airline` | safe_set | `cols[10]` |
| `CreateIATANr` | safe_set | `cols[6]` |
| `CustomerFullName` | safe_set | `cols[15]` |
| `AgentSine` | Direct if non-empty | `cols[9]` |
| `Fare` | Scan cols[27–54] | First 3-letter currency code + numeric amount found |

**Fare scanning logic:**  
The processor scans columns 27 through 54 looking for two patterns:
- A 3-letter string matching `[A-Z]{3}` that is **not** a passenger type code
  (`ADT`, `CHD`, `INF`, `INS`, `CCR`, `NET`) → treated as currency (e.g. `THB`, `USD`)
- A numeric string matching `^\d+\.\d+$` with value > 0 → treated as amount

Result is formatted as `"1,234.56 THB"`.

---

### rec19 — TkCoupon (Ticket Record)

*Primary source for coupon status, routing, and flight segment details.*

| Output Column | Source | cols[] index |
|---|---|---|
| `PrimaryDocNbr` | safe_set | `cols[3]` |
| `CouponStatus` | **Direct** (always overwrites) | `cols[8]` → `CTRL / USED / OPEN / VOID / RFND / EXCH` |
| `CouponSeqNbr` | safe_set | `cols[7]` |
| `FltNo` | safe_set | `cols[12]` |
| `ServiceStartDate` | safe_set | `cols[16]` |
| `ServiceStartTime` | safe_set | `cols[17]` |
| `ServiceStartCity` | safe_set | `cols[13]` *(departure IATA)* |
| `ServiceEndCity` | safe_set | `cols[14]` *(arrival IATA)* |
| `Sector` | safe_set | `cols[13] + cols[14]` *(e.g. `BKKPNH`)* |
| `ClassOfService` | safe_set | `cols[20]` |
| `FareBasisCode` | safe_set | `cols[21]` |
| `FlownFlightNbr` | safe_set | `cols[12]` |
| `FlownServiceStartDate` | safe_set | `cols[16]` |
| `FlownServiceStartCity` | safe_set | `cols[13]` |
| `FlownServiceEndCity` | safe_set | `cols[14]` |
| `FlownClassOfService` | safe_set | `cols[20]` |

> **Note:** `CouponStatus` uses a direct write (not `safe_set`) so it always
> reflects the actual coupon status from rec19, never overwritten by PNR data.

---

### rec00 — Res / PNR Header (PNR Record)

*Booking creation dates and agency identification.*

| Output Column | Source | cols[] index |
|---|---|---|
| `PNRCreateDate` | safe_set | `cols[2]` |
| `VCRCreateDate` | safe_set | `cols[3]` |
| `TTYAirlineCode` | safe_set | `cols[4]` |
| `Airline` | safe_set | `cols[13]` |
| `PCC` | safe_set, parsed | `cols[11]` → strips `HDQ1B`/`HDQ` prefix, takes first 6 chars before `/` |
| `CreateIATANr` | safe_set | `cols[18]` |

---

### rec01 — ResFlight (PNR Record)

*Flight segment detail — most routing and scheduling data comes from here.*

| Output Column | Source | cols[] index |
|---|---|---|
| `BookingCode` | safe_set | `cols[5]` |
| `ClassOfService` | safe_set | `cols[5]` |
| `SegmentTypeCode` | safe_set | `cols[11]` |
| `FltNo` | safe_set | `cols[15]` |
| `MarketingAirlineCode` | safe_set | `cols[16]` |
| `OperatingFlightNbr` | safe_set | `cols[15]` |
| `OperatingAirlineCode` | safe_set | `cols[17]` |
| `Airline` | safe_set | `cols[17]` |
| `ServiceStartCity` | safe_set | `cols[25]` *(departure IATA)* |
| `ServiceEndCity` | safe_set | `cols[28]` *(arrival IATA)* |
| `Sector` | safe_set | `cols[25] + cols[28]` |
| `City` | safe_set | `AIRPORT_CITY[cols[25]]` *(city name lookup)* |
| `ServiceStartDate` | safe_set | `cols[26]` |
| `ServiceStartTime` | safe_set | `cols[27]` |
| `ServiceEndDate` | safe_set | `cols[29]` |
| `ServiceEndTime` | safe_set | `cols[30]` |
| `FlownFlightNbr` | safe_set | `cols[15]` |
| `FlownServiceStartDate` | safe_set | `cols[26]` |
| `FlownServiceStartCity` | safe_set | `cols[25]` |
| `FlownServiceEndCity` | safe_set | `cols[28]` |
| `FlownClassOfService` | safe_set | `cols[5]` |
| `FlownFlightOrigDate` | safe_set | `cols[26]` |

---

### rec16 — ResODFlight (PNR Record)

*Origin-destination pair, nationality-based country/region.*

| Output Column | Source | cols[] index |
|---|---|---|
| `Origin` | safe_set | `cols[5]` |
| `Destination` | safe_set | `cols[6]` |
| `OD` | safe_set | `cols[5] + cols[6]` *(e.g. `BKKPNH`)* |
| `Country` | safe_set | `cols[9]` *(2-letter ISO)* |
| `CountryName` | safe_set | `COUNTRY_MAP[cols[9]]` |
| `RegionName` | safe_set | `REGION_MAP[cols[9]]` |
| `City` | safe_set | `AIRPORT_CITY[cols[5]]` |

---

### rec11 — ResPassenger (PNR Record)

| Output Column | Source | cols[] index |
|---|---|---|
| `CustomerFullName` | safe_set | `cols[6] + "/" + cols[5]` → `"SMITH/JOHN"` |

---

### rec07 — ResPaxDoc (PNR Record)

*Passport/travel document — nationality and passenger name.*

| Output Column | Source | cols[] index |
|---|---|---|
| `Nationality` | safe_set | `cols[11]` *(2-letter ISO)* |
| `NationalName` | safe_set | `NAT_MAP[cols[11]]` *(e.g. `"Thai"`)* |
| `Country` | safe_set | `cols[11]` |
| `CountryName` | safe_set | `COUNTRY_MAP[cols[11]]` |
| `RegionName` | safe_set | `REGION_MAP[cols[11]]` |
| `CustomerFullName` | safe_set | `cols[14] + "/" + cols[12]` |

---

### rec04 — ResPassengerFT (PNR Record)

| Output Column | Source | cols[] index |
|---|---|---|
| `MarketingAirlineCode` | safe_set | `cols[18]` |

---

### rec05 — ResRemarks (PNR Record)

*Free-text remarks scanned for transaction keywords.*

| Output Column | Logic |
|---|---|
| `Kind` | safe_set: `"VOID"` if `"VOID"` in text; `"RFND"` if `"RFD"` or `"REFUND"` in text; `"EXCH"` if `"EXCH"` in text |

---

### rec08 — ResSuspDocAgmt (PNR Record)

| Output Column | Source | cols[] index |
|---|---|---|
| `PrimaryDocNbr` | safe_set (only if cols[21] is valid 13-digit ticket) | `cols[21]` |
| `Kind` | safe_set via map `{TE→OC, TK→OC, TAW→OC}` | `cols[18]` |

---

### rec25 — TkDocumentHistory (Ticket Record)

| Output Column | Source | cols[] index |
|---|---|---|
| `Kind` | safe_set via map `{OC, VOID, RFND, EXCH, PNRP}` | `cols[7]` |

---

## 5. Lookup Tables & Enrichment

### Airline Prefix → IATA Code

The first 3 digits of a 13-digit e-ticket identify the airline:

| Prefix | IATA | Airline |
|--------|------|---------|
| `188` | K6 | Air Cambodia |
| `114` | TG | Thai Airways |
| `176` | EK | Emirates |
| `125` | BA | British Airways |
| `057` | AF | Air France |
| `076` | SQ | Singapore Airlines |
| `134` | CX | Cathay Pacific |
| `235` | TK | Turkish Airlines |
| `016` | UA | United Airlines |
| `695` | AA | American Airlines |
| *(70+ prefixes total)* | | |

This lookup is applied as a **post-processing step** after all records are
merged — it fills `Airline` if not already set from rec18/rec01.

### Airport → City Name (`AIRPORT_CITY`)

| IATA | City |
|------|------|
| `PNH` | Phnom Penh |
| `REP` | Siem Reap |
| `BKK` | Bangkok |
| `SGN` / `SAI` | Ho Chi Minh City |
| `DXB` | Dubai |
| `SIN` | Singapore |
| `HKG` | Hong Kong |
| `LHR` | London |
| `CDG` | Paris |
| `FRA` | Frankfurt |

### Country Code → Name and Region (`COUNTRY_MAP` / `REGION_MAP`)

| ISO | Country | Region |
|-----|---------|--------|
| `KH` | Cambodia | Southeast Asia |
| `TH` | Thailand | Southeast Asia |
| `VN` | Vietnam | Southeast Asia |
| `AE` | United Arab Emirates | Middle East |
| `CN` | China | East Asia |
| `JP` | Japan | East Asia |
| `GB` | United Kingdom | Europe |
| `US` | United States | North America |
| `AU` | Australia | Oceania |

### Nationality Code → Adjective (`NAT_MAP`)

| ISO | Nationality |
|-----|-------------|
| `KH` | Cambodian |
| `TH` | Thai |
| `VN` | Vietnamese |
| `CN` | Chinese |
| `GB` | British |
| `FR` | French |
| `DE` | German |
| `US` | American |

---

## 6. Post-Processing Rules

After all records are merged into the master dictionary, three additional
transformations are applied before building the DataFrame.

### Rule 1 — Fill Missing `PrimaryDocNbr`

For any row whose key is a valid 13-digit ticket number but `PrimaryDocNbr`
was never set by rec18/rec19:

```
if row key is valid ticket AND PrimaryDocNbr is empty:
    PrimaryDocNbr = row key
```

### Rule 2 — Fill `Airline` from Ticket Prefix

For every row where `PrimaryDocNbr` is a valid ticket number:

```
prefix = PrimaryDocNbr[:3]
Airline = AIRLINE_PREFIX.get(prefix, "")  if not already set
```

### Rule 3 — Strip "TKT" Noise from Name and Fare

Some Sabre records include the literal string `TKT` inside passenger name
or fare fields. Both `CustomerFullName` and `Fare` are cleaned with:

```python
re.sub(r'\bTKT\b', '', value, flags=re.IGNORECASE).strip(" /,-")
```

---

## 7. Output: 44 Columns

The final DataFrame always has exactly these 44 columns in this order:

| # | Column | Primary Source |
|---|--------|---------------|
| 1 | `PrimaryDocNbr` | rec18 col[3] |
| 2 | `PNRCreateDate` | rec18 col[2] / rec00 col[2] |
| 3 | `VCRCreateDate` | rec18 col[5] / rec00 col[3] |
| 4 | `Airline` | rec18 col[10] / rec01 col[17] / ticket prefix |
| 5 | `Country` | rec16 col[9] / rec07 col[11] |
| 6 | `City` | rec01/rec16 via AIRPORT_CITY |
| 7 | `PCC` | rec00 col[11] |
| 8 | `AgentSine` | rec18 col[9] |
| 9 | `CouponStatus` | **rec19 col[8]** — CTRL / USED / OPEN / VOID / RFND / EXCH |
| 10 | `ClassOfService` | rec19 col[20] / rec01 col[5] |
| 11 | `FltNo` | rec19 col[12] / rec01 col[15] |
| 12 | `OperatingFlightNbr` | rec01 col[15] |
| 13 | `MarketingAirlineCode` | rec01 col[16] / rec04 col[18] |
| 14 | `OperatingAirlineCode` | rec01 col[17] |
| 15 | `Sector` | rec19 / rec01: dep+arr |
| 16 | `Fare` | rec18 scanned fare |
| 17 | `CreateIATANr` | rec18 col[6] / rec00 col[18] |
| 18 | `CustomerFullName` | rec11 / rec07 / rec18 col[15] |
| 19 | `BookingCode` | rec01 col[5] |
| 20 | `FareBasisCode` | rec19 col[21] |
| 21 | `TourCode` | *(not currently mapped)* |
| 22 | `CouponSeqNbr` | rec19 col[7] |
| 23 | `SegmentTypeCode` | rec01 col[11] |
| 24 | `ServiceStartDate` | rec19 col[16] / rec01 col[26] |
| 25 | `ServiceStartTime` | rec19 col[17] / rec01 col[27] |
| 26 | `ServiceEndDate` | rec01 col[29] |
| 27 | `ServiceEndTime` | rec01 col[30] |
| 28 | `FlownFlightNbr` | rec19 col[12] / rec01 col[15] |
| 29 | `FlownServiceStartDate` | rec19 col[16] / rec01 col[26] |
| 30 | `FlownServiceStartCity` | rec19 col[13] / rec01 col[25] |
| 31 | `FlownServiceEndCity` | rec19 col[14] / rec01 col[28] |
| 32 | `FlownClassOfService` | rec19 col[20] / rec01 col[5] |
| 33 | `FlownFlightOrigDate` | rec01 col[26] |
| 34 | `ServiceStartCity` | rec19 col[13] / rec01 col[25] |
| 35 | `ServiceEndCity` | rec19 col[14] / rec01 col[28] |
| 36 | `OD` | rec16: origin+destination |
| 37 | `Kind` | rec25 / rec08 / rec05 keyword |
| 38 | `Origin` | rec16 col[5] |
| 39 | `Destination` | rec16 col[6] |
| 40 | `CountryName` | COUNTRY_MAP |
| 41 | `RegionName` | REGION_MAP |
| 42 | `Nationality` | rec07 col[11] |
| 43 | `NationalName` | NAT_MAP |
| 44 | `TTYAirlineCode` | rec00 col[4] |

### CouponStatus Values

| Value | Meaning |
|-------|---------|
| `CTRL` | Controlled — ticket issued, not yet flown |
| `USED` | Used — coupon has been lifted/flown |
| `OPEN` | Open — no flight assigned yet |
| `VOID` | Void — cancelled before use |
| `RFND` | Refunded — fare returned to passenger |
| `EXCH` | Exchanged — reissued for another flight |

### Kind Values

| Value | Source |
|-------|--------|
| `OC` | rec25 `OC` action / rec08 TE·TK·TAW type |
| `VOID` | rec25 `VOID` / rec05 remark text |
| `RFND` | rec25 `RFND` / rec05 remark text |
| `EXCH` | rec25 `EXCH` / rec05 remark text |
| `PNRP` | rec25 `PNRP` action |

---

## 8. Excel Export Formatting

The Excel file is produced by `excel_utils.py` using **openpyxl**.

| Property | Value |
|----------|-------|
| Engine | openpyxl |
| Sheet | Single sheet (active) |
| Header fill | Solid `#1F4E79` (dark navy) |
| Header font | Bold, white, 10 pt, centered |
| Row stripes | `TableStyleMedium9` — light-blue alternating stripes |
| Column width | Auto-fitted to content, maximum 40 characters |
| Freeze panes | Row 1 (header stays visible while scrolling) |
| Table name | `SabreData` (Excel named table — sortable/filterable) |

### Performance Note

For large datasets (thousands of rows), the exporter avoids a per-cell style
loop. Instead it:
1. Styles **only the 44 header cells** individually.
2. Registers an openpyxl `Table` object with a built-in stripe style for data
   rows — this is an O(1) operation regardless of row count.

---

## Quick Reference: File → Column Flow

```
Sabre .txt file(s)
        │
        ▼
   Pass 1: scan rec18/rec19 → build PNR ↔ Ticket map
        │
        ▼
   Pass 2: route every line
     ├─ Ticket record (18/19/25…)  ──► master[ticket_no]
     └─ PNR record (00/01/07/11…)  ──► pnr_data[pnr]
                                        + master[each linked ticket]
        │
        ▼
   PNR-only rows (no ticket found) ──► master[pnr]
        │
        ▼
   Post-process
     ├─ Fill PrimaryDocNbr from row key
     ├─ Fill Airline from ticket prefix (AIRLINE_PREFIX)
     └─ Strip "TKT" noise from name/fare
        │
        ▼
   DataFrame (44 columns, one row per ticket or PNR)
        │
        ├─► Download as Excel (.xlsx)
        │     └─ apply_excel_styles: header fill, stripe table, auto-width
        │
        └─► Save to database (SQLite or SQL Server)
              └─ ImportedAt timestamp + BatchLabel added per row
```
