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

# --- DARK MODE TOGGLE ---
# We place this in a small container at the top
col_t1, col_t2 = st.columns([8, 1])
with col_t2:
    is_dark = st.toggle("🌙 Dark Mode", value=False)

# --- THEME COLORS ---
if is_dark:
    # Dark Mode Palette
    BG_COLOR = "#0E1117"
    TEXT_COLOR = "#FAFAFA"
    CARD_BG = "#262730"
    HEADER_BG = "#162055" # Keep Navy for brand identity
    SUBTEXT = "#B0B0B0"
    BORDER_COLOR = "#444444"
else:
    # Light Mode Palette (Original)
    BG_COLOR = "#F4F5F7"
    TEXT_COLOR = "#162055"
    CARD_BG = "#FFFFFF"
    HEADER_BG = "#162055"
    SUBTEXT = "#AAB0D6"
    BORDER_COLOR = "#DDDDDD"

# --- DYNAMIC CSS INJECTION ---
st.markdown(f"""
    <style>
        /* Main Background */
        .stApp {{
            background-color: {BG_COLOR};
            color: {TEXT_COLOR};
        }}
        
        /* Custom Header */
        .custom-header {{
            background-color: {HEADER_BG};
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
        }}
        
        /* Text Overrides for Streamlit Elements */
        h1, h2, h3, .stRadio label, .stToggle label, .stFileUploader label {{
            color: {TEXT_COLOR} !important;
            font-family: 'Segoe UI', sans-serif;
        }}
        
        /* Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background-color: {CARD_BG};
            border-radius: 5px;
            padding: 10px 20px;
            font-weight: bold;
            color: {TEXT_COLOR};
            border: 1px solid {BORDER_COLOR};
        }}
        .stTabs [aria-selected="true"] {{
            background-color: #2962FF !important;
            color: white !important;
            border: none;
        }}

        /* Buttons (Rapyd Blue) */
        .stButton>button {{
            background-color: #2962FF;
            color: white;
            border-radius: 6px;
            font-weight: 600;
            border: none;
            padding: 0.5rem 1rem;
            width: 100%;
        }}
        .stButton>button:hover {{
            background-color: #1E4FCC;
        }}

        /* Expander / Cards */
        .streamlit-expanderHeader {{
            background-color: {CARD_BG};
            color: {TEXT_COLOR};
            border-radius: 5px;
        }}
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
    # We use f-strings to inject the dynamic colors into the HTML block
    st.markdown(f"""
        <div style='background-color: {HEADER_BG}; padding: 15px; border-radius: 8px;'>
            <h1 style='color: white; margin:0; font-size: 28px;'>Support Console Assistant</h1>
            <p style='color: #AAB0D6; margin:0; font-size: 14px;'>Web Edition v5.2 | Dark Mode Supported</p>
        </div>
    """, unsafe_allow_html=True)

st.write("") # Spacer

# --- HELPER: GMT PARSER ---
def get_gmt_timestamp(row):
    try:
        if 'Timestamp ns' in row and pd.notnull(row['Timestamp ns']):
            val = str(row['Timestamp ns']).strip().lstrip('_')
            return float(val) / 1e9
        
        if 'Date' in row and 'Time' in row and pd.notnull(row['Date']):
            dt_str = f"{row['Date']} {row['Time']}"
            return pd.to_datetime(dt_str).timestamp()
            
        if 'Time' in row and pd.notnull(row['Time']):
            return pd.to_datetime(str(row['Time'])).timestamp()
    except: pass
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
            st.caption("Auto-detects 'Timestamp ns' or 'Date' columns.")

    uploaded_files = st.file_uploader("Drop your files here (CSV, XLSX, LOG, TXT)", accept_multiple_files=True)

    if uploaded_files and st.button("🚀 Extract Tokens"):
        all_results = []
        prefix = token_mode.lower() if token_mode != "Custom" else custom_val
        pattern = re.compile(re.escape(prefix) + r"[a-fA-F0-9]{32}")
        
        my_bar = st.progress(0, text="Processing...")

        for i, uploaded_file in enumerate(uploaded_files):
            fname = uploaded_file.name.lower()
            try:
                # --- STRUCTURED (CSV / EXCEL) ---
                df = None
                if fname.endswith('.csv'):
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file)
                elif fname.endswith('.xlsx'):
                    uploaded_file.seek(0)
                    df = pd.read_excel(uploaded_file)
                
                if df is not None:
                    for idx, row in df.iterrows():
                        row_str = row.astype(str).str.cat(sep=' ')
                        matches = pattern.findall(row_str)
                        if matches:
                            ts = get_gmt_timestamp(row) if include_time else 0
                            for m in matches:
                                all_results.append({'token': m, 'ts': ts, 'source': uploaded_file.name})

                # --- UNSTRUCTURED (TXT / LOG) ---
                else:
                    uploaded_file.seek(0)
                    content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
                    for line in content.splitlines():
                        matches = pattern.findall(line)
                        if matches:
                            ts = 0
                            if include_time:
                                time_match = re.search(r"(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})", line)
                                if time_match:
                                    try: ts = pd.to_datetime(time_match.group(1)).timestamp()
                                    except: pass
                            for m in matches:
                                all_results.append({'token': m, 'ts': ts, 'source': uploaded_file.name})

            except Exception as e:
                st.error(f"Error parsing {uploaded_file.name}: {e}")
            
            my_bar.progress((i + 1) / len(uploaded_files))
        my_bar.empty()

        # --- OUTPUT ---
        if all_results:
            results_df = pd.DataFrame(all_results)
            
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
            df['_sort_ts'] = df.apply(get_gmt_timestamp, axis=1)
            df = df.sort_values(by='_sort_ts', ascending=False)
            
            df['GMT_Debug'] = pd.to_datetime(df['_sort_ts'], unit='s', utc=True).dt.strftime('%H:%M:%S')
            df = df.drop(columns=['_sort_ts'])
            
            st.dataframe(df.head(100), use_container_width=True)
            
            csv_output = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Sorted Log", 
                csv_output, 
                file_name=f"{log_file.name.split('.')[0]}_sorted_GMT.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"Failed to process log: {e}")
