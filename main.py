import streamlit as st
import io
import gc
import time
import openpyxl
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# --- WEB PAGE LAYOUT SETUP ---
st.set_page_config(page_title="Sabre Excel Converter", page_icon="✈️", layout="wide")

# ==========================================
# 🎨 CUSTOM STYLING BLOCK: LARGE UPLOAD BOX
# ==========================================
st.markdown("""
    <style>
        /* Expands the dropzone uploader area pad size dimension bounds within the sidebar frame container */
        [data-testid="stSidebar"] section[data-testid="stFileUploaderDropzone"] {
            padding: 2.5rem 1rem !important;
            min-height: 220px !important;
            border: 2px dashed #1F4E79 !important;
            background-color: rgba(31, 78, 121, 0.04) !important;
        }
        /* Style text lines inside uploader area */
        [data-testid="stSidebar"] section[data-testid="stFileUploaderDropzone"] div {
            font-size: 15px !important;
        }
    </style>
""", unsafe_allow_html=True)

# The exact 44 horizontal columns matching your master reference template schema
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

# Initialize persistent session tracking cache memory values for managing clear-all actions safely
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

# ==========================================
# 🛠️ LEFT SIDEBAR CONTROL PANEL
# ==========================================
with st.sidebar:
    st.title("⚙️ Controls")
    st.write("Manage your file uploads and engine actions here.")
    st.markdown("---")
    
    # Large Manual File Selection Box Dropzone Target View Area Instance
    uploaded_files = st.file_uploader(
        "👉 Manually Upload Sabre Files:", 
        type=["txt", "csv"], 
        accept_multiple_files=True,
        key=f"sabre_uploader_{st.session_state['uploader_key']}",
        help="Drag and Drop or Browse text files here."
    )
    
    # Clear All Button to drop cached memory and reset upload widget states instantly
    if uploaded_files:
        st.markdown("")
        if st.button("🗑️ Clear All Uploaded Files", use_container_width=True, type="secondary"):
            st.session_state["uploader_key"] += 1  # Increments state token key to instantly refresh widget views
            st.rerun()  # Forces hot reload to instantly clear memory paths
            
    st.markdown("---")
    st.caption("Sabre Engine v3.9 (Scrollable Status Box)")


# ==========================================
# 📊 MAIN DISPLAY PANEL (RIGHT SIDE)
# ==========================================
st.title("✈️ Sabre Standard Horizontal Excel Converter")
st.write("Your uploaded data will clear and format running left-to-right beneath your 44 template headers.")
st.markdown("---")

def build_standard_workbook(rows_data):
    """Compiles the horizontal sheet template in-memory using openpyxl engines."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sabre Data Report"
    
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Arial", size=10)
    left_align = Alignment(horizontal="left", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    cell_border = Border(left=Side(style='thin', color='E0E0E0'), right=Side(style='thin', color='E0E0E0'),
                         top=Side(style='thin', color='E0E0E0'), bottom=Side(style='thin', color='E0E0E0'))
    
    # Write Headers across Row 1
    for col_idx, header_name in enumerate(HEADERS_44, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = left_align
        cell.border = cell_border
        
    # Fill Data Rows from Row 2 downwards
    for row_idx, columns in enumerate(rows_data, start=2):
        for col_idx, header_name in enumerate(HEADERS_44, start=1):
            list_idx = col_idx - 1
            val = columns[list_idx].strip() if list_idx < len(columns) else ""
            
            if val.lower() in ["nan", "null", "undefined"]:
                val = ""
                
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = cell_border
            
            if header_name in ["PrimaryDocNbr", "Airline", "TicketNumber", "BookingCode", "PCC", "AgentSine"]:
                cell.value = val
                cell.number_format = '@'  
                cell.alignment = left_align
            elif header_name == "Fare":
                try:
                    cell.value = float(val) if val else 0.0
                except:
                    cell.value = val
                cell.number_format = '$#,##0.00'  
                cell.alignment = right_align
            else:
                cell.value = val
                cell.alignment = left_align

    ws.row_dimensions[1].height = 26
    
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 15)
        
    excel_file_buffer = io.BytesIO()
    wb.save(excel_file_buffer)
    wb.close()
    excel_file_buffer.seek(0)
    return excel_file_buffer.getvalue()


# Main operational workflow logic block execution profile
if uploaded_files:
    st.info(f"📂 Staged {len(uploaded_files)} files in left sidebar control memory.")
    
    if st.button("🚀 Start Sabre Data Analysis & Conversion", use_container_width=True):
        start_time = time.time()  
        
        with st.spinner("⏳ Analyzing data files and mapping columns... Please wait and do not click any buttons."):
            with st.status("🛠️ Running Data Pipeline...", expanded=True) as status_container:
                
                # =========================================================
                # 🔄 NEW ELEMENT: FIXED HEIGHT SCROLLABLE CONTAINER
                # =========================================================
                scroll_box = st.container(height=250)
                
                all_parsed_rows = []
                
                for idx, f in enumerate(uploaded_files):
                    if f.size == 0:
                        continue
                        
                    # All file logs are now safely contained inside the scrollable view box
                    scroll_box.write(f"⚡ Extracting data structures from: `{f.name}` ({idx+1}/{len(uploaded_files)})")
                    
                    content = f.read().decode("utf-8", errors="ignore")
                    for line in content.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                            
                        columns = line.split('|')
                        record_type = columns[0].strip()
                        
                        adjusted_row = [""] * len(HEADERS_44)
                        
                        # ==========================================
                        # ROUTE A: TRANSLATING TYPE '00' RESERVATIONS
                        # ==========================================
                        if record_type == '00':
                            doc_nbr = columns[1].strip().split('.')[0] if len(columns) > 1 else ""
                            
                            if doc_nbr and not doc_nbr.isdigit():
                                continue 
                                
                            airline = columns[4].strip().zfill(3) if len(columns) > 4 and columns[4].strip().isdigit() else columns[4].strip() if len(columns) > 4 else ""
                            
                            adjusted_row[0] = doc_nbr                                         
                            adjusted_row[1] = columns[2].strip() if len(columns) > 2 else ""  
                            adjusted_row[2] = columns[3].strip() if len(columns) > 3 else ""  
                            adjusted_row[3] = airline                                         
                            adjusted_row[4] = columns[5].strip() if len(columns) > 5 else ""  
                            adjusted_row[5] = columns[6].strip() if len(columns) > 6 else ""  
                            adjusted_row[6] = columns[7].strip() if len(columns) > 7 else ""  
                            adjusted_row[7] = columns[8].strip() if len(columns) > 8 else ""  
                            adjusted_row[8] = columns[9].strip() if len(columns) > 9 else ""  
                            adjusted_row[9] = columns[10].strip() if len(columns) > 10 else "" 
                            adjusted_row[10] = columns[11].strip() if len(columns) > 11 else "" 
                            adjusted_row[11] = columns[12].strip() if len(columns) > 12 else "" 
                            adjusted_row[12] = columns[13].strip() if len(columns) > 13 else "" 
                            adjusted_row[13] = columns[14].strip() if len(columns) > 14 else "" 
                            adjusted_row[14] = columns[15].strip() if len(columns) > 15 else "" 
                            adjusted_row[15] = columns[16].strip() if len(columns) > 16 else "" 
                            adjusted_row[16] = columns[17].strip() if len(columns) > 17 else "" 
                            adjusted_row[17] = columns[18].strip() if len(columns) > 18 else "" 
                            adjusted_row[18] = columns[19].strip() if len(columns) > 19 else "" 
                            adjusted_row[19] = columns[20].strip() if len(columns) > 20 else "" 
                            adjusted_row[20] = columns[21].strip() if len(columns) > 21 else "" 
                            adjusted_row[21] = columns[22].strip() if len(columns) > 22 else "" 
                            adjusted_row[22] = columns[23].strip() if len(columns) > 23 else "" 
                            adjusted_row[23] = columns[24].strip() if len(columns) > 24 else "" 
                            adjusted_row[24] = columns[25].strip() if len(columns) > 25 else "" 
                            adjusted_row[25] = columns[26].strip() if len(columns) > 26 else "" 
                            adjusted_row[26] = columns[27].strip() if len(columns) > 27 else "" 
                            adjusted_row[27] = columns[28].strip() if len(columns) > 28 else "" 
                            adjusted_row[28] = columns[29].strip() if len(columns) > 29 else "" 
                            adjusted_row[29] = columns[30].strip() if len(columns) > 30 else "" 
                            adjusted_row[30] = columns[31].strip() if len(columns) > 31 else "" 
                            adjusted_row[31] = columns[32].strip() if len(columns) > 32 else "" 
                            adjusted_row[32] = columns[33].strip() if len(columns) > 33 else "" 
                            adjusted_row[33] = columns[34].strip() if len(columns) > 34 else "" 
                            adjusted_row[34] = columns[35].strip() if len(columns) > 35 else "" 
                            adjusted_row[35] = columns[36].strip() if len(columns) > 36 else "" 
                            adjusted_row[36] = columns[37].strip() if len(columns) > 37 else "" 
                            adjusted_row[37] = columns[38].strip() if len(columns) > 38 else "" 
                            adjusted_row[38] = columns[39].strip() if len(columns) > 39 else "" 
                            adjusted_row[39] = columns[40].strip() if len(columns) > 40 else "" 
                            adjusted_row[40] = columns[41].strip() if len(columns) > 41 else "" 
                            adjusted_row[41] = columns[42].strip() if len(columns) > 42 else "" 
                            adjusted_row[42] = columns[43].strip() if len(columns) > 43 else "" 
                            adjusted_row[43] = columns[44].strip() if len(columns) > 44 else "" 
                            
                            all_parsed_rows.append(adjusted_row)
                            
                        # ==========================================
                        # ROUTE B: TRANSLATING TYPE '18' TICKETS
                        # ==========================================
                        elif record_type == '18':
                            ticket_number = columns[3].strip().split('.')[0] if len(columns) > 3 else ""
                            
                            if ticket_number and not ticket_number.isdigit():
                                continue 
                                
                            booking_date = columns[2].strip() if len(columns) > 2 else ""
                            airline_2letter = columns[10].strip() if len(columns) > 10 else "" 
                            pnr_code = columns[1].strip() if len(columns) > 1 else "" 
                            
                            calculated_fare = ""
                            try:
                                amt1 = float(columns[30]) if len(columns) > 30 and columns[30] else 0.0
                                amt2 = float(columns[32]) if len(columns) > 32 and columns[32] else 0.0
                                if amt1 > 0 or amt2 > 0:
                                    calculated_fare = str(amt1 + amt2)
                            except:
                                pass
                            
                            # Aligned explicit index mapping definitions for Type 18 records:
                            adjusted_row[0] = ticket_number                                        # PrimaryDocNbr (Pos 3)
                            adjusted_row[1] = booking_date                                         # PNRCreateDate
                            adjusted_row[2] = booking_date                                         # VCRCreateDate
                            adjusted_row[3] = airline_2letter                                      # Airline ('K6')
                            adjusted_row[4] = columns[16].strip() if len(columns) > 16 else ""    # Country (Pos 16)
                            adjusted_row[5] = columns[9].strip() if len(columns) > 9 else ""      # City (Pos 9)
                            adjusted_row[6] = columns[13].strip() if len(columns) > 13 else ""    # PCC (Pos 13)
                            adjusted_row[7] = columns[7].strip() if len(columns) > 7 else ""      # AgentSine (Pos 7)
                            adjusted_row[8] = columns[41].strip() if len(columns) > 41 else ""     # CouponStatus (Pos 41)
                            adjusted_row[9] = columns[42].strip() if len(columns) > 42 else ""     # ClassOfService (Pos 42)
                            adjusted_row[15] = calculated_fare if calculated_fare else columns[15].strip() if len(columns) > 15 else "" # Fare
                            adjusted_row[17] = columns[14].strip() if len(columns) > 14 else ""    # CustomerFullName (Pos 14)
                            adjusted_row[18] = pnr_code                                            # BookingCode (Pos 1)
                            adjusted_row[43] = columns[35].strip() if len(columns) > 35 else ""    # TTYAirlineCode
                            
                            all_parsed_rows.append(adjusted_row)

                scroll_box.write("🎨 Formatting Excel spreadsheet fonts and column widths...")
                excel_data_binary_bytes = build_standard_workbook(all_parsed_rows)
                status_container.update(label="✅ Data Pipeline Finished Successfully!", state="complete", expanded=False)

        elapsed_time = round(time.time() - start_time, 2)

        if not all_parsed_rows:
            st.error("❌ No valid Sabre '00' or '18' data found inside the uploaded text files.")
        else:
            st.success(f"✨ Analysis & Formatting Complete! Total Processing Time: **{elapsed_time} seconds**.")
            st.balloons()
            
            st.subheader("👀 Live Data Preview")
            st.write("Horizontal data grid mapping preview (showing first 15 records):")
            
            preview_dataframe = pd.DataFrame(all_parsed_rows, columns=HEADERS_44)
            st.dataframe(preview_dataframe.head(15), use_container_width=True)
            
            st.markdown("---")
            
            st.subheader("📥 Export Final Spreadsheet")
            st.download_button(
                label="💾 Download Processed Excel File",
                data=excel_data_binary_bytes,
                file_name="Horizontal_Master_Flight_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            del all_parsed_rows
            gc.collect()
else:
    st.info("👈 Please use the menu on the left side to upload your Sabre text files to get started!")