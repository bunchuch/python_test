import re

from core.config import AIRLINE_PREFIX, AIRPORT_CITY, COUNTRY_MAP, NAT_MAP, REGION_MAP


def is_valid_ticket(val):
    return bool(re.match(r'^\d{13}$', str(val).strip()))


def get_airline_from_ticket(ticket_no):
    """Return (prefix, iata_code) from first 3 digits of a 13-digit e-ticket."""
    if not ticket_no or not re.match(r'^\d{13}$', str(ticket_no).strip()):
        return "", ""
    prefix = str(ticket_no).strip()[:3]
    return prefix, AIRLINE_PREFIX.get(prefix, "")


def g(cols, idx, default=""):
    try:
        v = cols[idx].strip()
        return v if v else default
    except Exception:
        return default


def safe_set(row, field, value):
    if value and not row.get(field):
        row[field] = value


def parse_pcc(s):
    if not s:
        return ""
    s = s.replace("HDQ1B", "").replace("HDQ", "")
    return s.split("/")[0].strip()[:6]


# ── Date normalisation ─────────────────────────────────────────────────────────
# Sabre dates arrive as "25JAN25" or "25JAN2025"; normalise to "YYYY-MM-DD".
_MON = {"JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,
        "JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12}

def normalize_date(val: str) -> str:
    if not val:
        return val
    val = val.strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', val):
        return val                             # already ISO
    m = re.match(r'^(\d{1,2})([A-Z]{3})(\d{2,4})$', val.upper())
    if m:
        day, mon, yr = m.group(1), m.group(2), m.group(3)
        month = _MON.get(mon)
        if month:
            if len(yr) == 2:
                yr = ("20" if int(yr) < 70 else "19") + yr
            try:
                return f"{int(yr):04d}-{month:02d}-{int(day):02d}"
            except ValueError:
                pass
    return val                                 # return as-is if unrecognised


# ── Fare currency codes to skip (passenger type / non-currency 3-letter codes) ─
_FARE_SKIP = {
    "ADT", "CHD", "INF", "INS", "CCR", "NET", "BSP", "PTA",
    "MPD", "MCO", "EMD", "TAX", "YQ",  "YR",  "XT",
}

# ── Record handlers ────────────────────────────────────────────────────────────

_DATE_PAT = re.compile(
    r'^(\d{1,2}[A-Z]{3}\d{2,4}'   # 25JAN26 / 25JAN2026
    r'|\d{4}-\d{2}-\d{2}'          # 2026-01-25
    r'|\d{2}/\d{2}/\d{4}'          # 01/25/2026
    r'|\d{1,2}-[A-Z]{3}-\d{2,4}'  # 25-JAN-26
    r'|\d{8}'                       # 20260125
    r')$',
    re.IGNORECASE,
)

# PCC pattern: exactly 4 alphanumeric chars, at least one letter (not all digits)
_PCC_PAT = re.compile(r'^[A-Z0-9]{4}$')
# rec18 columns already assigned to other fields — skip during PCC scan
_PCC_SKIP_COLS = frozenset({2, 3, 5, 6, 9, 10, 14, 15})
# YYYYMMDD date disguised as 8 digits — exclude from IATA scan
_IATA_DATE_PAT = re.compile(r'^(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$')


def handle_18(cols, row):
    row["PrimaryDocNbr"] = g(cols, 3)
    safe_set(row, "PNRCreateDate",    normalize_date(g(cols, 2)))
    safe_set(row, "VCRCreateDate",    normalize_date(g(cols, 5)))
    safe_set(row, "Airline",          g(cols, 10))
    safe_set(row, "CustomerFullName", g(cols, 15))

    tc = re.sub(r'^(IT|BT|IND)[/\-]?', '', g(cols, 14).strip(), flags=re.IGNORECASE).strip().upper()
    if tc and not _DATE_PAT.match(tc):
        safe_set(row, "TourCode", tc)

    agent = g(cols, 9)
    if agent:
        safe_set(row, "AgentSine", agent)

    # Fallback: scan rec18 cols 4-25 for 8-digit IATA office number.
    # Skip values that look like YYYYMMDD dates (col[4] is a date field).
    for _i in range(4, min(len(cols), 26)):
        _v = re.sub(r'\D', '', g(cols, _i))
        if len(_v) == 8 and not _IATA_DATE_PAT.match(_v):
            safe_set(row, "CreateIATANr", _v)
            break

    # PCC fallback for group bookings where rec00[11] is empty:
    # scan for first 4-char alphanumeric value (at least one letter) in unassigned cols
    for _i in range(4, min(len(cols), 26)):
        if _i in _PCC_SKIP_COLS:
            continue
        _v = g(cols, _i)
        if _PCC_PAT.match(_v) and not _v.isdigit():
            safe_set(row, "PCC", _v)
            break

    # Take the FIRST valid fare amount and the FIRST valid 3-letter currency found
    # scanning cols 27-54.  Stopping on first complete pair avoids picking up
    # tax totals or other trailing numeric/alpha fields that appear later.
    fare_amount = ""
    fare_currency = ""
    for i in range(27, min(len(cols), 55)):
        val = g(cols, i)
        if not fare_currency and re.match(r'^[A-Z]{3}$', val) and val not in _FARE_SKIP:
            fare_currency = val
        if not fare_amount and re.match(r'^\d+\.\d+$', val):
            try:
                if float(val) > 0:
                    fare_amount = val
            except ValueError:
                pass
        if fare_amount and fare_currency:
            break

    if fare_amount:
        try:
            formatted = f"{float(fare_amount):,.2f}"
            row["Fare"] = f"{formatted} {fare_currency}" if fare_currency else formatted
        except ValueError:
            row["Fare"] = fare_amount
    elif not row.get("Fare"):
        row["Fare"] = ""


def handle_19(cols, row):
    safe_set(row, "PrimaryDocNbr",        g(cols, 3))
    row["CouponStatus"] = g(cols, 8)      # CTRL/USED/OPEN/VOID/RFND/EXCH
    safe_set(row, "ClassOfService",       g(cols, 20))
    safe_set(row, "FltNo",                g(cols, 12))
    safe_set(row, "CouponSeqNbr",         g(cols, 7))
    safe_set(row, "ServiceStartDate",     normalize_date(g(cols, 16)))
    safe_set(row, "ServiceStartTime",     g(cols, 17))
    safe_set(row, "ServiceEndDate",       normalize_date(g(cols, 18)))
    safe_set(row, "ServiceEndTime",       g(cols, 19))
    dep = g(cols, 13); arr = g(cols, 14)
    safe_set(row, "ServiceStartCity",         dep)
    safe_set(row, "ServiceEndCity",           arr)
    safe_set(row, "Sector",                   dep + arr if dep and arr else "")
    safe_set(row, "FlownFlightNbr",           g(cols, 12))
    safe_set(row, "FlownServiceStartDate",    normalize_date(g(cols, 16)))
    safe_set(row, "FlownServiceStartCity",    dep)
    safe_set(row, "FlownServiceEndCity",      arr)
    safe_set(row, "FlownClassOfService",      g(cols, 20))
    fbc = g(cols, 21).strip().upper().split("/")[0].strip()
    safe_set(row, "FareBasisCode", fbc)


def handle_00(cols, row):
    safe_set(row, "PNRCreateDate",  normalize_date(g(cols, 2)))
    safe_set(row, "VCRCreateDate",  normalize_date(g(cols, 3)))
    safe_set(row, "TTYAirlineCode", g(cols, 4))
    safe_set(row, "Airline",        g(cols, 13))
    safe_set(row, "BookingCode",     g(cols, 1))
    safe_set(row, "PCC",            parse_pcc(g(cols, 11)))  # from HDQ string
    safe_set(row, "PCC",            g(cols, 10))             # direct PCC fallback
    _country = g(cols, 5)
    safe_set(row, "Country",     _country)
    safe_set(row, "CountryName", COUNTRY_MAP.get(_country, _country) if _country else "")
    safe_set(row, "RegionName",  REGION_MAP.get(_country, "") if _country else "")
    # HDQ string: HDQ[prefix][PCC]/[AgentSine]/[IATAOfficeNo8]
    hdq = g(cols, 11)
    safe_set(row, "BookingType", "NORMAL" if hdq else "GROUP")
    if hdq:
        clean = hdq.replace("HDQ1B", "").replace("HDQ", "")
        parts = [p.strip() for p in clean.split("/")]
        if len(parts) >= 2 and parts[1]:
            safe_set(row, "AgentSine", parts[1])
        if len(parts) >= 3:
            iata = re.sub(r'\D', '', parts[2])
            if len(iata) >= 8:
                safe_set(row, "CreateIATANr", iata[:8])
    # IATA fallbacks for when HDQ is absent or empty
    iata18 = re.sub(r'\D', '', g(cols, 18))
    if len(iata18) == 8:
        safe_set(row, "CreateIATANr", iata18)
    iata30 = re.sub(r'\D', '', g(cols, 30))
    if len(iata30) == 8 and iata30 != '00000000':
        safe_set(row, "CreateIATANr", iata30)


def handle_01(cols, row):
    safe_set(row, "ClassOfService",       g(cols, 5))
    safe_set(row, "SegmentTypeCode",      g(cols, 11))
    safe_set(row, "FltNo",                g(cols, 15))
    safe_set(row, "MarketingAirlineCode", g(cols, 19))
    safe_set(row, "OperatingFlightNbr",   g(cols, 15))
    safe_set(row, "OperatingAirlineCode", g(cols, 17))
    safe_set(row, "Airline",              g(cols, 17))
    dep = g(cols, 25); arr = g(cols, 28)
    safe_set(row, "ServiceStartCity",      dep)
    safe_set(row, "ServiceEndCity",        arr)
    safe_set(row, "Sector",                dep + arr if dep and arr else "")
    safe_set(row, "City",                  AIRPORT_CITY.get(dep, dep))
    safe_set(row, "ServiceStartDate",      normalize_date(g(cols, 26)))
    safe_set(row, "ServiceStartTime",      g(cols, 27))
    safe_set(row, "ServiceEndDate",        normalize_date(g(cols, 29)))
    safe_set(row, "ServiceEndTime",        g(cols, 30))
    safe_set(row, "FlownFlightNbr",        g(cols, 15))
    safe_set(row, "FlownServiceStartDate", normalize_date(g(cols, 26)))
    safe_set(row, "FlownServiceStartCity", dep)
    safe_set(row, "FlownServiceEndCity",   arr)
    safe_set(row, "FlownClassOfService",   g(cols, 5))
    safe_set(row, "FlownFlightOrigDate",   normalize_date(g(cols, 26)))


def handle_16(cols, row):
    dep = g(cols, 5); arr = g(cols, 6); nation = g(cols, 9)
    safe_set(row, "Origin",      dep)
    safe_set(row, "Destination", arr)
    safe_set(row, "OD",          dep + arr if dep and arr else "")
    safe_set(row, "Country",     nation)
    safe_set(row, "CountryName", COUNTRY_MAP.get(nation, nation))
    safe_set(row, "RegionName",  REGION_MAP.get(nation, ""))
    safe_set(row, "City",        AIRPORT_CITY.get(dep, dep))


def handle_11(cols, row):
    first = g(cols, 5); last = g(cols, 6)
    safe_set(row, "CustomerFullName", f"{last}/{first}".strip("/"))


def handle_07(cols, row):
    nat = g(cols, 11)
    safe_set(row, "Nationality",  nat)
    safe_set(row, "NationalName", NAT_MAP.get(nat, nat))
    # Country/CountryName/RegionName are intentionally NOT set here —
    # those fields reflect origin-country (from handle_16/ResODFlight),
    # not the passenger's passport nationality.
    first = g(cols, 12); last = g(cols, 14)
    safe_set(row, "CustomerFullName", f"{last}/{first}".strip("/"))


def handle_04(cols, row):
    safe_set(row, "MarketingAirlineCode", g(cols, 18))


def handle_05(cols, row):
    txt = g(cols, 5).upper()
    if "VOID" in txt:
        safe_set(row, "Kind", "VOID")
    elif "RFD" in txt or "REFUND" in txt:
        safe_set(row, "Kind", "RFND")
    elif "EXCH" in txt:
        safe_set(row, "Kind", "EXCH")


def handle_08(cols, row):
    tkt = g(cols, 21)
    if is_valid_ticket(tkt):
        safe_set(row, "PrimaryDocNbr", tkt)
    tkt_type = g(cols, 18)
    safe_set(row, "Kind", {"TE": "OC", "TK": "OC", "TAW": "OC"}.get(tkt_type, ""))


def handle_25(cols, row):
    action = g(cols, 7).upper()
    kind_map = {"OC": "OC", "VOID": "VOID", "RFND": "RFND", "EXCH": "EXCH", "PNRP": "PNRP"}
    safe_set(row, "Kind", kind_map.get(action, action))


HANDLERS = {
    "00": handle_00,  "01": handle_01,  "04": handle_04,
    "05": handle_05,  "07": handle_07,  "08": handle_08,
    "11": handle_11,  "16": handle_16,  "18": handle_18,
    "19": handle_19,  "25": handle_25,
}
