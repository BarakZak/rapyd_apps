import streamlit as st
import pandas as pd
import re
import base64
import streamlit.components.v1 as components
from datetime import datetime, timezone
import os
from typing import List, Dict, Optional, Set

# --- PAGE CONFIG ---
st.set_page_config(page_title="Support Console", layout="wide")

# --- PATH SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "rapyd_logo.png")

# --- HELPER: LOGO ---
def get_img_as_base64(file_path: str) -> Optional[str]:
    """Load image file and return as base64 string."""
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()
    except Exception as e:
        st.error(f"Error loading logo: {e}")
    return None

logo_b64 = get_img_as_base64(LOGO_PATH)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height: 50px; margin-right: 15px;">' if logo_b64 else ''

# --- CSS: FORCE UNIFORMITY (NAVY) ---
st.markdown("""
    <style>
        /* MAIN HEADER */
        .main-header {
            background: #162055;
            padding: 20px;
            border-radius: 10px;
            color: white;
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        
        /* FORCE NATIVE DOWNLOAD BUTTONS TO MATCH RAPYD NAVY */
        section[data-testid="stSidebar"] { display: none; }
        
        /* Standardize ALL buttons - download buttons and custom buttons */
        div.stButton > button,
        div[data-testid="stDownloadButton"] > button {
            background-color: #162055 !important;
            color: white !important;
            border: 1px solid white !important;
            height: 45px !important;
            border-radius: 5px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            width: 100% !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        div.stButton > button:hover,
        div[data-testid="stDownloadButton"] > button:hover {
            background-color: #263775 !important;
            border-color: #00E5FF !important;
        }
        div.stButton > button:active,
        div[data-testid="stDownloadButton"] > button:active {
            background-color: #0b1030 !important;
        }
        
        /* Fix dataframe selection highlight - change red to navy and fix scrollbar overlap */
        .stDataFrame [data-testid="stDataFrame"] {
            overflow-x: auto;
        }
        
        /* Target the selected row highlight */
        div[data-testid="stDataFrame"] table tbody tr.selected,
        div[data-testid="stDataFrame"] table tbody tr:hover {
            background-color: rgba(22, 32, 85, 0.2) !important;
        }
        
        /* Fix the selection border - change from red to navy and prevent scrollbar overlap */
        div[data-testid="stDataFrame"] table tbody tr.selected td {
            border: 2px solid #162055 !important;
            border-radius: 3px;
            box-shadow: 0 0 0 1px rgba(0, 229, 255, 0.3) !important;
        }
        
        /* Ensure scrollbar doesn't overlap content */
        div[data-testid="stDataFrame"] > div {
            overflow-x: auto;
            overflow-y: auto;
        }
        
        /* Hide default red selection outline */
        div[data-testid="stDataFrame"] * {
            outline: none !important;
        }
        
        /* More specific targeting for Streamlit's selection box */
        .stDataFrame [data-testid="stDataFrame"] .stDataFrameSelectedRow {
            border: 2px solid #162055 !important;
            background-color: rgba(22, 32, 85, 0.15) !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
    <div class="main-header">
        {logo_html}
        <div>
            <h2 style="margin:0; padding:0; font-weight:600;">Support Console</h2>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- HELPER: COPY BUTTON (NO SCROLLBAR OVERLAP) ---
def copy_btn(text: str, label: str = "Copy") -> None:
    """Create a custom copy button with base64 encoded text."""
    try:
        b64_text = base64.b64encode(text.encode()).decode()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            body {{ margin: 0; padding: 2px; overflow: hidden; }}
            .btn {{
                width: 98%;
                height: 45px;
                background-color: #162055;
                color: white;
                border: 1px solid white;
                border-radius: 5px;
                font-family: "Source Sans Pro", sans-serif;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                box-sizing: border-box;
            }}
            .btn:hover {{ 
                background-color: #263775; 
                border-color: #00E5FF;
            }}
            .btn:active {{ background-color: #0b1030; transform: translateY(1px); }}
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
                            b.style.borderColor = "white";
                        }}, 2000);
                    }}).catch(err => {{
                        console.error("Copy failed:", err);
                    }});
                }}
            </script>
        </body>
        </html>
        """
        components.html(html, height=50)
    except Exception as e:
        st.error(f"Error creating copy button: {e}")

# --- STATE ---
if 'extracted' not in st.session_state:
    st.session_state.extracted = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# --- LOGIC ---
def get_ts(row: pd.Series) -> float:
    """Extract timestamp from a row, trying multiple column formats."""
    try:
        if 'Timestamp ns' in row.index and pd.notnull(row['Timestamp ns']):
            ts_str = str(row['Timestamp ns']).strip('_')
            return float(ts_str) / 1e9
        
        if 'Date' in row.index and 'Time' in row.index:
            date_val = row['Date']
            time_val = row['Time']
            if pd.notnull(date_val) and pd.notnull(time_val):
                return pd.to_datetime(f"{date_val} {time_val}").timestamp()
    except (ValueError, TypeError, KeyError):
        pass
    return 0.0

def extract(files: List, mode: str, cust: str) -> List[Dict[str, any]]:
    """Extract tokens from uploaded files based on pattern."""
    res = []
    prefix = mode.lower() if mode != "Custom" else cust
    pat = re.compile(re.escape(prefix) + r"[a-fA-F0-9]{32}", re.IGNORECASE)
    
    for f in files:
        try:
            if f.name.endswith('.csv'):
                df = pd.read_csv(f)
                for _, row in df.iterrows():
                    s = row.astype(str).str.cat(sep=' ')
                    matches = pat.findall(s)
                    for m in matches:
                        res.append({'token': m, 'ts': get_ts(row)})
            else:
                content = f.getvalue().decode("utf-8", errors="ignore")
                for line in content.splitlines():
                    matches = pat.findall(line)
                    res.extend([{'token': m, 'ts': None} for m in matches])
        except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
            st.warning(f"Error reading {f.name}: {e}")
        except Exception as e:
            st.warning(f"Unexpected error processing {f.name}: {e}")
    
    return res

# --- TABS ---
t1, t2, t3 = st.tabs(["Token Extractor", "Log Sorter", "Reconciler"])

# TAB 1
with t1:
    c1, c2, c3 = st.columns(3)
    mode = c1.radio("Pattern", ["payout_", "payment_", "Custom"], horizontal=True)
    cust = c2.text_input("Prefix", "inv_", disabled=mode != "Custom")
    time_on = c3.toggle("Include Time", True)
    
    files = st.file_uploader("Upload Files", accept_multiple_files=True)
    
    if files and st.button("Extract Tokens"):
        res = extract(files, mode, cust)
        if res:
            df = pd.DataFrame(res)
            
            if time_on:
                df_with_time = df[df['ts'].notna() & (df['ts'] > 0)].copy()
                df_no_time = df[df['ts'].isna() | (df['ts'] == 0)].copy()
                
                df_with_time = df_with_time.sort_values('ts', ascending=False)
                df_with_time = df_with_time.drop_duplicates('token', keep='first')
                
                df_with_time['Time'] = df_with_time['ts'].apply(
                    lambda x: datetime.fromtimestamp(x, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                )
                
                if not df_no_time.empty:
                    df_no_time = df_no_time[['token']].drop_duplicates()
                    df_no_time['Time'] = "-"
                    df_final = pd.concat([df_with_time[['Time', 'token']], df_no_time[['Time', 'token']]])
                else:
                    df_final = df_with_time[['Time', 'token']]
                
                st.session_state.extracted = df_final
                st.session_state.search_query = ""  # Reset search on new extraction
            else:
                st.session_state.extracted = df[['token']].drop_duplicates()
                st.session_state.search_query = ""  # Reset search on new extraction
        else:
            st.warning("No tokens found.")

    if st.session_state.extracted is not None:
        df = st.session_state.extracted
        
        st.write("---")
        # SEARCH - Real-time filtering (updates on every keystroke)
        search_query = st.text_input(
            "Filter Results", 
            value=st.session_state.search_query,
            key="search_input",
            placeholder="Type to filter tokens..."
        )
        
        # Update session state and filter immediately
        st.session_state.search_query = search_query
        
        if search_query:
            df = df[df['token'].str.contains(search_query, case=False, na=False)]
        
        st.dataframe(df.head(1000), use_container_width=True, height=300)
        
        # ACTIONS - All buttons now have consistent styling
        tokens = df['token'].tolist()
        
        if tokens:
            c_act1, c_act2, c_act3, c_act4 = st.columns(4)
            
            with c_act1:
                st.download_button(
                    "📥 Download TXT", 
                    "\n".join(tokens), 
                    "tokens.txt",
                    key="dl_txt"
                )
            with c_act2:
                st.download_button(
                    "📥 Download CSV", 
                    df.to_csv(index=False), 
                    "tokens.csv",
                    key="dl_csv"
                )
            with c_act3:
                copy_btn(", ".join(tokens), "📋 Copy List")
            with c_act4:
                copy_btn(", ".join([f"'{t}'" for t in tokens]), "📋 Copy SQL Query")

# TAB 2
with t2:
    f = st.file_uploader("Log CSV")
    if f and st.button("Sort"):
        try:
            d = pd.read_csv(f)
            d['ts'] = d.apply(get_ts, axis=1)
            sorted_df = d.sort_values('ts', ascending=False).drop('ts', axis=1).head(1000)
            st.dataframe(sorted_df, use_container_width=True)
        except pd.errors.EmptyDataError:
            st.error("The uploaded CSV file is empty.")
        except pd.errors.ParserError as e:
            st.error(f"Error parsing CSV: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

# TAB 3
with t3:
    c1, c2 = st.columns(2)
    fa = c1.file_uploader("File A")
    fb = c2.file_uploader("File B")
    if fa and fb and st.button("Compare"):
        def get_tokens(f) -> Set[str]:
            """Extract tokens from file using consistent regex pattern."""
            try:
                content = f.getvalue().decode("utf-8", errors="ignore")
                pattern = r"(payout_|payment_|inv_)[a-fA-F0-9]{32}"
                return set(re.findall(pattern, content, re.IGNORECASE))
            except Exception as e:
                st.warning(f"Error reading file: {e}")
                return set()
        
        tokens_a = get_tokens(fa)
        tokens_b = get_tokens(fb)
        miss = list(tokens_a - tokens_b)
        
        st.info(f"Missing in B: {len(miss)}")
        if miss:
            st.dataframe(pd.DataFrame(miss, columns=["Token"]), height=200, use_container_width=True)
            copy_btn(", ".join(miss), "Copy Missing List")
        else:
            st.success("No missing tokens found!")
