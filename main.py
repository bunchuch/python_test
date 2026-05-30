import streamlit as st
import pandas as pd
import re
from io import BytesIO

# --- 1. DEFINITIONS ---
HEADERS_44 = [
    "PrimaryDocNbr", "PNRCreateDate", "VCRCreateDate", "Airline", "Country", "City", "PCC",
    "AgentSine", "CouponStatus", "ClassOfService", "FltNo", "OperatingFlightNbr",
    "MarketingAirlineCode", "OperatingAirlineCode", "Sector", "Fare", "CreateIATANr",
    "CustomerFullName", "BookingCode", "FareBasisCode", "TourCode", "CouponSeqNbr",
    "SegmentTypeCode", "ServiceStartDate", "ServiceStartTime", "ServiceEndDate",
    "ServiceEndTime", "FlownFlightNbr", "FlownServiceStartDate", "FlownServiceStartCity",
    "FlownServiceEndCity", "FlownClassOfService", "FlownFlightOrigDate", "ServiceStartCity",
    "ServiceEndCity", "OD", "Kind", "Origin", "Destination", "CountryName",
    "RegionName", "Nationality", "NationalName", "TTYAirlineCode"
]

# ─── Record types where cols[3] is a ticket number ───────────────────────────
#  18=TkDocument, 19=TkCoupon, 20=TkTax, 21=TkTaxDetail, 22=TkPayment,
#  23=TktRemark, 25=TkDocumentHistory, 26=TktCouponHistory,
#  27=TkEndorsement, 29=TkProRation
TICKET_RECORD_TYPES = {"18", "19", "20", "21", "22", "23", "25", "26", "27", "29"}

# ─── Record types where cols[1] is PNR and cols[3] is VCRDate (NOT ticket) ───
# 00=Res, 01=ResFlight, 04=ResPassengerFT, 05=ResRemarks, 06=PreResSeat,
# 07=ResPaxDoc, 08=ResSuspDocAgmt, 09=ResSuspTimeLmt, 10=ResEmergencyCtc,
# 11=ResPassenger, 12=ResSSR, 13=ResTravelArranger, 14=ResPassengerEmail,
# 15=ResPassengerPhone, 16=ResODFlight, 28=ResDataIndex
PNR_RECORD_TYPES = {"00","01","04","05","06","07","08","09","10","11","12","13","14","15","16","28"}

COUNTRY_MAP = {
    "KH":"Cambodia","TH":"Thailand","VN":"Vietnam","AE":"United Arab Emirates",
    "HK":"Hong Kong","SG":"Singapore","MY":"Malaysia","ID":"Indonesia",
    "PH":"Philippines","MM":"Myanmar","LA":"Laos","CN":"China","JP":"Japan",
    "KR":"South Korea","IN":"India","AU":"Australia","NZ":"New Zealand",
    "GB":"United Kingdom","DE":"Germany","FR":"France","IT":"Italy","ITA":"Italy",
    "CH":"Switzerland","AT":"Austria","LU":"Luxembourg","US":"United States",
    "CA":"Canada","DZ":"Algeria","MA":"Morocco","SA":"Saudi Arabia",
    "QA":"Qatar","EG":"Egypt","LK":"Sri Lanka","BE":"Belgium","NL":"Netherlands",
    "SE":"Sweden","NO":"Norway","DK":"Denmark","ES":"Spain","PT":"Portugal",
    "GR":"Greece","PL":"Poland","CZ":"Czech Republic","FI":"Finland",
    "TR":"Turkey","ZA":"South Africa","BR":"Brazil",
}
REGION_MAP = {
    "KH":"Southeast Asia","TH":"Southeast Asia","VN":"Southeast Asia",
    "SG":"Southeast Asia","MY":"Southeast Asia","ID":"Southeast Asia",
    "PH":"Southeast Asia","MM":"Southeast Asia","LA":"Southeast Asia",
    "CN":"East Asia","JP":"East Asia","KR":"East Asia","HK":"East Asia",
    "AE":"Middle East","SA":"Middle East","QA":"Middle East",
    "EG":"Africa","DZ":"Africa","ZA":"Africa",
    "IN":"South Asia","LK":"South Asia",
    "AU":"Oceania","NZ":"Oceania",
    "US":"North America","CA":"North America",
    "BR":"South America",
    "GB":"Europe","DE":"Europe","FR":"Europe","IT":"Europe","ITA":"Europe",
    "CH":"Europe","AT":"Europe","LU":"Europe","NL":"Europe","BE":"Europe",
    "SE":"Europe","NO":"Europe","DK":"Europe","ES":"Europe","PT":"Europe",
    "GR":"Europe","PL":"Europe","CZ":"Europe","FI":"Europe","TR":"Europe",
}
NAT_MAP = {
    "AT":"Austrian","DE":"German","GB":"British","IT":"Italian","ITA":"Italian",
    "CH":"Swiss","FR":"French","NL":"Dutch","BE":"Belgian","SE":"Swedish",
    "DZ":"Algerian","KH":"Cambodian","TH":"Thai","VN":"Vietnamese",
    "CN":"Chinese","JP":"Japanese","KR":"Korean","AU":"Australian",
    "US":"American","CA":"Canadian","AE":"Emirati","IN":"Indian",
}
AIRPORT_CITY = {
    "KTI":"Koh Kong","SAI":"Ho Chi Minh City","SGN":"Ho Chi Minh City",
    "PNH":"Phnom Penh","REP":"Siem Reap","BKK":"Bangkok","HKG":"Hong Kong",
    "CDG":"Paris","LHR":"London","FRA":"Frankfurt","MUC":"Munich",
    "AUH":"Abu Dhabi","DXB":"Dubai","SIN":"Singapore","ALG":"Algiers",
    "MRS":"Marseille","NCE":"Nice","NTE":"Nantes",
}

def is_valid_ticket(val):
    return bool(re.match(r'^\d{13}$', str(val).strip()))

def g(cols, idx, default=""):
    try:
        v = cols[idx].strip()
        return v if v else default
    except:
        return default

def safe_set(row, field, value):
    """Only set if field is currently None/empty and value is non-empty."""
    if value and not row.get(field):
        row[field] = value

def parse_pcc(s):
    if not s:
        return ""
    s = s.replace("HDQ1B", "").replace("HDQ", "")
    return s.split("/")[0].strip()[:6]

# --- 2. HANDLERS (one per record type) ---

def handle_18(cols, row):
    """TkDocument — master ticket record. cols[3] = TicketNo."""
    row["PrimaryDocNbr"]   = g(cols, 3)        # TicketNo — ALWAYS overwrite
    safe_set(row, "PNRCreateDate",   g(cols, 2))
    safe_set(row, "VCRCreateDate",   g(cols, 5))
    safe_set(row, "Airline",         g(cols, 10))
    safe_set(row, "AgentSine",       g(cols, 9))
    safe_set(row, "CreateIATANr",    g(cols, 6))
    safe_set(row, "CustomerFullName",g(cols, 15))
    safe_set(row, "Fare",            g(cols, 31))

def handle_19(cols, row):
    """TkCoupon — one row per coupon/segment. cols[3] = TicketNo."""
    safe_set(row, "PrimaryDocNbr",    g(cols, 3))
    safe_set(row, "CouponStatus",     g(cols, 15))
    safe_set(row, "ClassOfService",   g(cols, 20))
    safe_set(row, "FltNo",            g(cols, 12))
    safe_set(row, "CouponSeqNbr",     g(cols, 7))
    safe_set(row, "ServiceStartDate", g(cols, 16))
    safe_set(row, "ServiceStartTime", g(cols, 17))
    dep = g(cols, 13); arr = g(cols, 14)
    safe_set(row, "ServiceStartCity", dep)
    safe_set(row, "ServiceEndCity",   arr)
    safe_set(row, "Sector",           dep + arr if dep and arr else "")
    safe_set(row, "FlownFlightNbr",       g(cols, 12))
    safe_set(row, "FlownServiceStartDate",g(cols, 16))
    safe_set(row, "FlownServiceStartCity",dep)
    safe_set(row, "FlownServiceEndCity",  arr)
    safe_set(row, "FlownClassOfService",  g(cols, 20))
    safe_set(row, "FareBasisCode",        g(cols, 21))

def handle_00(cols, row):
    """Res — master PNR header."""
    safe_set(row, "PNRCreateDate",  g(cols, 2))
    safe_set(row, "VCRCreateDate",  g(cols, 3))
    safe_set(row, "TTYAirlineCode", g(cols, 4))
    safe_set(row, "Airline",        g(cols, 13))
    safe_set(row, "PCC",            parse_pcc(g(cols, 11)))
    safe_set(row, "AgentSine",      g(cols, 10))
    safe_set(row, "CreateIATANr",   g(cols, 18))

def handle_01(cols, row):
    """ResFlight — flight segments. cols[5] = BookingCode (RBD)."""
    safe_set(row, "BookingCode",          g(cols, 5))    # ★ ClassInd = RBD
    safe_set(row, "ClassOfService",       g(cols, 5))
    safe_set(row, "CouponStatus",         g(cols, 10))
    safe_set(row, "SegmentTypeCode",      g(cols, 11))
    safe_set(row, "FltNo",                g(cols, 15))
    safe_set(row, "MarketingAirlineCode", g(cols, 16))
    safe_set(row, "OperatingFlightNbr",   g(cols, 15))
    safe_set(row, "OperatingAirlineCode", g(cols, 17))
    safe_set(row, "Airline",              g(cols, 17))
    dep = g(cols, 25); arr = g(cols, 28)
    safe_set(row, "ServiceStartCity",     dep)
    safe_set(row, "ServiceEndCity",       arr)
    safe_set(row, "Sector",               dep + arr if dep and arr else "")
    safe_set(row, "City",                 AIRPORT_CITY.get(dep, dep))
    safe_set(row, "ServiceStartDate",     g(cols, 26))
    safe_set(row, "ServiceStartTime",     g(cols, 27))
    safe_set(row, "ServiceEndDate",       g(cols, 29))
    safe_set(row, "ServiceEndTime",       g(cols, 30))
    safe_set(row, "FlownFlightNbr",       g(cols, 15))
    safe_set(row, "FlownServiceStartDate",g(cols, 26))
    safe_set(row, "FlownServiceStartCity",dep)
    safe_set(row, "FlownServiceEndCity",  arr)
    safe_set(row, "FlownClassOfService",  g(cols, 5))
    safe_set(row, "FlownFlightOrigDate",  g(cols, 26))

def handle_16(cols, row):
    """ResODFlight — OD pairs + country."""
    dep = g(cols, 5); arr = g(cols, 6); nation = g(cols, 9)
    safe_set(row, "Origin",      dep)
    safe_set(row, "Destination", arr)
    safe_set(row, "OD",          dep + arr if dep and arr else "")
    safe_set(row, "Country",     nation)
    safe_set(row, "CountryName", COUNTRY_MAP.get(nation, nation))
    safe_set(row, "RegionName",  REGION_MAP.get(nation, ""))
    safe_set(row, "City",        AIRPORT_CITY.get(dep, dep))

def handle_11(cols, row):
    """ResPassenger — passenger names."""
    first = g(cols, 5); last = g(cols, 6)
    name = f"{last}/{first}".strip("/")
    safe_set(row, "CustomerFullName", name)

def handle_07(cols, row):
    """ResPaxDoc — passport/documents."""
    nat = g(cols, 11)
    safe_set(row, "Nationality",  nat)
    safe_set(row, "NationalName", NAT_MAP.get(nat, nat))
    safe_set(row, "Country",      nat)
    safe_set(row, "CountryName",  COUNTRY_MAP.get(nat, nat))
    safe_set(row, "RegionName",   REGION_MAP.get(nat, ""))
    first = g(cols, 12); last = g(cols, 14)
    safe_set(row, "CustomerFullName", f"{last}/{first}".strip("/"))

def handle_04(cols, row):
    """ResPassengerFT — frequent traveler."""
    safe_set(row, "MarketingAirlineCode", g(cols, 18))

def handle_05(cols, row):
    """ResRemarks."""
    txt = g(cols, 5).upper()
    if "VOID" in txt:
        safe_set(row, "Kind", "VOID")
    elif "RFD" in txt or "REFUND" in txt:
        safe_set(row, "Kind", "RFND")
    elif "EXCH" in txt:
        safe_set(row, "Kind", "EXCH")

def handle_08(cols, row):
    """ResSuspDocAgmt — suspended ticket references."""
    tkt = g(cols, 21)
    if is_valid_ticket(tkt):
        safe_set(row, "PrimaryDocNbr", tkt)
    tkt_type = g(cols, 18)
    safe_set(row, "Kind", {"TE":"OC","TK":"OC","TAW":"OC"}.get(tkt_type, ""))

def handle_25(cols, row):
    """TkDocumentHistory — derive Kind from Action."""
    action = g(cols, 7).upper()
    kind_map = {"OC":"OC","VOID":"VOID","RFND":"RFND","EXCH":"EXCH","PNRP":"PNRP"}
    safe_set(row, "Kind", kind_map.get(action, action))

# Dispatch table
HANDLERS = {
    "00": handle_00,  "01": handle_01,  "04": handle_04,
    "05": handle_05,  "07": handle_07,  "08": handle_08,
    "11": handle_11,  "16": handle_16,  "18": handle_18,
    "19": handle_19,  "25": handle_25,
}

# --- 3. PROCESSING ENGINE ---
def process_data(uploaded_files):
    """
    Two-pass approach:
      Pass 1: Parse all lines, build PNR→TicketNo map from rec18
      Pass 2: Route each line to the correct row (ticket or PNR-based)
    """
    all_lines = []
    pnr_to_tickets = {}   # PNR → set of ticket numbers

    # ── Pass 1: Collect all lines + build PNR↔Ticket mapping ──────────────────
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

            # rec18: cols[1]=PNR, cols[3]=TicketNo
            rtype = cols[0].strip()
            if rtype == "18" and len(cols) > 3:
                pnr = cols[1].strip()
                tkt = cols[3].strip()
                if pnr and is_valid_ticket(tkt):
                    pnr_to_tickets.setdefault(pnr, set()).add(tkt)

            # rec19: also has PNR→Ticket mapping
            if rtype == "19" and len(cols) > 3:
                pnr = cols[1].strip()
                tkt = cols[3].strip()
                if pnr and is_valid_ticket(tkt):
                    pnr_to_tickets.setdefault(pnr, set()).add(tkt)

    # ── Master table: keyed by TICKET NUMBER ──────────────────────────────────
    master = {}  # ticket_number → row dict

    # Also keep PNR-only rows for records that don't link to any ticket
    pnr_data = {}  # PNR → collected field values (for enrichment)

    # ── Pass 2: Process every line ─────────────────────────────────────────────
    for cols in all_lines:
        rtype = cols[0].strip()
        pnr   = cols[1].strip() if len(cols) > 1 else ""
        handler = HANDLERS.get(rtype)
        if not handler:
            continue

        if rtype in TICKET_RECORD_TYPES:
            # ── Ticket record: key = cols[3] (ticket number) ──────────────────
            tkt = cols[3].strip() if len(cols) > 3 else ""
            if not is_valid_ticket(tkt):
                continue  # skip malformed ticket records

            if tkt not in master:
                master[tkt] = dict.fromkeys(HEADERS_44, None)
            handler(cols, master[tkt])

        elif rtype in PNR_RECORD_TYPES:
            # ── PNR record: collect data, then push to ALL linked tickets ─────
            # First, collect into pnr_data buffer
            if pnr not in pnr_data:
                pnr_data[pnr] = dict.fromkeys(HEADERS_44, None)
            handler(cols, pnr_data[pnr])

            # If this PNR links to ticket(s), also enrich those ticket rows
            linked_tickets = pnr_to_tickets.get(pnr, set())
            for tkt in linked_tickets:
                if tkt not in master:
                    master[tkt] = dict.fromkeys(HEADERS_44, None)
                handler(cols, master[tkt])

    # ── Post-process: PNR-only rows (no linked ticket) get their own rows ─────
    pnrs_with_tickets = set(pnr_to_tickets.keys())
    for pnr, row_data in pnr_data.items():
        if pnr not in pnrs_with_tickets:
            # This PNR has no ticket — keep as standalone row
            if any(v for v in row_data.values()):
                master[pnr] = row_data

    # ── Build DataFrame ───────────────────────────────────────────────────────
    df = pd.DataFrame.from_dict(master, orient="index")
    df = df.reindex(columns=HEADERS_44)

    # Ensure PrimaryDocNbr is filled from the key for ticket rows
    for idx in df.index:
        if is_valid_ticket(idx) and pd.isna(df.at[idx, "PrimaryDocNbr"]):
            df.at[idx, "PrimaryDocNbr"] = idx

    return df

# --- 4. STREAMLIT UI ---
st.set_page_config(page_title="Sabre Mapper", page_icon="✈️", layout="wide")

st.markdown("""
<style>
[data-testid="stHeader"] { background: linear-gradient(90deg, #1F4E79, #2E86C1); }
div.stButton > button[kind="primary"] { background: #1F4E79; }
</style>
""", unsafe_allow_html=True)

st.title("✈️ Sabre Master Processor")
st.markdown("Upload raw Sabre `.txt` files → auto-map to 44 columns → download Excel")

with st.sidebar:
    st.markdown("## How it works")
    st.markdown("""
1. **Pass 1** — Scan rec18/19 to build PNR↔Ticket mapping
2. **Pass 2** — Route each record to the correct ticket row
3. **Enrich** — PNR data (flights, pax, docs) fills into linked ticket rows
4. **Export** — Flat Excel with 44 columns
    """)
    st.markdown("---")
    st.markdown("### Key Fix ★")
    st.warning("**BookingCode** = rec01[5] (Y/K/C)  \nNOT the 6-char PNR code")
    st.markdown("---")
    st.markdown("### Record Types")
    st.markdown("""
**Ticket records** (key=TicketNo):  
`18` TkDocument, `19` TkCoupon,  
`20-29` Tax/Payment/History

**PNR records** (key=PNR→Ticket):  
`00` Res, `01` ResFlight,  
`07` ResPaxDoc, `11` ResPassenger,  
`16` ResODFlight, `08` SuspDoc
    """)

uploaded_files = st.file_uploader(
    "Drop Sabre .txt files here",
    accept_multiple_files=True,
    type=["txt", "dat", "log"],
)

if uploaded_files:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"**{len(uploaded_files)} file(s)** selected")
    with col2:
        run = st.button("🚀 Process Files", type="primary", use_container_width=True)

    if run:
        with st.spinner("Processing..."):
            df = process_data(uploaded_files)

        # Stats
        c1, c2, c3, c4 = st.columns(4)
        ticket_rows = df[df.index.map(is_valid_ticket)]
        pnr_rows = df[~df.index.map(is_valid_ticket)]
        c1.metric("Total Rows", len(df))
        c2.metric("Ticket Rows", len(ticket_rows))
        c3.metric("PNR-Only Rows", len(pnr_rows))

        # Coverage
        filled = df.notna().sum().sum()
        total_cells = len(df) * len(df.columns)
        pct = filled / total_cells * 100 if total_cells > 0 else 0
        c4.metric("Field Coverage", f"{pct:.0f}%")

        # Show data
        st.markdown("### Mapped Data")
        st.dataframe(df, use_container_width=True, height=500)

        # Column coverage
        with st.expander("📊 Column coverage"):
            cov = []
            for h in HEADERS_44:
                filled_ct = df[h].notna().sum()
                cov.append({"Column": h, "Filled": filled_ct, "Total": len(df),
                            "Coverage": f"{filled_ct/len(df)*100:.0f}%" if len(df) > 0 else "0%"})
            st.dataframe(pd.DataFrame(cov), use_container_width=True, hide_index=True)

        # Download
        output = BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        st.download_button(
            "📥 Download Excel",
            output.getvalue(),
            f"Sabre_Report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )