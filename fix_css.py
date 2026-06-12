import sys
import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

start_idx = code.find('def inject_global_css() -> None:')
if start_idx == -1:
    print('Could not find inject_global_css()')
    sys.exit(1)

end_idx = code.find('def main():', start_idx)

new_func = '''def inject_global_css() -> None:
    # Theme colors based on session state
    theme = st.session_state.get("theme", "dark")
    if theme == "dark":
        bg_main = "#0d0d1a"
        bg_sidebar = "linear-gradient(180deg, #0f0c29 0%, #1a1a3e 50%, #16213E 100%)"
        text_color = "#e2e8f0"
        card_bg = "rgba(108, 99, 255, 0.08)"
        card_border = "rgba(108, 99, 255, 0.25)"
        input_bg = "rgba(255,255,255,0.05)"
        input_border = "rgba(255,255,255,0.1)"
        sidebar_border = "rgba(167,139,250,0.15)"
    else:
        bg_main = "#f8fafc"
        bg_sidebar = "linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%)"
        text_color = "#1e293b"
        card_bg = "rgba(108, 99, 255, 0.04)"
        card_border = "rgba(108, 99, 255, 0.2)"
        input_bg = "rgba(0,0,0,0.03)"
        input_border = "rgba(0,0,0,0.1)"
        sidebar_border = "rgba(108, 99, 255, 0.15)"

    css = """
        <style>
        /* ── Hide default Streamlit branding ── */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        [data-testid="stToolbar"] { visibility: hidden; }

        /* ── Global font & text color ── */
        html, body, [class*="css"], .stMarkdown, .stButton, input, textarea, select {
            font-family: 'Inter', 'Segoe UI', sans-serif !important;
            color: __TEXT_COLOR__ !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: __TEXT_COLOR__ !important;
        }

        /* ── Backgrounds ── */
        [data-testid="stAppViewContainer"] {
            background: __BG_MAIN__;
        }
        [data-testid="stHeader"] {
            background: transparent;
        }
        [data-testid="stMain"] {
            background: transparent;
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background: __BG_SIDEBAR__ !important;
            border-right: 1px solid __SIDEBAR_BORDER__;
        }
        [data-testid="stSidebarNav"] a {
            color: #cbd5e1 !important;
            border-radius: 10px;
            transition: background 0.2s;
        }
        [data-testid="stSidebarNav"] a:hover {
            background: rgba(167,139,250,0.12) !important;
            color: #a78bfa !important;
        }
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: rgba(167,139,250,0.18) !important;
            color: #c4b5fd !important;
            font-weight: 700;
        }

        /* ── Buttons ── */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
            border: none !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 10px !important;
            transition: transform 0.15s, box-shadow 0.15s !important;
        }
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(124,58,237,0.45) !important;
        }
        .stButton > button[kind="secondary"] {
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            color: #e2e8f0 !important;
            border-radius: 10px !important;
        }

        /* ── Inputs ── */
        .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox div[data-baseweb] {
            background: __INPUT_BG__ !important;
            border: 1px solid __INPUT_BORDER__ !important;
            border-radius: 10px !important;
            color: __TEXT_COLOR__ !important;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: rgba(167,139,250,0.5) !important;
            box-shadow: 0 0 0 3px rgba(167,139,250,0.15) !important;
        }

        /* ── Progress bar ── */
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #7c3aed, #a78bfa) !important;
            border-radius: 99px;
        }
        .stProgress > div > div {
            background: rgba(255,255,255,0.06) !important;
            border-radius: 99px;
        }

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            padding: 4px;
            gap: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            color: #9ca3af;
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(167,139,250,0.18) !important;
            color: #a78bfa !important;
            font-weight: 700 !important;
        }

        /* ── Info/Success/Warning/Error boxes ── */
        .stAlert { border-radius: 14px !important; }

        /* ── Metrics ── */
        [data-testid="stMetric"] {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 12px;
            padding: 0.75rem 1rem;
        }

        /* ── Module tile card ── */
        .cq-card {
            background: __CARD_BG__;
            border: 1px solid __CARD_BORDER__;
            border-radius: 16px;
            padding: 1.25rem;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .cq-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 32px rgba(108, 99, 255, 0.35);
        }

        /* ── Badge image ── */
        .cq-badge-img {
            width: 80px; height: 80px;
            object-fit: contain;
            filter: drop-shadow(0 0 8px rgba(108,99,255,0.6));
        }

        /* ── Dataframe ── */
        [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
        </style>
        """
    css = css.replace("__TEXT_COLOR__", text_color)
    css = css.replace("__BG_MAIN__", bg_main)
    css = css.replace("__BG_SIDEBAR__", bg_sidebar)
    css = css.replace("__SIDEBAR_BORDER__", sidebar_border)
    css = css.replace("__INPUT_BG__", input_bg)
    css = css.replace("__INPUT_BORDER__", input_border)
    css = css.replace("__CARD_BG__", card_bg)
    css = css.replace("__CARD_BORDER__", card_border)

    st.markdown(css, unsafe_allow_html=True)

'''

final_code = code[:start_idx] + new_func + code[end_idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(final_code)
print('Updated app.py successfully.')
