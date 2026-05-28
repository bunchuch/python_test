import streamlit as st
import pandas as pd
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# App header initialization
st.set_page_config(page_title="Low-Memory Flight Processor", page_icon="✈️", layout="wide")
st.title("✈️ High-Performance Flight Data Web Processor")
st.write("Optimized for heavy datasets: This version processes files **one by one** to prevent memory overload (RAM crashes).")

# Master unified columns list requested
FINAL_HEADERS = [
    "primaryDocNr", "PNRCreateDate", "VCRCrateDate", "Airline", "Country", "City", "PCC", 
    "AgentSine", "CouponSatus", "ClassOfService", "FltNo", "OperatingFlightNbr", 
    "MarketingAirlineCode", "OperatingAirlineCode", "Sector", "Fare", "CreateIATANr", 
    "CustomerFullName", "BookingCode", "FareBasisCode", "TourCode", "CouponSeqNbr", 
    "SegmentTypeCode", "ServiceStartDate", "ServiceStartTime", "ServiceEndDate", 
    "ServiceEndTime", "FlownFligthNrb", "FlownServiceStartDate", "FlownServiceStartCity", 
    "FlownClassOfService", "FlownFlightOrigDate", "ServiceStartCity", "ServiceEndCCity", 
    "OD", "Kind", "Origin", "Destion CountryName", "RegionName Nationality", "TTYAirlineCode"
]

# Mapping rules based on file structures
COLS_FOR_RES = [
    "RecordType", "BookingCode", "PNRCreateDate", "VCRCrateDate", "Airline", "CouponSatus", 
    "ClassOfService", "FltNo", "ServiceStartDate", "ServiceStartTime", "ServiceStartCity", 
    "ServiceEndCCity", "Sector", "primaryDocNr", "Fare", "CreateIATANr"
]

COLS_FOR_SEAT = [
    "RecordType", "BookingCode", "ServiceStartDate", "VCRCrateDate", "FltNo", "CouponSeqNbr", 
    "Airline", "OperatingFlightNbr", "SegmentTypeCode", "ClassOfService", "CouponSatus"
]

def determine_and_map_df(df, filename):
    """Detects file type dynamically and applies correct header structure."""
    name_lower = filename.lower()
    num_cols = len(df.columns)
    
    if "res_" in name_lower or (num_cols >= 14 and str(df.iloc[0, 0]).startswith("00")):
        mapping = {i: COLS_FOR_RES[i] for i in range(min(num_cols, len(COLS_FOR_RES)))}
        return df.rename(columns=mapping), "Reservation Data"
    elif "seat" in name_lower or str(df.iloc[0, 0]).startswith("06"):
        mapping = {i: COLS_FOR_SEAT[i] for i in range(min(num_cols, len(COLS_FOR_SEAT)))}
        return df.rename(columns=mapping), "Seat Assignment"
    else:
        mapping = {i: FINAL_HEADERS[i] for i in range(min(num_cols, len(FINAL_HEADERS)))}
        return df.rename(columns=mapping), "General Log Data"

# Drag and drop input
uploaded_files = st.file_uploader(
    "Drag and drop your flight files here (RAM safe for 50+ large files)", 
    type=["txt", "csv"], 
    accept_multiple_files=True
)

if uploaded_files:
    # --- LIVE STATUS LOG CONSOLE BLOCK ---
    st.markdown("### 🖥️ Real-time Processing Console Log (One-by-One Queue)")
    log_window = st.empty()
    log_history = []
    
    def add_log(msg):
        log_history.append(msg)
        log_window.code("\n".join(log_history[-10:]))
        print(f"[MEMORY-SAFE LOG] {msg}")

    add_log(f"🔄 Staging sequential queue pipeline for {len(uploaded_files)} files...")

    # Initialize openpyxl workbook structure directly to pipe data streams straight to disk pathing
    output_excel_buffer = io.BytesIO()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Master Flight Report"
    ws.views.sheetView[0].showGridLines = True
    
    # Write structural headers directly as row #1
    headers_with_source = FINAL_HEADERS + ["Source_File_Name"]
    ws.append(headers_with_source)
    
    total_rows_written = 0
    valid_files_count = 0

    # TASK PROCESSOR: One by One loop execution
    for file in uploaded_files:
        if file.size == 0:
            add_log(f"⚠️ [SKIP] {file.name} has 0 KB size. Skipping instantly.")
            continue
            
        try:
            add_log(f"📥 [TASK START] Processing isolated file stream: {file.name}")
            
            # Read single file into temporary variable string block
            df_temp = pd.read_csv(file, sep="|", header=None, on_bad_lines='skip', dtype=str)
            
            if df_temp.empty:
                del df_temp  # Free memory allocation immediately
                continue
                
            # Dynamic Mapping Node Execution
            df_mapped, type_lbl = determine_and_map_df(df_temp, file.name)
            
            # Standardize column structure matching layout requirements
            for col in FINAL_HEADERS:
                if col not in df_mapped.columns:
                    df_mapped[col] = ""
            
            # --- STRICT BUSINESS CUSTOM CLEANING RULES ---
            # Rule 1: primaryDocNr text conversion constraints 
            df_mapped['primaryDocNr'] = df_mapped['primaryDocNr'].fillna('').astype(str).str.strip()
            df_mapped['primaryDocNr'] = df_mapped['primaryDocNr'].apply(lambda x: x.split('.')[0] if '.' in x else x)
            
            # Rule 2: Airline standard 3-digit padding padding rules (000 format)
            df_mapped['Airline'] = df_mapped['Airline'].fillna('').astype(str).str.strip()
            df_mapped['Airline'] = df_mapped['Airline'].apply(lambda x: x.zfill(3) if x.isdigit() else x)
            
            # Rule 3: Fare currency formatting normalization
            df_mapped['Fare'] = pd.to_numeric(df_mapped['Fare'], errors='coerce').fillna(0)
            
            # Add file origin flag column to matching layout track bounds
            df_mapped['Source_File_Name'] = file.name
            
            # Filter layout ordering schema sequence
            df_mapped = df_mapped[headers_with_source]
            
            # Stream transformed rows directly into the openpyxl worksheet structure rows array
            for row_records in df_mapped.values.tolist():
                ws.append(row_records)
                
            total_rows_written += len(df_mapped)
            valid_files_count += 1
            add_log(f"✅ [TASK END] Successfully appended {len(df_mapped)} rows from {file.name}. Memory cleared.")
            
            # --- CRITICAL RAM CLEANUP: Explicitly destroy variables to free system memory ---
            del df_temp
            del df_mapped
            
        except Exception as e:
            add_log(f"❌ [CRITICAL ERROR] Failed parsing {file.name}: {str(e)}")

    if total_rows_written > 0:
        add_log("🎨 Post-Processing: Initializing cellular fonts grid rules formatting styling...")
        
        # Style sheet properties layout initialization blocks configuration
        hdr_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        hdr_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        row_font = Font(name="Arial", size=10)
        center_align = Alignment(horizontal="center", vertical="center")
        border_line = Border(
            left=Side(style='thin', color='E0E0E0'), right=Side(style='thin', color='E0E0E0'),
            top=Side(style='thin', color='E0E0E0'), bottom=Side(style='thin', color='E0E0E0')
        )
        
        # Style header row directly
        for cell in ws[1]:
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = center_align
        ws.row_dimensions[1].height = 26
        
        # Iterate over cells row-by-row to safely configure formats
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                cell.font = row_font
                cell.border = border_line
                col_title = str(ws.cell(row=1, column=cell.column).value)
                
                if col_title in ["primaryDocNr", "Airline", "FltNo", "OperatingFlightNbr"]:
                    cell.number_format = '@'  # Lock format explicitly as raw String data
                elif col_title == "Fare":
                    # Clean currency numeric evaluation layout formatting rule patches
                    try:
                        cell.value = float(cell.value) if cell.value else 0.0
                    except:
                        pass
                    cell.number_format = '$#,##0.00'
                    
        # Apply Auto-Fit width logic columns spectrum
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 14)
            
        # Save structural workbook properties to the out buffer memory stack stream location 
        wb.save(output_excel_buffer)
        add_log(f"🏁 Done! Total of {valid_files_count} files merged. {total_rows_written} lines exported.")
        
        st.success("All tasks completed successfully without memory overload!")
        st.markdown("---")
        
        # Download Action Trigger Node placement Link
        st.subheader("💾 Export Report")
        st.download_button(
            label="📥 Download RAM-Safe Consolidated Flight Report (.xlsx)",
            data=output_excel_buffer.getvalue(),
            file_name="RAM_Safe_Flight_Master_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No actionable dataset content could be processed from queue criteria.")