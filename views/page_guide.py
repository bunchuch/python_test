import streamlit as st


def render() -> None:
    st.title(":material/menu_book: Guide")
    st.markdown("Everything you need to know about how the processor works.")

    # ── How it works ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## How It Works")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
### Pass 1 — Build PNR ↔ Ticket Map
Scans every `rec18` and `rec19` line to link each PNR to its ticket numbers.
This map is used in Pass 2 to know which ticket row PNR data belongs to.

### Pass 2 — Route Each Record
Every line is dispatched to the correct handler based on its record type (column 0).
- **Ticket records** (`18`, `19`, `20`–`29`): keyed by the 13-digit ticket number.
- **PNR records** (`00`, `01`, `07`, `11`, `16` …): merged into all linked ticket rows.
""")
    with col2:
        st.markdown("""
### Enrich
PNR-level data (passenger name, nationality, flight segments, OD pairs) is pushed
into every ticket row that shares the same PNR.
If a PNR has no linked ticket it becomes its own standalone row.

### Export
The result is a flat table with **44 columns**.
- Download as a formatted Excel file (blue header, alternating stripes, frozen row).
- Or save directly to the database via the **Database** page.
""")

    # ── Record types ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## Record Types")
    tc, pc = st.columns(2)
    with tc:
        st.markdown("### Ticket Records *(key = Ticket No.)*")
        st.markdown("""
| Code | Name |
|------|------|
| `18` | TkDocument |
| `19` | TkCoupon |
| `20` | TkTax |
| `21` | TkTaxDetail |
| `22` | TkPayment |
| `23` | TktRemark |
| `25` | TkDocumentHistory |
| `26` | TktCouponHistory |
| `27` | TkEndorsement |
| `29` | TkProRation |
""")
    with pc:
        st.markdown("### PNR Records *(key = PNR → Ticket)*")
        st.markdown("""
| Code | Name |
|------|------|
| `00` | Res — PNR header |
| `01` | ResFlight |
| `04` | ResPassengerFT |
| `05` | ResRemarks |
| `07` | ResPaxDoc |
| `08` | ResSuspDocAgmt |
| `11` | ResPassenger |
| `16` | ResODFlight |
| `28` | ResDataIndex |
""")

    # ── CouponStatus ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## CouponStatus Codes")
    statuses = [
        ("CTRL", "Controlled", "Ticket issued but **not yet flown**.",  "#1a73e8"),
        ("USED", "Used",       "Coupon has been **flown / lifted**.",    "#34a853"),
        ("OPEN", "Open",       "No specific flight assigned yet.",       "#9aa0a6"),
        ("VOID", "Void",       "Ticket **cancelled** before use.",       "#ea4335"),
        ("RFND", "Refunded",   "Fare **refunded** to passenger.",        "#f9ab00"),
        ("EXCH", "Exchanged",  "Ticket **exchanged** for another.",      "#fa7b17"),
    ]
    cs_cols = st.columns(3)
    for i, (code, name, desc, color) in enumerate(statuses):
        with cs_cols[i % 3]:
            st.markdown(
                f"""<div style="border:1px solid #dde;border-radius:10px;padding:14px 16px;
                margin-bottom:10px;background:#fafbff;">
                <span style="display:inline-block;width:13px;height:13px;border-radius:50%;
                background:{color};margin-bottom:6px;vertical-align:middle;"></span>
                <code style="font-size:14px;font-weight:700;">{code}</code>
                <span style="font-size:13px;font-weight:600;color:#333;margin-left:6px;">{name}</span>
                <p style="font-size:12px;color:#555;margin-top:6px;margin-bottom:0;">{desc}</p>
                </div>""",
                unsafe_allow_html=True,
            )

    # ── Output columns ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 44 Output Columns")
    st.markdown("""
`PrimaryDocNbr` · `PNRCreateDate` · `VCRCreateDate` · `Airline` · `Country` · `City` · `PCC` ·
`AgentSine` · `CouponStatus` · `ClassOfService` · `FltNo` · `OperatingFlightNbr` ·
`MarketingAirlineCode` · `OperatingAirlineCode` · `Sector` · `Fare` · `CreateIATANr` ·
`CustomerFullName` · `BookingCode` · `FareBasisCode` · `TourCode` · `CouponSeqNbr` ·
`SegmentTypeCode` · `ServiceStartDate` · `ServiceStartTime` · `ServiceEndDate` ·
`ServiceEndTime` · `FlownFlightNbr` · `FlownServiceStartDate` · `FlownServiceStartCity` ·
`FlownServiceEndCity` · `FlownClassOfService` · `FlownFlightOrigDate` · `ServiceStartCity` ·
`ServiceEndCity` · `OD` · `Kind` · `Origin` · `Destination` · `CountryName` ·
`RegionName` · `Nationality` · `NationalName` · `TTYAirlineCode`
""")
