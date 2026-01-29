import streamlit as st
import pandas as pd
import re
import base64
import streamlit.components.v1 as components
from datetime import datetime, timezone
import os

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Support Console",
    page_icon="⚡",
    layout="wide"
)

# --- PATH SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "rapyd_logo.png")

# --- SESSION STATE ---
if 'extracted_df' not in st.session_state:
    st.session_state.extracted_df = None
if 'sort_df' not in st.session_state:
    st.session_state.sort_df = None
if 'rec_result' not in st.session_state:
    st.session_state.rec_result = None

# --- HELPER: LOGO ---
def get_img_as_base64(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

logo_b64 = get_img_as_base64(LOGO_PATH)
# If logo exists, create HTML. If not, fallback text.
logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height: 50px; margin-right: 15px;">' if logo_b64 else ''

# --- CSS (UNIFIED NAVY THEME) ---
st.markdown("""
    <style>
        /* HEADER */
        .main-header {
            background: linear-gradient(90deg, #162055 0%, #2962FF 100%);
            padding: 20px;
            border-radius: 12px;
            color: white;
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .main-header h1 {
            color: white !important;
            margin: 0;
            font-size: 1.8rem;
            font-weight: 600;
        }
        
        /* FORCE ALL STREAMLIT BUTTONS TO RAPYD NAVY */
        div.stButton > button {
            background-color: #162055 !important;
            color: white !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 8px !important;
            height: 42px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            width: 100% !important;
            transition: all 0.2s ease !important;
        }
        div.stButton > button:hover {
            background-color: #263775 !important; /* Lighter Navy on Hover */
            border-color: #00E5FF !important; /* Cyan border on hover */
            transform: translateY(-1px);
        }
        div.stButton > button:active {
            background-color: #0b1030 !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
    <div class="main-header">
        {logo_html}
        <div>
            <h1>Support Console</h1>
            <p style="margin:0; opacity:0.8; font-size:0.9rem;">v7.4 | Stable & Unified</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- HELPER: ROBUST COPY BUTTON (MATCHING NAVY) ---
def copy_btn(text, label="Copy", key_id="btn"):
    b64_text = base64.b64encode(text.encode()).decode()
    
    # HTML Button designed to match the CSS above exactly
    # Added padding: 1px to body and box-sizing to fix scrollbar overlap
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 1px; overflow: hidden; box-sizing: border-box; }}
        .btn {{
            width: 99%; /* Slight reduction to avoid edge touch */
            height: 40px; /* Slightly smaller to fit inside 42px iframe */
            background-color: #162055; /* RAPYD NAVY */
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            font-family: "Source Sans Pro", sans-serif;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }}
        .btn:hover {{ 
            background-color: #263775; 
            border-color: #00E5FF; 
        }}
        .btn:active {{ transform: scale(0.99); }}
    </style>
    </head>
    <body>
        <button class="btn" onclick="copy()">📋 {label}</button>
        <script>
            function copy() {{
                const txt = atob("{b64_text}");
                navigator.clipboard.writeText(txt).then(() => {{
                    const b = document.querySelector('.btn');
                    b.innerText = "✅ Copied!";
                    b.style.backgroundColor = "#00C853";
                    b.style.borderColor = "#00C853";
                    setTimeout(() => {{
                        b.innerText = "📋 {label}";
                        b.style.backgroundColor = "#162055";
                        b.style.borderColor = "rgba(255, 255, 255, 0.1)";
                    }}, 2000);
                }});
            }}
        </script>
    </body>
    </html>
    """
    # iframe height 45 ensures the 40px button fits with margin
    components.html(html, height=45)

# --- LOGIC ---
def get_ts(row):
    try:
        if 'Timestamp ns' in row and pd.notnull(row['Timestamp ns']):
            return float(str(row['Timestamp ns']).strip('_')) / 1e9
        if 'Date' in row and 'Time' in row:
            return pd.to_datetime(f"{row['Date']} {row['Time']}").timestamp()
    except: return 0.0

def extract(files, pattern, mode, custom):
    results = []
    prefix = mode.lower() if mode != "Custom" else custom
    pat = re.compile(re.escape(prefix) + r"[a-fA-F0-9]{32}")
    
    for f in files:
        try:
            if f.name.endswith('.csv'):
                df = pd.read_csv(f)
                for _, row in df.iterrows():
                    s = row.astype(str).str.cat(sep=' ')
                    for m in pat.findall(s):
                        results.append({'token': m, 'ts': get_ts(row)})
            else:
                content = f.getvalue().decode("utf-8", errors="ignore")
                for line in content.splitlines():
                    matches = pat.findall(line)
                    if matches:
                        ts = 0
                        results.extend([{'token': m, 'ts': ts} for m in matches])
        except: pass
    return results

# --- TABS ---
t1, t2, t3 = st.tabs(["Extract", "Sort Logs", "Reconcile"])

# TAB 1: EXTRACTOR
with t1:
    c1, c2, c3 = st.columns(3)
    mode = c1.radio("Pattern", ["payout_", "payment_", "Custom"], horizontal=True)
    cust = c2.text_input("Prefix", "inv_", disabled=mode!="Custom")
    time_on = c3.toggle("Include Time", True)
    
    files = st.file_uploader("Upload Files", accept_multiple_files=True)
    
    if files and st.button("Run Extraction"):
        res = extract(files, None, mode, cust)
        if res:
            df = pd.DataFrame(res)
            if time_on:
                df = df.sort_values('ts', ascending=False).drop_duplicates('token')
                df['Time'] = df['ts'].apply(lambda x: datetime.fromtimestamp(x, timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if x>0 else "-")
                st.session_state.extracted_df = df[['Time', 'token']]
            else:
                st.session_state.extracted_df = df[['token']].drop_duplicates()
        else:
            st.warning("No tokens found.")

    # RESTORED SEARCH BAR
    if st.session_state.extracted_df is not None:
        df = st.session_state.extracted_df
        
        st.write("---")
        
        # Search Filter
        search_q = st.text_input("🔍 Filter Results", placeholder="Type ID to search...")
        if search_q:
            df = df[df['token'].str.contains(search_q, case=False)]
            
        st.metric("Total Found", len(df))
        st.dataframe(df.head(1000), use_container_width=True, height=300)
        
        # PREPARE STRINGS
        tokens = df['token'].tolist()
        looker_str = ", ".join(tokens) # No Quotes
        sql_str = ", ".join([f"'{t}'" for t in tokens]) # With Quotes
        
        st.write("### Actions")
        
        # 4 COLUMN LAYOUT
        ac1, ac2, ac3, ac4 = st.columns(4)
        
        with ac1:
            st.download_button("💾 Download TXT", "\n".join(tokens), "tokens.txt")
        with ac2:
            st.download_button("📊 Download CSV", df.to_csv(index=False), "tokens.csv")
        with ac3:
            copy_btn(looker_str, "Copy Looker (No Quotes)")
        with ac4:
            copy_btn(sql_str, "Copy SQL (With Quotes)")

# TAB 2: SORTER
with t2:
    f = st.file_uploader("Log CSV")
    if f and st.button("Sort"):
        d = pd.read_csv(f)
        d['ts'] = d.apply(get_ts, axis=1)
        st.dataframe(d.sort_values('ts', ascending=False).drop('ts', axis=1).head(1000), use_container_width=True)

# TAB 3: RECONCILER
with t3:
    c1, c2 = st.columns(2)
    fa = c1.file_uploader("File A")
    fb = c2.file_uploader("File B")
    
    if fa and fb and st.button("Compare"):
        def get_set(f):
            try: return set(re.findall(r"(payout_|payment_|inv_)[a-f0-9]{32}", f.getvalue().decode("utf-8", errors="ignore")))
            except: return set()
        
        sa = get_set(fa)
        sb = get_set(fb)
        miss = list(sa - sb)
        
        # Changed RED (error) to BLUE (info)
        st.info(f"🔹 Missing in B: {len(miss)}")
        
        if miss:
            st.dataframe(pd.DataFrame(miss, columns=["Token"]), height=200, use_container_width=True)
            # Copy Button for Reconciler
            copy_btn(", ".join(miss), "Copy Missing (Looker)")
