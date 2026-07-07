import streamlit as st

CSS = """
<style>
:root { --gold:#d4b06e; --emerald:#3ecf8e; --red:#ef6a5f; --muted:#8c99ae; --line:#232e42; }
h1, h2, h3 { font-family: Georgia, "Times New Roman", serif !important; }
.stMetric label { text-transform: uppercase; letter-spacing: .08em; font-size: 11px; }
[data-testid="stMetricValue"] { font-family: Georgia, serif; }
.up { color: var(--emerald); } .down { color: var(--red); } .muted { color: var(--muted); }
.stale-badge { color:#c98500; font-size:11px; border:1px solid #c98500; border-radius:8px; padding:0 6px; }
div[data-testid="stSidebarUserContent"] .brand { color: var(--gold); font-family: Georgia, serif;
  letter-spacing:.14em; font-size:16px; }
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
