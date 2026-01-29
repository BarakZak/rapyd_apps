import streamlit as st
import pandas as pd
import re
import base64
import streamlit.components.v1 as components
from datetime import datetime, timezone
import os

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Support Console Assistant",
    page_icon="⚡",
    layout="wide"
)

# --- SESSION STATE ---
if 'extracted_df' not in st.session_state:
    st.session_state.extracted_df = None
if 'sort_df' not in st.session_state:
    st.session_state.sort_df = None
if 'rec_result' not in st.session_state:
    st.session_state.rec_result = None

# --- HELPER: LOAD IMAGE AS BASE64 ---
def get_img_as_base64(file_path):
    """Reads an image file and converts it to base64 for HTML embedding."""
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

# Try to load local logo
logo_b64 = get_img_as_base64("rapyd_logo.png")

# Fallback SVG Logo (A cool "Shield/Bolt" icon if image is missing)
fallback_svg = """
<svg width="60" height="60" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M12 2L2 7L4 17C4 17 6 22 12 22C18 22 20 17 20 17L22 7L12 2Z" fill="white" fill-opacity="0.2"/>
<path d="M12 6L14.5 11H19L11 18L13 13H8L12 6Z" fill="#00E5FF"/>
</svg>
"""

# Determine what to show
if logo_b64:
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height: 70px; margin-right: 25px;">'
else:
    logo_html = f'<div style="margin-right: 20px;">{fallback_svg}</div>'

# --- CSS STYLES ---
st.markdown("""
    <style>
        /* MODERN GRADIENT HEADER */
        .modern-header {
            background: linear-gradient(135deg, #0b133b 0%, #1a237e 100%);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 25px;
            color: white;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            border-bottom: 4px solid #00E5FF; /* Cyan Accent */
        }
        .modern-header h1 {
            color: white !important;
            margin: 0;
            font-family: 'Segoe UI', sans-serif;
            font-weight: 600;
            font-size: 2.2rem;
            letter-spacing: 0.5px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .modern-header p { 
            color: #82B1FF; /* Light Blue Text */
            margin: 5px 0 0 0; 
            font-size: 1rem;
            font-weight: 500;
        }
        
        /* UNIFIED BUTTON STYLING */
        div.stButton > button {
            background-color: #162055; 
            color: white;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            height: 45px; 
            width: 100%;
            margin-top: 0px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        div.stButton > button:hover {
            background-color: #293885; /* Lighter Navy */
            color: white;
            border-color: #00E5FF; /* Cyan Glow on Hover */
            transform: translateY(-1px);
        }
        div.stButton > button:active {
            background-color: #0b1030;
            transform: translateY(1px);
        }
    </style>
""", unsafe_allow_html=True)

# --- HEADER RENDER ---
# We inject the logo DIRECTLY into the HTML block for perfect alignment
st.markdown(f"""
    <div class="modern-header">
        {logo_html}
        <div>
            <h1>Support Console Assistant</h1>
            <p>Web Edition v6.9 | <span style="color:#00E5FF;">●</span> System Online</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- HELPER: COPY BUTTON ---
def copy_to_clipboard_button(text, label="Copy to Looker"):
    b64_text = base64.b64encode(text.encode()).decode()
    html_code = f"""
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 0; overflow: hidden; }}
        .copy-btn {{
            background-color: #162055;
            color: white;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 0px 10px;
            font-family: "Source Sans Pro", sans-serif;
            font-size: 14px;
            font-weight: 600;
            height: 45px; 
            width: 100%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .copy-btn:hover {{ 
            background-color: #293885; 
            border-color: #00E5FF;
        }}
        .copy-btn:active {{ background-color: #0b1030; }}
    </style>
    </head>
    <body>
        <button class="copy-btn" onclick="copyText()">📋 {label}</button>
        <script>
            function copyText() {{
                const text = atob("{b64_text}");
                navigator.clipboard.writeText(text).then(function() {{
                    const btn = document.querySelector('.copy-btn');
                    btn.innerHTML = "✅ Copied!";
                    btn.style.backgroundColor = "#00C853";
                    btn.style.borderColor = "#00C853";
                    setTimeout(() => {{ 
                        btn.innerHTML = "📋 {label}"; 
                        btn.style.backgroundColor = "#162055"; 
                        btn.style.borderColor = "rgba(255,255,255,0.1)";
                    }}, 2000);
                }}, function(err) {{ alert("Copy failed."); }});
            }}
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=45)

# --- HELPER: TIME PARSING ---
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
    try:
        if file_obj.name.endswith('.csv'):
            file_obj.seek(0)
            df = pd.read_csv(file_obj)
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
# TAB 1: TOKEN EXTRACTOR
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

    # --- RESULTS ---
    if st.session_state.extracted_df is not None and not st.session_state.extracted_df.empty:
        df_full = st.session_state.extracted_df.copy()

        st.markdown("---")
        
        c_search, c_metrics = st.columns([3, 1])
        with c_search:
            search_query = st.text_input("🔍 Filter Results:", placeholder="Type to search...", key="t1_search")
        if search_query:
            df_full = df_full[df_full['token'].astype(str).str.contains(search_query, case=False)]
        with c_metrics:
            st.metric("Total Tokens", len(df_full))

        limit = 1000
        if len(df_full) > limit:
            st.warning(f"⚠️ Showing first {limit} rows only (Full data in downloads).")
            st.dataframe(df_full.head(limit), use_container_width=True, height=400, hide_index=True)
        else:
            st.dataframe(df_full, use_container_width=True, height=400, hide_index=True)

        st.markdown("### 📥 Actions")
        token_list = df_full['token'].tolist()
        looker_string = ", ".join([f"'{t}'" for t in token_list])

        b_col1, b_col2, b_col3, b_col4 = st.columns([1, 1, 1, 3])
        
        with b_col1:
            if include_time:
                txt_data = df_full.to_csv(sep='|', index=False, header=False)
            else:
                txt_data = "\n".join(token_list)
            st.download_button("Download txt file", txt_data, file_name="tokens.txt")
        with b_col2:
            csv_data = df_full.to_csv(index=False).encode('utf-8')
            st.download_button("Download csv file", csv_data, file_name="tokens.csv")
        with b_col3:
            copy_to_clipboard_button(looker_string, "Copy to Looker")

    elif st.session_state.extracted_df is not None:
        st.warning("No tokens found.")

# ==========================================
# TAB 2
# ==========================================
with tab2:
    st.info("Sort CSV logs by Time (Descending) + Auto-Convert to GMT.")
    log_file = st.file_uploader("Upload Log File", type=["csv"], key="sorter")
    if log_file and st.button("Sort File"):
        try:
            df = pd.read_csv(log_file)
            df['_sort_ts'] = df.apply(get_gmt_timestamp, axis=1)
            df = df.sort_values(by='_sort_ts', ascending=False)
            df = df.drop(columns=['_sort_ts'])
            st.session_state.sort_df = df 
        except Exception as e: st.error(f"Error: {e}")

    if st.session_state.sort_df is not None:
        st.dataframe(st.session_state.sort_df.head(1000), use_container_width=True)
        csv_output = st.session_state.sort_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download sorted csv", csv_output, file_name="sorted_log.csv", mime="text/csv")

# ==========================================
# TAB 3
# ==========================================
with tab3:
    st.markdown("### ⚖️ File Reconciler")
    c_r1, c_r2 = st.columns(2)
    with c_r1: rec_mode = st.radio("Token Pattern:", ["payout_", "payment_", "Custom"], horizontal=True, key="rec_mode")
    with c_r2: rec_custom = st.text_input("Prefix:", value="inv_", disabled=(rec_mode != "Custom"), key="rec_cust")

    col_a, col_b = st.columns(2)
    with col_a: file_a = st.file_uploader("📂 File A", key="file_a")
    with col_b: file_b = st.file_uploader("📂 File B", key="file_b")

    if file_a and file_b and st.button("Compare Files"):
        prefix = rec_mode.lower() if rec_mode != "Custom" else rec_custom
        pattern = re.compile(re.escape(prefix) + r"[a-fA-F0-9]{32}")
        tokens_a = extract_tokens_set(file_a, pattern)
        tokens_b = extract_tokens_set(file_b, pattern)
        st.session_state.rec_result = {"a": tokens_a, "b": tokens_b, "missing_in_b": tokens_a - tokens_b, "extra_in_b": tokens_b - tokens_a}

    if st.session_state.rec_result:
        res = st.session_state.rec_result
        m1, m2, m3 = st.columns(3)
        m1.metric("File A", len(res['a']))
        m2.metric("File B", len(res['b']))
        m3.metric("Match", len(res['a'].intersection(res['b'])))
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.info(f"🔹 Missing in File B ({len(res['missing_in_b'])})")
            if res['missing_in_b']:
                missing_list = list(res['missing_in_b'])
                st.dataframe(pd.DataFrame(missing_list), height=200, use_container_width=True)
                copy_to_clipboard_button(", ".join([f"'{t}'" for t in missing_list]), "Copy Missing to Looker")
        with c2:
            st.warning(f"⚠️ Extra in File B ({len(res['extra_in_b'])})")
            if res['extra_in_b']:
                st.dataframe(pd.DataFrame(list(res['extra_in_b'])), height=200, use_container_width=True)
