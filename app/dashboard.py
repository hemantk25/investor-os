from pathlib import Path

import streamlit as st

from app import mapping, parser, prices, theme
from app import portfolio as pmod

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
HOLDINGS = DATA / "holdings.xlsx"

st.set_page_config(page_title="Investor OS — Paresh Karia", page_icon="◈", layout="wide")
theme.inject()


def _mtime(p: Path) -> float:
    return p.stat().st_mtime if p.exists() else 0.0


@st.cache_data(show_spinner="Reading holdings…")
def _load(mtime: float, extras_mtime: float):
    pr = parser.parse_holdings(HOLDINGS)
    isin_map = mapping.ensure_map(DATA)
    symbols = [isin_map.get(h.isin) for h in pr.holdings]
    quotes = prices.fetch_quotes([s for s in symbols if s])
    extras = pmod.load_extras(DATA / "extras.json")
    return pr, isin_map, quotes, extras


def load_portfolio():
    if not HOLDINGS.exists():
        return None
    pr, isin_map, quotes, extras = _load(_mtime(HOLDINGS), _mtime(DATA / "extras.json"))
    return pmod.build_portfolio(pr, isin_map, quotes, extras)


def onboarding_card():
    st.markdown("### 📂 No holdings file yet")
    st.markdown(
        f"1. Log in to **ICICI Direct** → Portfolio → download the holdings Excel (all members).\n"
        f"2. Save/drag it here as: `{HOLDINGS}`\n"
        f"3. Press **R** (or the ⟳ button top-right) to reload.")
    st.caption("The dashboard reads the member sheets (PK / CK / NK / DK) automatically.")


def member_selector(members: list[str]) -> str | None:
    choice = st.segmented_control("Member", ["All"] + members, default="All",
                                  label_visibility="collapsed")
    return None if choice in (None, "All") else choice


def view_overview():
    pf = load_portfolio()
    if pf is None:
        onboarding_card()
        return
    member = member_selector(pf.members)
    t = pf.totals(member)
    cons = pf.consolidated(member)
    live = sum(1 for c in cons if c.price_live)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", pmod.fmt_short(t.total_value), pmod.fmt_inr(t.total_value),
              delta_color="off")
    c2.metric("Unrealised P/L", pmod.fmt_short(t.pl),
              (pmod.fmt_pct(t.pl_pct) + " on known cost") if t.pl_pct is not None else "—")
    c3.metric("Day P/L", pmod.fmt_short(t.day_pl), pmod.fmt_pct(t.day_pl_pct))
    c4.metric("Equity / Extras", pmod.fmt_short(t.equity_value),
              " · ".join(f"{k} {pmod.fmt_short(v)}" for k, v in t.extras_by_class.items())
              or "no extras", delta_color="off")
    st.caption(f"Holdings file: {pf.asof:%d %b %Y %H:%M} · live prices {live}/{len(cons)} · "
               f"{'member ' + member if member else 'all members'}")
    left, right = st.columns(2)
    with left:
        st.subheader("Allocation")
        rows = [{"Bucket": "Equity", "Value (₹)": round(t.equity_value)}] + \
               [{"Bucket": k.upper(), "Value (₹)": round(v)} for k, v in t.extras_by_class.items()]
        st.dataframe(rows, hide_index=True, width="stretch")
        st.subheader("Largest positions")
        for c in cons[:5]:
            st.markdown(f"**{c.name.title()}** — {pmod.fmt_short(c.value)}"
                        + ("" if c.price_live else " <span class='stale-badge'>stale</span>"),
                        unsafe_allow_html=True)
    with right:
        st.subheader("Top movers today")
        movers = pf.movers(member)
        if not movers:
            st.caption("No live day-change data yet.")
        for c in movers:
            cls = "up" if (c.day_pct or 0) >= 0 else "down"
            st.markdown(f"{c.name.title()} — <span class='{cls}'>{pmod.fmt_pct(c.day_pct)}</span>"
                        f" · {pmod.fmt_short(c.value)}", unsafe_allow_html=True)
    if pf.skipped:
        with st.expander(f"⚠ {len(pf.skipped)} rows skipped while reading the Excel "
                         "(incomplete data in the file)"):
            for s in pf.skipped:
                st.text(s)


def view_holdings():
    st.info("Holdings — coming in Task 9")


def view_rebalance():
    st.info("Rebalance — coming in Task 10")


def view_brief():
    st.info("Morning Brief — coming in Task 11")


def view_profile():
    st.info("Profile — coming in Task 12")


VIEWS = {"◈ Overview": view_overview, "▤ Holdings": view_holdings,
         "⚖ Rebalance": view_rebalance, "⚡ Morning Brief": view_brief,
         "👤 Investor Profile": view_profile}

with st.sidebar:
    st.markdown('<div class="brand">INVESTOR OS</div>', unsafe_allow_html=True)
    st.caption("Private · Paresh Karia")
    view = st.radio("View", list(VIEWS), label_visibility="collapsed")

st.title("Paresh Karia — Investor OS")
VIEWS[view]()
