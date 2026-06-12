import re

import pandas as pd

from core.config import HEADERS_44, PNR_RECORD_TYPES, TICKET_RECORD_TYPES
from core.handlers import HANDLERS, get_airline_from_ticket, is_valid_ticket


def process_data(uploaded_files):
    """
    Two-pass approach:
      Pass 1: Parse all lines, build PNR→TicketNo map from rec18/19.
      Pass 2: Route each line to the correct row (ticket or PNR-based).
    """
    all_lines = []
    pnr_to_tickets = {}

    # ── Pass 1 ────────────────────────────────────────────────────────────────
    for uf in uploaded_files:
        text = uf.getvalue().decode("utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if not line or "|" not in line:
                continue
            cols = [c.strip() for c in line.split("|")]
            if len(cols) < 2:
                continue
            all_lines.append(cols)

            rtype = cols[0].strip()
            if rtype in ("18", "19") and len(cols) > 3:
                pnr = cols[1].strip()
                tkt = cols[3].strip()
                if pnr and is_valid_ticket(tkt):
                    pnr_to_tickets.setdefault(pnr, set()).add(tkt)

    # ── Pass 2 ────────────────────────────────────────────────────────────────
    master = {}
    pnr_data = {}

    for cols in all_lines:
        rtype = cols[0].strip()
        pnr   = cols[1].strip() if len(cols) > 1 else ""
        handler = HANDLERS.get(rtype)
        if not handler:
            continue

        if rtype in TICKET_RECORD_TYPES:
            tkt = cols[3].strip() if len(cols) > 3 else ""
            if not is_valid_ticket(tkt):
                continue
            if tkt not in master:
                master[tkt] = dict.fromkeys(HEADERS_44, None)
            handler(cols, master[tkt])

        elif rtype in PNR_RECORD_TYPES:
            if pnr not in pnr_data:
                pnr_data[pnr] = dict.fromkeys(HEADERS_44, None)
            handler(cols, pnr_data[pnr])

            for tkt in pnr_to_tickets.get(pnr, set()):
                if tkt not in master:
                    master[tkt] = dict.fromkeys(HEADERS_44, None)
                handler(cols, master[tkt])

    # ── PNR-only rows (no linked ticket) ──────────────────────────────────────
    pnrs_with_tickets = set(pnr_to_tickets.keys())
    for pnr, row_data in pnr_data.items():
        if pnr not in pnrs_with_tickets and any(v for v in row_data.values()):
            master[pnr] = row_data

    # ── Build DataFrame ───────────────────────────────────────────────────────
    df = pd.DataFrame.from_dict(master, orient="index").reindex(columns=HEADERS_44)

    # Force string columns that must never be cast to numeric
    for _col in ("CreateIATANr", "PrimaryDocNbr", "FltNo", "OperatingFlightNbr",
                 "FlownFlightNbr", "CouponSeqNbr", "PCC"):
        if _col in df.columns:
            df[_col] = df[_col].where(df[_col].isna(), df[_col].astype(str))

    for idx in df.index:
        if is_valid_ticket(idx) and pd.isna(df.at[idx, "PrimaryDocNbr"]):
            df.at[idx, "PrimaryDocNbr"] = idx

    for idx in df.index:
        doc = df.at[idx, "PrimaryDocNbr"]
        if doc and is_valid_ticket(doc):
            prefix, iata = get_airline_from_ticket(doc)
            df.at[idx, "Airline"] = iata if iata else prefix

    # ── Strip "TKT" from name and fare ────────────────────────────────────────
    for col in ("CustomerFullName", "Fare"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda v: re.sub(r'\bTKT\b', '', str(v), flags=re.IGNORECASE).strip(" /,-")
                if pd.notna(v) and v != "" else v
            )

    return df
