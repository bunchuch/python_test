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


# ── Record handlers ────────────────────────────────────────────────────────────

def handle_18(cols, row):
    row["PrimaryDocNbr"] = g(cols, 3)
    safe_set(row, "PNRCreateDate",    g(cols, 2))
    safe_set(row, "VCRCreateDate",    g(cols, 5))
    safe_set(row, "Airline",          g(cols, 10))
    safe_set(row, "CreateIATANr",     g(cols, 6))
    safe_set(row, "CustomerFullName", g(cols, 15))

    agent = g(cols, 9)
    if agent:
        row["AgentSine"] = agent

    fare_amount = ""
    fare_currency = ""
    for i in range(27, min(len(cols), 55)):
        val = g(cols, i)
        if re.match(r'^[A-Z]{3}$', val) and val not in ("ADT", "CHD", "INF", "INS", "CCR", "NET"):
            fare_currency = val
        if re.match(r'^\d+\.\d+$', val) and float(val) > 0:
            fare_amount = val

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
    row["CouponStatus"] = g(cols, 8)      # col 8 = CTRL/USED/OPEN/VOID/RFND/EXCH
    safe_set(row, "ClassOfService",       g(cols, 20))
    safe_set(row, "FltNo",                g(cols, 12))
    safe_set(row, "CouponSeqNbr",         g(cols, 7))
    safe_set(row, "ServiceStartDate",     g(cols, 16))
    safe_set(row, "ServiceStartTime",     g(cols, 17))
    dep = g(cols, 13); arr = g(cols, 14)
    safe_set(row, "ServiceStartCity",         dep)
    safe_set(row, "ServiceEndCity",           arr)
    safe_set(row, "Sector",                   dep + arr if dep and arr else "")
    safe_set(row, "FlownFlightNbr",           g(cols, 12))
    safe_set(row, "FlownServiceStartDate",    g(cols, 16))
    safe_set(row, "FlownServiceStartCity",    dep)
    safe_set(row, "FlownServiceEndCity",      arr)
    safe_set(row, "FlownClassOfService",      g(cols, 20))
    safe_set(row, "FareBasisCode",            g(cols, 21))


def handle_00(cols, row):
    safe_set(row, "PNRCreateDate",  g(cols, 2))
    safe_set(row, "VCRCreateDate",  g(cols, 3))
    safe_set(row, "TTYAirlineCode", g(cols, 4))
    safe_set(row, "Airline",        g(cols, 13))
    safe_set(row, "PCC",            parse_pcc(g(cols, 11)))
    safe_set(row, "CreateIATANr",   g(cols, 18))


def handle_01(cols, row):
    safe_set(row, "BookingCode",          g(cols, 5))
    safe_set(row, "ClassOfService",       g(cols, 5))
    safe_set(row, "SegmentTypeCode",      g(cols, 11))
    safe_set(row, "FltNo",                g(cols, 15))
    safe_set(row, "MarketingAirlineCode", g(cols, 16))
    safe_set(row, "OperatingFlightNbr",   g(cols, 15))
    safe_set(row, "OperatingAirlineCode", g(cols, 17))
    safe_set(row, "Airline",              g(cols, 17))
    dep = g(cols, 25); arr = g(cols, 28)
    safe_set(row, "ServiceStartCity",      dep)
    safe_set(row, "ServiceEndCity",        arr)
    safe_set(row, "Sector",                dep + arr if dep and arr else "")
    safe_set(row, "City",                  AIRPORT_CITY.get(dep, dep))
    safe_set(row, "ServiceStartDate",      g(cols, 26))
    safe_set(row, "ServiceStartTime",      g(cols, 27))
    safe_set(row, "ServiceEndDate",        g(cols, 29))
    safe_set(row, "ServiceEndTime",        g(cols, 30))
    safe_set(row, "FlownFlightNbr",        g(cols, 15))
    safe_set(row, "FlownServiceStartDate", g(cols, 26))
    safe_set(row, "FlownServiceStartCity", dep)
    safe_set(row, "FlownServiceEndCity",   arr)
    safe_set(row, "FlownClassOfService",   g(cols, 5))
    safe_set(row, "FlownFlightOrigDate",   g(cols, 26))


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
    safe_set(row, "Nationality",       nat)
    safe_set(row, "NationalName",      NAT_MAP.get(nat, nat))
    safe_set(row, "Country",           nat)
    safe_set(row, "CountryName",       COUNTRY_MAP.get(nat, nat))
    safe_set(row, "RegionName",        REGION_MAP.get(nat, ""))
    first = g(cols, 12); last = g(cols, 14)
    safe_set(row, "CustomerFullName",  f"{last}/{first}".strip("/"))


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
