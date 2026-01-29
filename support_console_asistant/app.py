import streamlit as st
import pandas as pd
import re
import zipfile
import io
from datetime import datetime, timezone
from PIL import Image

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Support Console Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS FOR RAPYD LOOK ---
st.markdown("""
    <style>
    .main { background-color: #F4F5F7; }
    .stButton>button { background-color: #2962FF; color: white; font-weight: bold; border-radius: 8px; border: none; padding: 0.5rem 2rem; }
    .stButton>button:hover { background-color: #1E4FCC; color: white; }
    h1, h2, h3 { color: #162055; font-family: 'Segoe UI', sans-serif; }
    .stRadio > label { font-weight: bold; color: #162055; }
    .css-1aumxhk { background-color: #162055; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
col1, col2 = st.columns([1, 6])
with col1:
    # Try to load logo if exists, else skip
    try:
        image = Image.open("rapyd_logo.png")
        st.image(image, width=150)
    except:
        st.write("🔷")
with col2:
    st.title("Support Console Assistant")
    st.caption("Internal Productivity Suite | v5.0 Web Edition")

# --- TABS ---
tab1, tab2 = st.tabs(["⚡ Token Extractor", "🕒 Log Time Sorter"])

# ==========================================
# TAB 1: TOKEN EXTRACTOR
# ==========================================
with tab1:
    st.subheader("1. Extraction Rules")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        token_mode = st.radio("Search Pattern:", ["payout_", "payment_", "Custom"], horizontal=True)
    with c2:
        custom_val = st.text_input("Custom Prefix:", value="inv_", disabled=(token_mode != "Custom"))
    with c3:
        include_time = st.toggle("Include GMT Timestamp")

    st.subheader("2. Upload Data")
    uploaded_files = st.file_uploader("Upload Files (CSV, TXT, LOG, XLSX)", accept_multiple_files=True)

    if uploaded_files and st.button("Extract Tokens"):
        all_tokens = []
        
        # Determine Prefix
        prefix = token_mode.lower() if token_mode != "Custom" else custom_val
        pattern = re.compile(re.escape(prefix) + r"[a-fA-F0-9]{32}")
        
        progress_bar = st.progress(0)
        
        for idx, uploaded_file in enumerate(uploaded_files):
            content = ""
            file_type = uploaded_file.name.split('.')[-1].lower()
            
            try:
                # READ TEXT/CSV/LOG
                if file_type in ['txt', 'csv', 'log', 'json']:
                    stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8", errors="ignore"))
                    content = stringio.read()
                
                # READ EXCEL (XLSX) - Extracting XML data from zip
                elif file_type == 'xlsx':
                    with zipfile.ZipFile(uploaded_file) as z:
                        for name in z.namelist():
                            if name.endswith('.xml'):
                                with z.open(name) as f:
                                    content += f.read().decode("utf-8", errors="ignore") + " "
                                    
                # FIND MATCHES
                matches = pattern.findall(content)
                
                # Timestamp Logic (Simple Line Search for Text files)
                if include_time:
                    # Reread strictly for line-by-line timestamping
                    if file_type in ['txt', 'csv', 'log']:
                        uploaded_file.seek(0)
                        stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8", errors="ignore"))
                        for line in stringio:
                            line_matches = pattern.findall(line)
                            if line_matches:
                                # Look for YYYY-MM-DD HH:MM:SS pattern
                                time_match = re.search(r"(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})", line)
                                ts_str = time_match.group(1) if time_match else "Unknown Time"
                                for m in line_matches:
                                    all_tokens.append({"token": m, "time": ts_str})
                    else:
                        # Fallback for binary/excel (No timestamp support in simple regex mode)
                        for m in matches:
                            all_tokens.append({"token": m, "time": "Unknown"})
                else:
                    for m in matches:
                        all_tokens.append({"token": m})

            except Exception as e:
                st.error(f"Error reading {uploaded_file.name}: {e}")
            
            progress_bar.progress((idx + 1) / len(uploaded_files))

        # DEDUPLICATE & DISPLAY
        if all_tokens:
            df = pd.DataFrame(all_tokens)
            
            if include_time:
                # Sort Descending (if timestamps exist)
                df = df.sort_values(by="time", ascending=False).drop_duplicates(subset=["token"])
                result_text = df.to_csv(index=False, header=False, sep="|")
            else:
                # Simple List
                unique_tokens = sorted(list(set(df["token"])))
                result_text = "\n".join(unique_tokens)

            st.success(f"Found {len(df)} unique tokens!")
            st.text_area("Results", result_text, height=200)
            
            st.download_button("Download .txt", result_text, file_name="extracted_tokens.txt")
        else:
            st.warning("No tokens found.")

# ==========================================
# TAB 2: LOG SORTER
# ==========================================
with tab2:
    st.info("Upload a CSV log to sort it by Time (Descending) and convert to GMT.")
    
    log_file = st.file_uploader("Upload CSV Log", type=["csv"])
    
    if log_file:
        try:
            df = pd.read_csv(log_file)
            
            # PARSING LOGIC
            def parse_gmt(row):
                # 1. Timestamp ns
                if 'Timestamp ns' in row and pd.notnull(row['Timestamp ns']):
                    try: 
                        val = str(row['Timestamp ns']).strip().lstrip('_')
                        return float(val) / 1e9
                    except: pass
                
                # 2. Date + Time
                if 'Date' in row and 'Time' in row:
                    try:
                        dt_str = f"{row['Date']} {row['Time']}"
                        # Simple conversion: Assume IL Time (GMT+2/3) -> GMT
                        # For web app simplicity, we'll use pandas efficient conversion if possible
                        # or just naive timestamp
                        return pd.to_datetime(dt_str).timestamp()
                    except: pass
                
                # 3. Time only
                if 'Time' in row:
                    try: return pd.to_datetime(str(row['Time'])).timestamp()
                    except: pass
                return 0.0

            if st.button("Sort & Convert"):
                # Apply Sorting
                df['_sort_key'] = df.apply(parse_gmt, axis=1)
                df = df.sort_values(by='_sort_key', ascending=False)
                
                # Update Display Columns to GMT
                # (This is a simplified logic for the web demo)
                df['Date'] = pd.to_datetime(df['_sort_key'], unit='s').dt.date
                df['Time'] = pd.to_datetime(df['_sort_key'], unit='s').dt.time
                
                # Drop helper
                df = df.drop(columns=['_sort_key'])
                
                st.dataframe(df.head(50)) # Preview
                
                # Download
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Sorted CSV",
                    data=csv_data,
                    file_name=f"{log_file.name.split('.')[0]}_sorted_GMT.csv",
                    mime="text/csv"
                )
                
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")