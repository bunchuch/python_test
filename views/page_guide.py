import streamlit as st


def render() -> None:
    st.title(":material/menu_book: Guide")
    st.markdown("Everything you need to know about how the Sabre Master Processor works.")

    # ── How it works — 4 step cards ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("### :material/play_circle: How It Works")

    step_data = [
        ("📂", "Upload",
         "Drop one or more Sabre export files (<code>.txt</code> / <code>.dat</code> / "
         "<code>.log</code>) into the sidebar. Multiple files are merged automatically."),
        ("🔍", "Pass 1 — Build Map",
         "Scans every <b>rec18</b> and <b>rec19</b> line to build a "
         "PNR ↔ Ticket-number map used in the next pass."),
        ("🔀", "Pass 2 — Route Records",
         "Each record is dispatched to its handler. Ticket records are keyed by ticket number; "
         "PNR records are merged into all linked ticket rows."),
        ("📊", "Export",
         "The result is a flat <b>44-column</b> table. Download as a styled Excel file "
         "or save to SQLite / SQL Server."),
    ]

    c0, arr1, c1, arr2, c2, arr3, c3 = st.columns([1, 0.12, 1, 0.12, 1, 0.12, 1])
    step_cols  = [c0, c1, c2, c3]
    arrow_cols = [arr1, arr2, arr3]

    for i, (emoji, title, desc) in enumerate(step_data):
        with step_cols[i]:
            st.markdown(
                f"""
                <div style="border:1px solid #c8dff5;border-radius:12px;padding:20px 14px;
                            background:linear-gradient(150deg,#eef6ff,#f8fcff);
                            text-align:center;min-height:185px;box-sizing:border-box;">
                  <div style="font-size:28px;margin-bottom:8px;">{emoji}</div>
                  <div style="font-size:10px;font-weight:700;color:#2E86C1;
                              letter-spacing:.8px;margin-bottom:5px;">STEP {i + 1}</div>
                  <div style="font-size:13px;font-weight:700;color:#1F4E79;
                              margin-bottom:10px;">{title}</div>
                  <div style="font-size:11.5px;color:#556;line-height:1.65;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    for ac in arrow_cols:
        with ac:
            st.markdown(
                "<div style='text-align:center;padding-top:72px;"
                "font-size:20px;color:#aac;'>→</div>",
                unsafe_allow_html=True,
            )

    # ── Record types ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### :material/list_alt: Record Types")

    tc, pc = st.columns(2)

    with tc:
        with st.container(border=True):
            st.markdown("**🎫 Ticket Records** — keyed by 13-digit ticket number")
            st.markdown("""
| Code | Record Name |
|:----:|-------------|
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
        with st.container(border=True):
            st.markdown("**📋 PNR Records** — merged into all linked ticket rows")
            st.markdown("""
| Code | Record Name |
|:----:|-------------|
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
    st.markdown("### :material/label: CouponStatus Codes")

    statuses = [
        ("CTRL", "Controlled", "Ticket issued but <b>not yet flown</b>.",   "#1a73e8"),
        ("USED", "Used",       "Coupon has been <b>flown / lifted</b>.",     "#34a853"),
        ("OPEN", "Open",       "No specific flight assigned yet.",            "#9aa0a6"),
        ("VOID", "Void",       "Ticket <b>cancelled</b> before use.",         "#ea4335"),
        ("RFND", "Refunded",   "Fare <b>refunded</b> to the passenger.",      "#f9ab00"),
        ("EXCH", "Exchanged",  "Ticket <b>exchanged</b> for another.",        "#fa7b17"),
    ]

    cs_cols = st.columns(3)
    for i, (code, name, desc, color) in enumerate(statuses):
        with cs_cols[i % 3]:
            st.markdown(
                f"""
                <div style="border:1px solid #e0e4f0;border-radius:10px;
                            padding:14px 16px;margin-bottom:10px;background:#fafbff;">
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                    <span style="display:inline-block;width:12px;height:12px;border-radius:50%;
                                 background:{color};flex-shrink:0;"></span>
                    <code style="font-size:14px;font-weight:700;">{code}</code>
                    <span style="font-size:13px;font-weight:600;color:#333;">{name}</span>
                  </div>
                  <p style="font-size:12px;color:#555;margin:0;line-height:1.55;">{desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── 44 output columns ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### :material/table_chart: 44 Output Columns")

    groups = {
        "🎫 Document & Status": [
            "PrimaryDocNbr", "PNRCreateDate", "VCRCreateDate",
            "CouponStatus", "CouponSeqNbr", "Kind",
        ],
        "✈️ Airline & Agency": [
            "Airline", "TTYAirlineCode", "MarketingAirlineCode",
            "OperatingAirlineCode", "PCC", "AgentSine", "CreateIATANr",
        ],
        "🛫 Flight Segment": [
            "FltNo", "OperatingFlightNbr", "BookingCode", "ClassOfService",
            "SegmentTypeCode", "Sector",
            "ServiceStartDate", "ServiceStartTime",
            "ServiceEndDate",  "ServiceEndTime",
            "ServiceStartCity", "ServiceEndCity",
        ],
        "📍 Flown Data": [
            "FlownFlightNbr", "FlownServiceStartDate",
            "FlownServiceStartCity", "FlownServiceEndCity",
            "FlownClassOfService", "FlownFlightOrigDate",
        ],
        "💰 Fare": ["Fare", "FareBasisCode", "TourCode"],
        "👤 Passenger": ["CustomerFullName", "Nationality", "NationalName"],
        "🌍 Route & Location": [
            "Origin", "Destination", "OD",
            "City", "Country", "CountryName", "RegionName",
        ],
    }

    for group_name, cols in groups.items():
        with st.container(border=True):
            st.markdown(f"**{group_name}**")
            pills = " &nbsp;·&nbsp; ".join(
                f"<code style='font-size:12px;'>{c}</code>" for c in cols
            )
            st.markdown(
                f"<div style='line-height:2.2;'>{pills}</div>",
                unsafe_allow_html=True,
            )
