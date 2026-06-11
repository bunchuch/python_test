"""
Two-pass normalized processor.

Returns a dict of row-lists ready for insertion into the star schema:
  pnr        → fact_pnr
  ticket     → fact_ticket
  coupon     → fact_coupon  (rec19 primary, enriched by rec01)
  passenger  → dim_passenger (rec11 primary, enriched by rec07)
  od         → fact_od
  history    → fact_ticket_history
  payment    → fact_payment
  tax        → fact_tax
"""

import re
from collections import defaultdict

from core.config import AIRLINE_PREFIX
from core.handlers import g, parse_pcc, normalize_date, is_valid_ticket, _FARE_SKIP


# ── Time normalisation ────────────────────────────────────────────────────────
_TIME_HHMM = re.compile(r'^(\d{2})(\d{2})$')


def _norm_time(val: str):
    if not val:
        return None
    val = val.strip()
    if re.match(r'^\d{2}:\d{2}:\d{2}$', val):
        return val
    if re.match(r'^\d{2}:\d{2}$', val):
        return val + ':00'
    m = _TIME_HHMM.match(val)
    return f"{m.group(1)}:{m.group(2)}:00" if m else None


def _to_decimal(val: str):
    try:
        return float(val.replace(',', '')) if val else None
    except (ValueError, TypeError):
        return None


def _or_none(v: str):
    return v if v else None


# ── Main entry point ──────────────────────────────────────────────────────────

def process_normalized(uploaded_files) -> dict:
    """
    Two-pass processing into the normalized star schema structures.

    Pass 1 — scan rec18/rec19 to build:
      • pnr_to_tickets   : pnr  → set of ticket_nos
      • ticket_to_pnr    : ticket_no → pnr

    Pass 2 — route each line into the correct table accumulator.
    Post-pass — enrich fact_coupon rows with rec01 booking data.
    """
    all_lines: list[list[str]] = []
    pnr_to_tickets: dict[str, set] = defaultdict(set)
    ticket_to_pnr:  dict[str, str] = {}

    # ── Pass 1 ────────────────────────────────────────────────────────────────
    for uf in uploaded_files:
        raw = uf.getvalue().decode("utf-8", errors="replace")
        for line in raw.splitlines():
            line = line.strip()
            if not line or "|" not in line:
                continue
            cols = [c.strip() for c in line.split("|")]
            if len(cols) < 2:
                continue
            all_lines.append(cols)

            rtype = cols[0]
            if rtype in ("18", "19") and len(cols) > 3:
                pnr = cols[1].strip()
                tkt = cols[3].strip()
                if pnr and is_valid_ticket(tkt):
                    pnr_to_tickets[pnr].add(tkt)
                    ticket_to_pnr.setdefault(tkt, pnr)

    # ── Accumulators ─────────────────────────────────────────────────────────
    pnr_rows:     dict[str, dict] = {}           # pnr → row
    ticket_rows:  dict[str, dict] = {}           # ticket_no → row
    coupon_rows:  dict[tuple, dict] = {}         # (ticket_no, coupon_seq) → row
    pnr_rec01:    dict[str, list] = defaultdict(list)  # pnr → [cols, ...]
    pax_rows:     dict[tuple, dict] = {}         # (pnr, pax_seq) → row
    pnr_pax_seq:  dict[str, int]   = defaultdict(int)  # pnr → next pax_seq for rec07
    od_seq:       dict[str, int]   = defaultdict(int)  # pnr → next OD seq
    od_rows:      list[dict] = []
    history_rows: list[dict] = []
    payment_rows: list[dict] = []
    tax_rows:     list[dict] = []

    # ── Pass 2 ────────────────────────────────────────────────────────────────
    for cols in all_lines:
        rtype = cols[0]
        pnr   = g(cols, 1)

        # ── fact_pnr (rec00) ─────────────────────────────────────────────────
        if rtype == "00":
            if not pnr:
                continue
            if pnr not in pnr_rows:
                pnr_rows[pnr] = {}
            row = pnr_rows[pnr]
            row["pnr"] = pnr
            row.setdefault("create_date",    _or_none(normalize_date(g(cols, 2))))
            row.setdefault("vcr_date",       _or_none(normalize_date(g(cols, 3))))
            row.setdefault("tty_code",       _or_none(g(cols, 4)))
            row.setdefault("pcc",            _or_none(parse_pcc(g(cols, 11))))
            row.setdefault("airline",        _or_none(g(cols, 13)))
            row.setdefault("iata_office_no", _or_none(g(cols, 18)))

        # ── fact_ticket (rec18) ──────────────────────────────────────────────
        elif rtype == "18":
            tkt = g(cols, 3)
            if not is_valid_ticket(tkt):
                continue
            if tkt not in ticket_rows:
                ticket_rows[tkt] = {}
            row = ticket_rows[tkt]
            row["ticket_no"]      = tkt
            row["pnr"]            = _or_none(pnr)
            row["airline_prefix"] = tkt[:3]
            row.setdefault("agent_sine",     _or_none(g(cols, 9)))
            row.setdefault("pax_name",       _or_none(g(cols, 15)))
            row.setdefault("iata_office_no", _or_none(g(cols, 6)))

            # Fare: scan cols 27-54 for first (decimal, 3-letter-currency) pair
            fare_amount, fare_currency = None, None
            for i in range(27, min(len(cols), 55)):
                val = g(cols, i)
                if fare_currency is None and re.match(r'^[A-Z]{3}$', val) and val not in _FARE_SKIP:
                    fare_currency = val
                if fare_amount is None and re.match(r'^\d+\.\d+$', val):
                    try:
                        if float(val) > 0:
                            fare_amount = float(val)
                    except ValueError:
                        pass
                if fare_amount and fare_currency:
                    break
            if "fare_amount" not in row:
                row["fare_amount"]   = fare_amount
                row["fare_currency"] = _or_none(fare_currency)

        # ── fact_coupon (rec19 — primary source) ─────────────────────────────
        elif rtype == "19":
            tkt = g(cols, 3)
            if not is_valid_ticket(tkt):
                continue
            seq_raw = g(cols, 7)
            seq     = int(seq_raw) if seq_raw.isdigit() else 0
            key     = (tkt, seq)
            if key not in coupon_rows:
                coupon_rows[key] = {}
            row = coupon_rows[key]
            row["ticket_no"]  = tkt
            row["coupon_seq"] = seq or None
            row.setdefault("coupon_status",    _or_none(g(cols, 8)))
            row.setdefault("class_of_service", _or_none(g(cols, 20)))
            row.setdefault("flight_no",        _or_none(g(cols, 12)))
            row.setdefault("fare_basis",       _or_none(g(cols, 21)))
            dep = g(cols, 13); arr = g(cols, 14)
            row.setdefault("dep_airport", _or_none(dep))
            row.setdefault("arr_airport", _or_none(arr))
            row.setdefault("sector",      (dep + arr) if dep and arr else None)
            row.setdefault("dep_date",    _or_none(normalize_date(g(cols, 16))))
            row.setdefault("dep_time",    _norm_time(g(cols, 17)))
            row.setdefault("arr_date",    _or_none(normalize_date(g(cols, 18))))
            row.setdefault("arr_time",    _norm_time(g(cols, 19)))

        # ── rec01 — collected in order per PNR for later coupon enrichment ───
        elif rtype == "01":
            if pnr:
                pnr_rec01[pnr].append(cols)

        # ── dim_passenger (rec11 — pax_seq + name) ───────────────────────────
        elif rtype == "11":
            if not pnr:
                continue
            seq_raw = g(cols, 4)
            seq     = int(seq_raw) if seq_raw.isdigit() else (pnr_pax_seq[pnr] + 1)
            key     = (pnr, seq)
            if key not in pax_rows:
                pax_rows[key] = {}
            row = pax_rows[key]
            row["pnr"]     = pnr
            row["pax_seq"] = seq
            first = g(cols, 5); last = g(cols, 6)
            row.setdefault("first_name", _or_none(first))
            row.setdefault("last_name",  _or_none(last))
            row.setdefault("full_name",  _or_none(f"{last}/{first}".strip("/")))
            pnr_pax_seq[pnr] = max(pnr_pax_seq[pnr], seq)

        # ── dim_passenger (rec07 — doc info; matched to rec11 by PNR + name) ─
        elif rtype == "07":
            if not pnr:
                continue
            nat    = g(cols, 11)
            first  = g(cols, 12); last = g(cols, 14)
            dob    = _or_none(normalize_date(g(cols, 6)))
            doc_no = _or_none(g(cols, 7))
            doc_ty = _or_none(g(cols, 8))
            gender = _or_none(g(cols, 9))

            # Try to match an existing rec11 row by name
            matched = None
            for key, row in pax_rows.items():
                if key[0] != pnr:
                    continue
                if first and last:
                    if row.get("first_name") == first and row.get("last_name") == last:
                        matched = row
                        break
                elif not matched:
                    matched = row  # fallback: first passenger for this PNR

            if matched is None:
                # No rec11 row yet — create a stub
                seq = pnr_pax_seq[pnr] + 1
                pnr_pax_seq[pnr] = seq
                key = (pnr, seq)
                pax_rows[key] = {"pnr": pnr, "pax_seq": seq,
                                 "first_name": _or_none(first),
                                 "last_name":  _or_none(last),
                                 "full_name":  _or_none(f"{last}/{first}".strip("/"))}
                matched = pax_rows[key]

            matched.setdefault("dob",        dob)
            matched.setdefault("doc_number", doc_no)
            matched.setdefault("doc_type",   doc_ty)
            matched.setdefault("gender",     gender)
            matched.setdefault("nationality", _or_none(nat))

        # ── fact_od (rec16) ───────────────────────────────────────────────────
        elif rtype == "16":
            if not pnr:
                continue
            od_seq[pnr] += 1
            od_rows.append({
                "pnr":         pnr,
                "seq":         od_seq[pnr],
                "origin":      _or_none(g(cols, 5)),
                "destination": _or_none(g(cols, 6)),
                "board_nation":_or_none(g(cols, 9)),
            })

        # ── fact_ticket_history (rec25) ───────────────────────────────────────
        elif rtype == "25":
            tkt = g(cols, 3)
            if is_valid_ticket(tkt):
                history_rows.append({
                    "ticket_no":   tkt,
                    "action":      _or_none(g(cols, 7)),
                    "agent_sine":  _or_none(g(cols, 9)),
                    "action_date": _or_none(g(cols, 12)),
                })

        # ── fact_payment (rec22) ──────────────────────────────────────────────
        elif rtype == "22":
            tkt = g(cols, 3)
            if is_valid_ticket(tkt):
                payment_rows.append({
                    "ticket_no":    tkt,
                    "payment_code": _or_none(g(cols, 7)),
                    "amount":       _to_decimal(g(cols, 8)),
                    "currency":     _or_none(g(cols, 11)),
                    "payment_type": _or_none(g(cols, 12)),
                })

        # ── fact_tax (rec20) ──────────────────────────────────────────────────
        elif rtype == "20":
            tkt = g(cols, 3)
            if is_valid_ticket(tkt):
                tax_rows.append({
                    "ticket_no":  tkt,
                    "tax_amount": _to_decimal(g(cols, 7)),
                    "tax_code":   _or_none(g(cols, 8)),
                    "currency":   _or_none(g(cols, 11)),
                })

        # ── rec05 — kind (VOID/RFND/EXCH) via PNR fan-out ────────────────────
        elif rtype == "05":
            txt = g(cols, 5).upper()
            kind = None
            if "VOID" in txt:
                kind = "VOID"
            elif "RFD" in txt or "REFUND" in txt:
                kind = "RFND"
            elif "EXCH" in txt:
                kind = "EXCH"
            if kind:
                for tkt in pnr_to_tickets.get(pnr, set()):
                    if tkt in ticket_rows:
                        ticket_rows[tkt].setdefault("kind", kind)

        # ── rec25 already handled; kind from history ──────────────────────────

    # ── Post-pass: enrich coupons with rec01 booking info ────────────────────
    for pnr, rec01_list in pnr_rec01.items():
        tkts = pnr_to_tickets.get(pnr, set())
        # Group coupon keys by ticket_no, sorted by coupon_seq
        tkt_coupons: dict[str, list] = defaultdict(list)
        for key in coupon_rows:
            if key[0] in tkts:
                tkt_coupons[key[0]].append(key)
        for tkt, keys in tkt_coupons.items():
            for key in sorted(keys, key=lambda k: k[1] or 0):
                seq = key[1] or 1
                idx = seq - 1
                if idx < len(rec01_list):
                    r01 = rec01_list[idx]
                    row = coupon_rows[key]
                    row.setdefault("booking_code",  _or_none(g(r01, 5)[:1] if g(r01, 5) else ""))
                    row.setdefault("segment_type",  _or_none(g(r01, 11)))
                    row.setdefault("mkt_airline",   _or_none(g(r01, 16)))
                    row.setdefault("op_airline",    _or_none(g(r01, 17)))
                    row.setdefault("arr_date",      _or_none(normalize_date(g(r01, 29))))
                    row.setdefault("arr_time",      _norm_time(g(r01, 30)))

    # ── Post-pass: copy PCC and tty_airline from pnr_rows to ticket_rows ─────
    for tkt, row in ticket_rows.items():
        pnr = row.get("pnr")
        if pnr and pnr in pnr_rows:
            row.setdefault("pcc",        pnr_rows[pnr].get("pcc"))
            row.setdefault("tty_airline", pnr_rows[pnr].get("tty_code"))

    return {
        "pnr":       list(pnr_rows.values()),
        "ticket":    list(ticket_rows.values()),
        "coupon":    list(coupon_rows.values()),
        "passenger": list(pax_rows.values()),
        "od":        od_rows,
        "history":   history_rows,
        "payment":   payment_rows,
        "tax":       tax_rows,
    }
