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
    layout="wide"
)

# --- CLEAN STYLE OVERRIDES ---
# This CSS works safely in both Light and Dark modes
st.markdown("""
    <style>
        /* Force the Rapyd Navy Header */
        .custom-header {
            background-color: #162055;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            color: white;
        }
        .custom-header h1 {
            color: white !important;
            margin: 0;
            font-family: 'Segoe UI', sans-serif;
            font-weight: 300;
        }
        .custom-header p {
            color: #AAB0D6;
            margin: 0;
        }
        
        /* Rapyd Blue Buttons */
        .stButton>button {
            background-color: #2962FF;
            color: white;
            border: none;
            width: 100%;
        }
        .stButton>button:hover {
            background-color: #1E4FCC;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
col_logo, col_title = st.columns([1, 8])

with col_logo:
    try:
        image = Image.open("rapyd_logo.png")
        st.image(image, width=110)
    except:
        st.markdown("## 🔷")

with col_title:
    st.markdown("""
        <div class="custom-header">
            <h1>Support Console Assistant</h1>
            <p>Web Edition v5.3 | Stable</p>
        </div>
    """, unsafe_allow_html=True)

# --- LOGIC: TIME PARSING ---
def get_gmt_timestamp(row):
    """
    Extracts GMT timestamp from a Pandas Row.
    Handles 'Timestamp ns' (Rapyd Logs) and 'Date'/'Time' columns.
    """
    try:
        # 1. Timestamp ns (Your specific file format)
        # It handles the leading underscore (e.g., "_1769...")
        if 'Timestamp ns' in row and pd.notnull(row['Timestamp ns']):
            val = str(row['Timestamp ns']).strip().lstrip('_')
            return float(val) / 1e9
        
        # 2. Date + Time columns
        if 'Date' in row and 'Time' in row and pd.notnull(row['Date']):
            dt_str = f"{row['Date']} {row['Time']}"
            return pd.to_datetime(dt_str).timestamp()
            
        # 3. Time column only
        if 'Time' in row and pd.notnull(row['Time']):
            return pd.to_datetime(str(row['Time'])).timestamp()
            
    except:
        pass
    return 0.0

# --- TABS ---
tab1, tab2 = st.tabs(["⚡ Token Extractor", "🕒 Log Time Sorter"])

# ==========================================
# TAB 1: TOKEN EXTRACTOR
# ==========================================
with tab1:
    with st.expander("⚙️ Extraction Rules", expanded=True):
        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            token_mode = st.radio("Pattern Type:", ["payout_", "payment_", "Custom"], horizontal=True)
        with c2:
            custom_val = st.text_input("Custom Prefix:", value="inv_", disabled=(token_mode != "Custom"))
        with c3:
            include_time = st.toggle("Include GMT Timestamp", value=True)
            st.caption("Matches tokens to the row's Time/Date.")

    uploaded_files = st.file_uploader("Drop files here (CSV, XLSX, LOG)", accept_multiple_files=True)

    if uploaded_files and st.button("🚀 Extract Tokens"):
        all_results = []
        prefix = token_mode.lower() if token_mode != "Custom" else custom_val
        pattern = re.compile(re.escape(prefix) + r"[a-fA-F0-9]{32}")
        
        my_bar = st.progress(0, text="Processing...")

        for i, uploaded_file in enumerate(uploaded_files):
            fname = uploaded_file.name.lower()
            try:
                # STRUCTURED (CSV / EXCEL)
                df = None
                if fname.endswith('.csv'):
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file)
                elif fname.endswith('.xlsx'):
                    uploaded_file.seek(0)
                    df = pd.read_excel(uploaded_file)
                
                if df is not None:
                    # Search every row
                    for idx, row in df.iterrows():
                        # Convert row to string to find token
                        row_str = row.astype(str).str.cat(sep=' ')
                        matches = pattern.findall(row_str)
                        if matches:
                            # Use the Helper Function to get time from THIS row
                            ts = get_gmt_timestamp(row) if include_time else 0
                            for m in matches:
                                all_results.append({'token': m, 'ts': ts})

                # UNSTRUCTURED (TXT / LOG)
                else:
                    uploaded_file.seek(0)
                    content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
                    for line in content.splitlines():
                        matches = pattern.findall(line)
                        if matches:
                            ts = 0
                            if include_time:
                                # Try finding YYYY-MM-DD in the text line
                                time_match = re.search(r"(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})", line)
                                if time_match:
                                    try: ts = pd.to_datetime(time_match.group(1)).timestamp()
                                    except: pass
                            for m in matches:
                                all_results.append({'token': m, 'ts': ts})

            except Exception as e:
                st.error(f"Error parsing {uploaded_file.name}: {e}")
            
            my_bar.progress((i + 1) / len(uploaded_files))
        my_bar.empty()

        # OUTPUT
        if all_results:
            results_df = pd.DataFrame(all_results)
            
            # Deduplicate & Sort
            if include_time:
                results_df = results_df.sort_values(by='ts', ascending=False)
                results_df = results_df.drop_duplicates(subset=['token'])
                results_df['GMT Time'] = results_df['ts'].apply(
                    lambda x: datetime.fromtimestamp(x, timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if x > 0 else "Unknown"
                )
                display_df = results_df[['GMT Time', 'token']].copy()
            else:
                results_df = results_df.drop_duplicates(subset=['token'])
                display_df = results_df[['token']].copy()

            st.success(f"Found {len(display_df)} unique tokens.")
            st.dataframe(display_df, use_container_width=True, height=300)
            
            # Downloads
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                if include_time:
                    txt_data = display_df.to_csv(sep='|', index=False, header=False)
                else:
                    txt_data = "\n".join(display_df['token'].tolist())
                st.download_button("💾 Download .txt", txt_data, file_name="tokens.txt")
            with c_d2:
                csv_data = display_df.to_csv(index=False).encode('utf-8')
                st.download_button("📊 Download .csv", csv_data, file_name="tokens.csv")
        else:
            st.warning("No matching tokens found.")

# ==========================================
# TAB 2: LOG SORTER
# ==========================================
with tab2:
    st.info("Sort CSV logs by Time (Descending) + Auto-Convert to GMT.")
    log_file = st.file_uploader("Upload Log File", type=["csv"], key="sorter")
    
    if log_file and st.button("Sort File"):
        try:
            df = pd.read_csv(log_file)
            
            # Use same helper function for sorting
            df['_sort_ts'] = df.apply(get_gmt_timestamp, axis=1)
            df = df.sort_values(by='_sort_ts', ascending=False)
            
            # Display readable GMT time
            df['GMT_Debug'] = pd.to_datetime(df['_sort_ts'], unit='s', utc=True).dt.strftime('%H:%M:%S')
            df = df.drop(columns=['_sort_ts'])
            
            st.dataframe(df.head(100), use_container_width=True)
            
            csv_output = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Sorted Log", csv_output, file_name=f"{log_file.name}_sorted.csv", mime="text/csv")
        except Exception as e:
            st.error(f"Failed to process log: {e}")
