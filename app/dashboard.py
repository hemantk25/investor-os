import os
from pathlib import Path

import streamlit as st

from app import mapping, parser, prices, theme
from app import portfolio as pmod

BASE = Path(__file__).resolve().parent.parent
# Data folder is overridable so tests never touch the real instance data.
DATA = Path(os.environ.get("INVESTOR_OS_DATA", str(BASE / "data")))
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
    extras_sub = " · ".join(f"{k} {pmod.fmt_short(v)}" for k, v in t.extras_by_class.items())
    cards = [
        ("Total Value", pmod.fmt_short(t.total_value), pmod.fmt_inr(t.total_value), "muted"),
        ("Unrealised P/L", pmod.fmt_short(t.pl),
         (pmod.fmt_pct(t.pl_pct) + " on known cost") if t.pl_pct is not None else "—",
         "up" if t.pl >= 0 else "down"),
        ("Day P/L", pmod.fmt_short(t.day_pl), pmod.fmt_pct(t.day_pl_pct),
         "up" if t.day_pl >= 0 else "down"),
        ("Equity / Extras", pmod.fmt_short(t.equity_value), extras_sub or "no extras", "muted"),
    ]
    st.markdown('<div class="hero">' + "".join(
        f'<div class="mcard"><div class="mlbl">{lbl}</div>'
        f'<div class="mnum">{val}</div><div class="msub {cls}">{sub}</div></div>'
        for lbl, val, sub, cls in cards) + '</div>', unsafe_allow_html=True)
    st.caption(f"Holdings file: {pf.asof:%d %b %Y %H:%M} · live prices {live}/{len(cons)} · "
               f"{'member ' + member if member else 'all members'}")
    left, right = st.columns(2)
    with left:
        st.subheader("Allocation")
        rows = [{"Bucket": "Equity", "Value (₹)": round(t.equity_value)}] + \
               [{"Bucket": k.upper(), "Value (₹)": round(v)} for k, v in t.extras_by_class.items()]
        st.dataframe(rows, hide_index=True, width="stretch")
        st.subheader("Largest positions")
        rows_html = "".join(
            f"<div class='row'><b>{c.name.title()}</b> — {pmod.fmt_short(c.value)}"
            + ("" if c.price_live else " <span class='stale-badge'>stale</span>") + "</div>"
            for c in cons[:5])
        st.markdown(rows_html or "<div class='row muted'>No positions.</div>",
                    unsafe_allow_html=True)
    with right:
        st.subheader("Top movers today")
        movers = pf.movers(member)
        if not movers:
            st.markdown("<div class='row muted'>No live day-change data yet.</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("".join(
                f"<div class='row'>{c.name.title()} — "
                f"<span class='{'up' if (c.day_pct or 0) >= 0 else 'down'}'>"
                f"{pmod.fmt_pct(c.day_pct)}</span> · {pmod.fmt_short(c.value)}</div>"
                for c in movers), unsafe_allow_html=True)
    if pf.skipped:
        with st.expander(f"⚠ {len(pf.skipped)} rows skipped while reading the Excel "
                         "(incomplete data in the file)"):
            for s in pf.skipped:
                st.text(s)


def view_holdings():
    pf = load_portfolio()
    if pf is None:
        onboarding_card()
        return
    member = member_selector(pf.members)
    q = st.text_input("Search", placeholder="Filter by name or symbol…")
    cons = pf.consolidated(member)
    if q:
        ql = q.lower()
        cons = [c for c in cons if ql in c.name.lower() or ql in (c.nse_symbol or "").lower()]
    rows = []
    for c in cons:
        rows.append({
            "Stock": c.name.title(),
            "NSE": c.nse_symbol or "—",
            "Qty": c.qty,
            "Avg Cost": round(c.avg_cost, 2) if c.avg_cost else None,
            "Price": round(c.price, 2),
            "Value": round(c.value),
            "P/L %": round(c.pl_pct, 1) if c.pl_pct is not None else None,
            "Day %": round(c.day_pct, 2) if c.day_pct is not None else None,
            "Held By": " + ".join(c.held_by),
            "Flags": (("⚠cost " if (c.avg_cost is None or c.cost_partial) else "")
                      + ("" if c.price_live else "stale")).strip(),
        })
    st.dataframe(rows, hide_index=True, width="stretch",
                 column_config={"P/L %": st.column_config.NumberColumn(format="%.1f%%"),
                                "Day %": st.column_config.NumberColumn(format="%.2f%%")})
    st.caption(f"{len(rows)} positions · ⚠cost = buy price missing in ICICI export · "
               "stale = price from your Excel, not live")
    if pf.extras:
        st.subheader("Other assets (from extras.json)")
        st.dataframe([{"Member": e.member, "Asset": e.label, "Class": e.asset_class,
                       "Value": round(e.value)} for e in pf.extras
                      if member is None or e.member == member],
                     hide_index=True, width="stretch")


def view_rebalance():
    from datetime import date as _date

    from app import advisory as amod

    pf = load_portfolio()
    if pf is None:
        onboarding_card()
        return
    advp = DATA / "advisory.xlsx"
    if not advp.exists():
        st.markdown("### ⚖ No advisory report found")
        st.markdown(f"Save the *Portfolio Advisory Report* Excel as `{advp}` and reload.")
        return
    adv = amod.apply_status(amod.parse_advisory(advp), pf, DATA, _date.today())
    done = sum(1 for e in adv.exits if e.status == "DONE")
    st.caption(f"Exits: {done}/{len(adv.exits)} done · New buys: {len(adv.buys)} · "
               "auto-detected from your latest holdings; override via data/rebalance-status.json")
    tab_e, tab_b, tab_s, tab_t = st.tabs(["Exits", "New Buys", "Schedule", "Target Portfolio"])
    with tab_e:
        badge = {"DONE": "✅", "IN PROGRESS": "🔄", "PENDING": "⏳", "REVIEW": "❓"}
        st.dataframe([{"": badge.get(e.status, ""), "Stock": e.stock, "Status": e.status,
                       "Src": e.source, "Priority": e.priority, "Category": e.category,
                       "Est. Proceeds": e.proceeds, "Reason": e.reason} for e in adv.exits],
                     hide_index=True, width="stretch")
        st.caption("❓ REVIEW = couldn't match this name to a holding — set it manually in "
                   "rebalance-status.json")
    with tab_b:
        for b in adv.buys:
            st.markdown(f"**{b.stock}** ({b.sector}) — target {pmod.fmt_short(b.alloc_lo)}–"
                        f"{pmod.fmt_short(b.alloc_hi)} · deployed {pmod.fmt_short(b.current_value)}")
            st.progress(min(1.0, b.progress_pct / 100))
    with tab_s:
        for m in adv.schedule:
            st.markdown(f"**{m.label}**" + (" ← you are here" if m.is_current else ""))
            if m.exits_text:
                st.markdown(f"- Exits: {m.exits_text}")
            if m.buys_text:
                st.markdown(f"- Buys: {m.buys_text}")
    with tab_t:
        st.dataframe([{"#": t.num, "Stock": t.stock, "Sector": t.sector, "Status": t.status,
                       "Target %": t.target_pct, "CAGR": t.cagr, "Conviction": t.conviction,
                       "Thesis": t.thesis} for t in adv.targets],
                     hide_index=True, width="stretch")


def view_brief():
    from app import brief as bmod

    pf = load_portfolio()
    if pf is None:
        onboarding_card()
        return
    briefs_dir = BASE / "briefs"
    files = sorted(briefs_dir.glob("*.md"), reverse=True) if briefs_dir.exists() else []
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("⚡ Generate Morning Brief", type="primary", width="stretch"):
            try:
                with st.spinner("Claude is reading your portfolio and overnight markets… (1–3 min)"):
                    path = bmod.generate_brief(pf, BASE)
                st.success(f"Saved {path.name}")
                st.rerun()
            except bmod.BriefError as e:
                st.error(e.message)
        if not bmod.find_claude():
            st.warning("Claude CLI not detected — the button will explain the fix.")
    with col1:
        if not files:
            st.markdown("### ⚡ No briefs yet")
            st.markdown("Click **Generate Morning Brief** — Claude reads your one-pager, your "
                        "live portfolio and overnight news, and writes the brief here.")
        else:
            pick = st.selectbox("Brief date", [f.stem for f in files])
            st.markdown((briefs_dir / f"{pick}.md").read_text(encoding="utf-8"))


def view_profile():
    p = BASE / "profile" / "one-pager.md"
    if p.exists():
        st.markdown(p.read_text(encoding="utf-8"))
        st.caption(f"Source: {p} — edit the file in any editor; every brief obeys it.")
    else:
        st.markdown("### 👤 No investor one-pager yet")
        st.markdown(
            "This file makes every brief and suggestion *yours*.\n\n"
            "1. Open a new chat in Claude and paste the interview prompt "
            "(`prompts/investor-interview-prompt.md` in the repo, or ask Hemant).\n"
            "2. Answer ~20–30 min of questions (voice input is fastest).\n"
            f"3. Save the result as `{p}` and reload this page.")


VIEWS = {"◈ Overview": view_overview, "▤ Holdings": view_holdings,
         "⚖ Rebalance": view_rebalance, "⚡ Morning Brief": view_brief,
         "👤 Investor Profile": view_profile}

with st.sidebar:
    st.markdown('<div class="brand">INVESTOR OS</div>', unsafe_allow_html=True)
    st.caption("Private · Paresh Karia")
    view = st.radio("View", list(VIEWS), label_visibility="collapsed")

st.title("Paresh Karia — Investor OS")
VIEWS[view]()
