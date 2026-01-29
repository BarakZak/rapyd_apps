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

# --- CSS: MINIMAL, ONLY HEADER ---
st.markdown("""
    <style>
        .main-header {
            background: #162055;
            padding: 20px;
            border-radius: 10px;
            color: white;
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        section[data-testid="stSidebar"] { display: none; }
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

# --- HELPER: UNIFIED BUTTON COMPONENT (Download or Copy) ---
def unified_button(text: str, label: str, button_type: str = "copy", file_data: str = None, filename: str = None):
    """Create a unified button for both download and copy actions."""
    if button_type == "download" and file_data:
        # Create download button
        b64_data = base64.b64encode(file_data.encode()).decode()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                margin: 0; 
                padding: 0; 
                overflow: hidden;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 45px;
            }}
            .btn {{
                width: 100%;
                height: 45px;
                min-height: 45px;
                background-color: #162055;
                color: white;
                border: 1px solid white;
                border-radius: 5px;
                font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                box-sizing: border-box;
                padding: 0;
            }}
            .btn:hover {{ 
                background-color: #263775; 
                border-color: #00E5FF;
            }}
            .btn:active {{ 
                background-color: #0b1030; 
                transform: translateY(1px); 
            }}
        </style>
        </head>
        <body>
            <button class="btn" onclick="download()">📥 {label}</button>
        <script>
            function download() {{
                const data = atob("{b64_data}");
                const blob = new Blob([data], {{ type: 'text/plain' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = "{filename}";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }}
        </script>
        </body>
        </html>
        """
    else:
        # Create copy button
        b64_text = base64.b64encode(text.encode()).decode()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                margin: 0; 
                padding: 0; 
                overflow: hidden;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 45px;
            }}
            .btn {{
                width: 100%;
                height: 45px;
                min-height: 45px;
                background-color: #162055;
                color: white;
                border: 1px solid white;
                border-radius: 5px;
                font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                box-sizing: border-box;
                padding: 0;
            }}
            .btn:hover {{ 
                background-color: #263775; 
                border-color: #00E5FF;
            }}
            .btn:active {{ 
                background-color: #0b1030; 
                transform: translateY(1px); 
            }}
        </style>
        </head>
        <body>
            <button class="btn" onclick="copy()">📋 {label}</button>
        <script>
            function copy() {{
                const txt = atob("{b64_text}");
                navigator.clipboard.writeText(txt).then(() => {{
                    const b = document.querySelector('.btn');
                    const originalText = b.innerText;
                    b.innerText = "✅ Copied!";
                    b.style.backgroundColor = "#00C853";
                    b.style.borderColor = "#00C853";
                    setTimeout(() => {{
                        b.innerText = originalText;
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
    
    components.html(html, height=45)

# --- JAVASCRIPT: Fix dataframe selection and force styling ---
st.markdown("""
<script>
(function() {
    function fixSelection() {
        // Remove red selection, replace with navy
        const style = document.createElement('style');
        style.textContent = `
            div[data-testid="stDataFrame"] table tbody tr[aria-selected="true"],
            div[data-testid="stDataFrame"] table tbody tr.selected {
                background-color: rgba(22, 32, 85, 0.15) !important;
            }
            div[data-testid="stDataFrame"] table tbody tr[aria-selected="true"] td,
            div[data-testid="stDataFrame"] table tbody tr.selected td {
                border: 2px solid #162055 !important;
                border-radius: 3px !important;
                background-color: rgba(22, 32, 85, 0.15) !important;
                box-shadow: 0 0 0 1px rgba(0, 229, 255, 0.3) inset !important;
                outline: none !important;
            }
            div[data-testid="stDataFrame"] * {
                outline: none !important;
            }
            div[data-testid="stDataFrame"] table tbody tr td:last-child {
                padding-right: 15px !important;
            }
        `;
        document.head.appendChild(style);
        
        // Force remove red selection on click
        document.addEventListener('click', function(e) {
            setTimeout(() => {
                const selected = document.querySelectorAll('div[data-testid="stDataFrame"] table tbody tr[aria-selected="true"] td');
                selected.forEach(td => {
                    td.style.border = '2px solid #162055';
                    td.style.backgroundColor = 'rgba(22, 32, 85, 0.15)';
                    td.style.outline = 'none';
                });
            }, 10);
        });
    }
    
    // Run immediately and on DOM changes
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixSelection);
    } else {
        fixSelection();
    }
    
    // Watch for new content
    const observer = new MutationObserver(fixSelection);
    observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
""", unsafe_allow_html=True)

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
                st.session_state.search_query = ""
            else:
                st.session_state.extracted = df[['token']].drop_duplicates()
                st.session_state.search_query = ""
        else:
            st.warning("No tokens found.")

    if st.session_state.extracted is not None:
        df = st.session_state.extracted
        
        st.write("---")
        
        # SEARCH - Truly reactive with immediate update
        search_input = st.text_input(
            "Filter Results", 
            value=st.session_state.search_query,
            key="search_input",
            placeholder="Type to filter tokens..."
        )
        
        # Update immediately - Streamlit will rerun on every keystroke
        if search_input != st.session_state.search_query:
            st.session_state.search_query = search_input
        
        # Filter
        display_df = df.copy()
        if st.session_state.search_query:
            display_df = display_df[display_df['token'].str.contains(st.session_state.search_query, case=False, na=False)]
        
        st.dataframe(display_df.head(1000), use_container_width=True, height=300)
        
        # ACTIONS - All unified custom buttons for perfect alignment
        tokens = display_df['token'].tolist()
        
        if tokens:
            c_act1, c_act2, c_act3, c_act4 = st.columns(4)
            
            with c_act1:
                unified_button("\n".join(tokens), "Download TXT", "download", "\n".join(tokens), "tokens.txt")
            with c_act2:
                unified_button(df.to_csv(index=False), "Download CSV", "download", display_df.to_csv(index=False), "tokens.csv")
            with c_act3:
                unified_button(", ".join(tokens), "Copy List", "copy")
            with c_act4:
                unified_button(", ".join([f"'{t}'" for t in tokens]), "Copy SQL Query", "copy")

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
            unified_button(", ".join(miss), "Copy Missing List", "copy")
        else:
            st.success("No missing tokens found!")
