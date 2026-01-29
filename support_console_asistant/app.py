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

# --- SESSION STATE (Persist Data) ---
if 'extracted_df' not in st.session_state:
    st.session_state.extracted_df = None
if 'sort_df' not in st.session_state:
    st.session_state.sort_df = None
if 'rec_result' not in st.session_state:
    st.session_state.rec_result = None

# --- STYLES ---
st.markdown("""
    <style>
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
        .custom-header p { color: #AAB0D6; margin: 0; }
        
        .stButton>button {
            background-color: #2962FF;
            color: white;
            border: none;
            width: 100%;
        }
        .stButton>button:hover { background-color: #1E4FCC; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
col_logo, col_title = st.columns([1, 8])
with col_logo:
    try:
        image = Image.open("rapyd_logo.png")
        st.image(image, width=110)
    except: st.markdown("## 🔷")

with col_title:
    st.markdown("""
        <div class="custom-header">
            <h1>Support Console Assistant</h1>
            <p>Web Edition v6.2 | Performance Optimized</p>
        </div>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
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

def extract_tokens_set(file_obj, pattern):
    tokens = set()
    fname = file_obj.name.lower()
    try:
        if fname.endswith('.csv'):
            file_obj.seek(0)
            df = pd.read_csv(file_obj)
            tokens.update(pattern.findall(df.astype(str).to_string()))
        elif fname.endswith('.xlsx'):
            file_obj.seek(0)
            df = pd.read_excel(file_obj)
            tokens.update(pattern.findall(df.astype(str).to_string()))
        else:
            file_obj.seek(0)
            content = file_obj.getvalue().decode("utf-8", errors="ignore")
            tokens.update(pattern.findall(content))
    except: pass
    return tokens

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["⚡ Token Extractor", "🕒 Log Time Sorter", "⚖️ Reconciler"])

# ==========================================
# TAB 1: TOKEN EXTRACTOR (OPTIMIZED)
# ==========================================
with tab1:
    with st.expander("⚙️ Extraction Rules", expanded=True):
        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            token_mode = st.radio("Pattern Type:", ["payout_", "payment_", "Custom"], horizontal=True, key="t1_mode")
        with c2:
            custom_val = st.text_input("Custom Prefix:", value="inv_", disabled=(token_mode != "Custom"), key="t1_cust")
        with c3:
            include_time = st.toggle("Include GMT Timestamp", value=True)

    uploaded_files = st.file_uploader("Drop files here", accept_multiple_files=True, key="t1_files")

    if uploaded_files and st.button("🚀 Extract Tokens", key="t1_btn"):
        all_results = []
        prefix = token_mode.lower() if token_mode != "Custom" else custom_val
        pattern = re.compile(re.escape(prefix) + r"[a-fA-F0-9]{32}")
        
        my_bar = st.progress(0, text="Processing...")

        for i, uploaded_file in enumerate(uploaded_files):
            fname = uploaded_file.name.lower()
            try:
                df = None
                if fname.endswith('.csv'):
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file)
                elif fname.endswith('.xlsx'):
                    uploaded_file.seek(0)
                    df = pd.read_excel(uploaded_file)
                
                if df is not None:
                    # Optimized Iteration
                    for idx, row in df.iterrows():
                        row_str = row.astype(str).str.cat(sep=' ')
                        matches = pattern.findall(row_str)
                        if matches:
                            ts = get_gmt_timestamp(row) if include_time else 0
                            for m in matches:
                                all_results.append({'token': m, 'ts': ts})
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
                                all_results.append({'token': m, 'ts': ts})
            except: pass
            my_bar.progress((i + 1) / len(uploaded_files))
        my_bar.empty()

        if all_results:
            res_df = pd.DataFrame(all_results)
            if include_time:
                res_df = res_df.sort_values(by='ts', ascending=False)
                res_df = res_df.drop_duplicates(subset=['token'])
                res_df['GMT Time'] = res_df['ts'].apply(
                    lambda x: datetime.fromtimestamp(x, timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if x > 0 else "Unknown"
                )
                st.session_state.extracted_df = res_df[['GMT Time', 'token']].copy()
            else:
                res_df = res_df.drop_duplicates(subset=['token'])
                st.session_state.extracted_df = res_df[['token']].copy()
        else:
            st.session_state.extracted_df = pd.DataFrame()

    # --- RESULTS (PERFORMANCE MODE) ---
    if st.session_state.extracted_df is not None and not st.session_state.extracted_df.empty:
        df_full = st.session_state.extracted_df.copy()
        total_count = len(df_full)

        st.markdown("---")
        
        # 1. Search Bar
        c_search, c_metrics = st.columns([3, 1])
        with c_search:
            search_query = st.text_input("🔍 Filter Results:", placeholder="Type to search...", key="t1_search")
        
        # Apply Search
        if search_query:
            df_full = df_full[df_full['token'].astype(str).str.contains(search_query, case=False)]
        
        with c_metrics:
            st.metric("Total Tokens", len(df_full))

        # 2. Performance Limit for Table Display
        # We only show the first 1000 rows to prevent browser crash
        limit = 1000
        if len(df_full) > limit:
            st.warning(f"⚠️ Showing first {limit} rows only (to prevent browser lag). All {len(df_full)} are included in downloads.")
            st.dataframe(df_full.head(limit), use_container_width=True, height=400, hide_index=True)
        else:
            st.dataframe(df_full, use_container_width=True, height=400, hide_index=True)

        # 3. Action Buttons
        st.markdown("### 📥 Downloads & Actions")
        
        token_list = df_full['token'].tolist()
        looker_string = ", ".join([f"'{t}'" for t in token_list])

        c_d1, c_d2, c_d3 = st.columns(3)
        
        with c_d1:
            if include_time:
                txt_data = df_full.to_csv(sep='|', index=False, header=False)
            else:
                txt_data = "\n".join(token_list)
            st.download_button("💾 Download .txt", txt_data, file_name="tokens.txt")
            
        with c_d2:
            csv_data = df_full.to_csv(index=False).encode('utf-8')
            st.download_button("📊 Download .csv", csv_data, file_name="tokens.csv")
            
        with c_d3:
            # Replaced the heavy st.code block with a simple download button
            st.download_button("📋 Download Looker / SQL", looker_string, file_name="looker_query.sql")

    elif st.session_state.extracted_df is not None:
        st.warning("No tokens found.")


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
            st.session_state.sort_df = df 
        except Exception as e:
            st.error(f"Failed to process log: {e}")

    if st.session_state.sort_df is not None:
        # Also limit sort view for performance
        st.dataframe(st.session_state.sort_df.head(1000), use_container_width=True)
        csv_output = st.session_state.sort_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Sorted CSV", csv_output, file_name="sorted_log.csv", mime="text/csv")


# ==========================================
# TAB 3: THE RECONCILER
# ==========================================
with tab3:
    st.markdown("### ⚖️ File Reconciler")
    st.info("Upload two files. We will tell you which tokens are missing.")

    c_r1, c_r2 = st.columns(2)
    with c_r1:
        rec_mode = st.radio("Token Pattern:", ["payout_", "payment_", "Custom"], horizontal=True, key="rec_mode")
    with c_r2:
        rec_custom = st.text_input("Prefix:", value="inv_", disabled=(rec_mode != "Custom"), key="rec_cust")

    col_a, col_b = st.columns(2)
    with col_a:
        file_a = st.file_uploader("📂 File A (Reference)", key="file_a")
    with col_b:
        file_b = st.file_uploader("📂 File B (Compare)", key="file_b")

    if file_a and file_b and st.button("Compare Files"):
        prefix = rec_mode.lower() if rec_mode != "Custom" else rec_custom
        pattern = re.compile(re.escape(prefix) + r"[a-fA-F0-9]{32}")
        
        tokens_a = extract_tokens_set(file_a, pattern)
        tokens_b = extract_tokens_set(file_b, pattern)
        
        st.session_state.rec_result = {
            "a": tokens_a, "b": tokens_b,
            "missing_in_b": tokens_a - tokens_b,
            "extra_in_b": tokens_b - tokens_a,
            "common": tokens_a.intersection(tokens_b)
        }

    if st.session_state.rec_result:
        res = st.session_state.rec_result
        m1, m2, m3 = st.columns(3)
        m1.metric("Total File A", len(res['a']))
        m2.metric("Total File B", len(res['b']))
        m3.metric("Common", len(res['common']))
        
        st.divider()
        c_miss, c_extra = st.columns(2)
        
        with c_miss:
            st.error(f"🚫 Missing in File B ({len(res['missing_in_b'])})")
            if res['missing_in_b']:
                missing_list = list(res['missing_in_b'])
                # Limit display for performance
                df_miss = pd.DataFrame(missing_list, columns=["Token ID"])
                st.dataframe(df_miss.head(1000), height=300, use_container_width=True)
                
                # Download for Missing
                missing_str = ", ".join([f"'{t}'" for t in missing_list])
                st.download_button("📋 Download Missing SQL", missing_str, file_name="missing_tokens.sql")
        
        with c_extra:
            st.warning(f"⚠️ Extra in File B ({len(res['extra_in_b'])})")
            if res['extra_in_b']:
                extra_list = list(res['extra_in_b'])
                df_extra = pd.DataFrame(extra_list, columns=["Token ID"])
                st.dataframe(df_extra.head(1000), height=300, use_container_width=True)
