import streamlit as st

CSS = """
<style>
:root {
  --bg:#0b0f16; --panel:#121826; --panel-2:#1a2233; --line:#232e42;
  --text:#e9edf5; --muted:#8c99ae; --gold:#d4b06e; --gold-deep:#a98545;
  --emerald:#3ecf8e; --red:#ef6a5f;
}

/* ---- hide Streamlit chrome so it reads as a product, not a dev tool ---- */
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], #MainMenu, footer { display: none !important; }
[data-testid="stHeader"] { background: transparent; }
/* keep the reopen-sidebar control reachable after the sidebar is collapsed */
[data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] {
  display: flex !important; z-index: 1000; }

/* ---- surfaces ---- */
.stApp, [data-testid="stAppViewContainer"] { background: var(--bg); }
[data-testid="stMain"] .block-container { padding-top: 2.2rem; max-width: 1220px; }

body, .stApp, p, span, div, label, li, td, th { color: var(--text); }
.stCaption, [data-testid="stCaptionContainer"], small { color: var(--muted) !important; }

/* ---- typography ---- */
h1 { font-family: Georgia, "Times New Roman", serif; font-weight: 600;
     font-size: 30px; letter-spacing: .01em; }
h2 { font-family: Georgia, serif; font-size: 18px; color: var(--text); }
h3 { font-family: Georgia, serif; font-size: 16px; color: var(--gold);
     letter-spacing: .02em; margin-bottom: .4rem; }

/* ---- sidebar ---- */
[data-testid="stSidebar"] { background: var(--panel); border-right: 1px solid var(--line); }
[data-testid="stSidebar"] .block-container { padding-top: 1.4rem; }
.brand { color: var(--gold); font-family: Georgia, serif; letter-spacing: .16em;
         font-size: 17px; font-weight: 600; }

/* radio -> nav rows */
[data-testid="stSidebar"] div[role="radiogroup"] { gap: 3px; }
[data-testid="stSidebar"] div[role="radiogroup"] > label {
  display: flex; align-items: center; width: 100%; margin: 0; cursor: pointer;
  padding: 10px 14px; border-radius: 10px; color: var(--muted);
  font-size: 14px; transition: background .15s, color .15s;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
  background: var(--panel-2); color: var(--text);
}
[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none; }
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
  background: var(--panel-2); color: var(--gold); font-weight: 600;
}

/* ---- hero metric cards ---- */
.hero { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 6px 0 10px; }
.mcard { background: var(--panel); border: 1px solid var(--line);
         border-radius: 14px; padding: 16px 18px; }
.mlbl { color: var(--muted); text-transform: uppercase; letter-spacing: .09em;
        font-size: 11px; margin-bottom: 8px; }
.mnum { font-family: Georgia, serif; font-size: 26px; color: var(--text); line-height: 1.1; }
.msub { font-size: 12.5px; margin-top: 5px; }
.msub.up { color: var(--emerald); } .msub.down { color: var(--red); }
.msub.muted { color: var(--muted); }
@media (max-width: 900px) { .hero { grid-template-columns: 1fr 1fr; } }

/* list rows (movers, largest positions) */
.up { color: var(--emerald); } .down { color: var(--red); } .muted { color: var(--muted); }
.row { padding: 9px 2px; border-bottom: 1px solid var(--line); font-size: 14px; }
.row:last-child { border-bottom: none; }
.stale-badge { color: var(--gold-deep); font-size: 10.5px; border: 1px solid var(--gold-deep);
               border-radius: 8px; padding: 1px 6px; margin-left: 6px; }

/* ---- member chips (segmented control) ---- */
[data-testid="stSegmentedControl"] button { background: var(--panel);
  border: 1px solid var(--line); color: var(--muted); }
[data-testid="stSegmentedControl"] button:hover { color: var(--text); }
[data-testid="stSegmentedControl"] button[aria-checked="true"] {
  border-color: var(--gold); color: var(--gold); background: var(--panel-2); }

/* ---- tables ---- */
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; }

/* ---- tabs ---- */
[data-testid="stTabs"] button[aria-selected="true"] { color: var(--gold); }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: var(--gold); }

/* ---- primary button (Generate Morning Brief) ---- */
[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, var(--gold), var(--gold-deep));
  color: #14100a; border: none; font-weight: 650; }
[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.07); color: #14100a; }

/* ---- expander (skipped-rows panel) ---- */
[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 12px; }
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
