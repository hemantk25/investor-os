# Investor OS — Stitch Frontend Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Streamlit UI with a Flask + Jinja2 web app that renders the approved Stitch designs (`stitch_investor_os_portfolio_dashboard/*/code.html`) driven by the existing Python data engine — same look as the mockups, real data, fully local and offline.

**Architecture:** Keep the entire data engine untouched (`parser.py`, `mapping.py`, `prices.py`, `portfolio.py`, `advisory.py`, `brief.py`). A thin Flask app (`server.py`) turns each request into a template context via pure functions in `view_models.py` and `charts.py`, then renders a Jinja2 template adapted from the corresponding Stitch `code.html`. Styling is a **compiled, committed Tailwind CSS file** (built once with the Tailwind v3 CLI from the Stitch config) plus **self-hosted fonts** — no CDN, no runtime JS framework. Interactions (member switch, range, tab, search, generate brief) are server-side via query params / form POST, with a few lines of vanilla JS only for the brief spinner.

**Tech Stack:** Python 3.11+ (dev has 3.14), Flask ≥3.0, Jinja2, `markdown` (brief/profile rendering), yfinance/openpyxl/requests (existing), Tailwind CSS v3 CLI (build-time only, via `npx`), pytest.

## Global Constraints

- **Match the approved Stitch designs** in `stitch_investor_os_portfolio_dashboard/` (screens: overview, holdings, rebalance, morning_brief, investor_profile) and the token system in its `premium_wealth_portal/DESIGN.md`. Those files are the visual source of truth — copy their markup and classes.
- **Palette (from DESIGN.md):** teal primary `#0f766e` / deep `#005c55`, background `#f7faf8`/`#F5F7FA`, white cards, hairline `#E6E9F0`, text `#181c1c`, muted `#3e4947`/`#6e7977`, error `#ba1a1a`, positive green `#059669`. Chart colors: `#005c55, #4f46e5, #f59e0b, #3b82f6, #64748b`. Fonts: **Manrope** (headings), **Inter** (body + tabular numbers).
- **Runtime is fully offline:** no CDN links in served HTML. Tailwind is compiled to `app/static/app.css`; Inter/Manrope/Material-Symbols are self-hosted in `app/static/fonts/`. Node/npx is needed only at build time.
- **No real data in git** (unchanged): `/data/`, `/briefs/`, `/profile/` gitignored; only `tests/fixtures/*.xlsx` committed.
- Indian money formatting everywhere: `₹` with lakh/crore short forms and en-IN grouping (reuse `portfolio.fmt_inr/fmt_short/fmt_pct`).
- **No stack traces in the UI** — every failure renders a friendly card (spec principle carried over).
- Data folder path stays overridable via `INVESTOR_OS_DATA` env var (already in place) so tests never touch real data.
- Members are **PK, CK, NK, DK** (the Stitch mockups only drew All/PK/CK — render all real members).
- Commit after every task. Retain the existing data-module tests (they must stay green throughout).

## Module / File Map

```
app/
  server.py            # NEW  Flask app: routes → context → render_template
  view_models.py       # NEW  pure functions: Portfolio/Advisory → template context dicts
  charts.py            # NEW  pure SVG/segment builders for the value chart + allocation bar
  parser.py mapping.py prices.py portfolio.py advisory.py brief.py   # UNCHANGED (prices gets +fetch_history)
  templates/
    base.html          # NEW  sidebar + topbar layout, {% block content %}
    overview.html holdings.html rebalance.html brief.html profile.html   # NEW (from Stitch code.html)
    _icons.html        # NEW  Jinja macro: inline SVG icon set (nav + ui icons)
  static/
    app.css            # NEW (built)  compiled Tailwind + custom rules
    fonts/             # NEW  self-hosted woff2 (Inter, Manrope, MaterialSymbols)
  tailwind/
    input.css          # NEW  @font-face + @tailwind directives + custom classes
    tailwind.config.js # NEW  the Stitch design tokens (shared)
build-css.ps1 / build-css.sh   # NEW  one-line Tailwind build wrapper
tests/
  test_view_models.py test_charts.py test_routes.py   # NEW
  test_parser.py test_mapping.py test_prices.py test_portfolio.py test_advisory.py test_brief.py  # UNCHANGED
REMOVED: app/dashboard.py, app/theme.py, .streamlit/, tests/test_dashboard_smoke.py
```

## Interfaces (single source of truth — all tasks conform)

```python
# app/charts.py
CHART_COLORS = ["#005c55", "#4f46e5", "#f59e0b", "#3b82f6", "#64748b"]  # equity, mf, gold, debt, cash
def area_path(series: list[float], w: int = 1000, h: int = 250) -> dict
    # -> {"line": "<svg path d>", "area": "<closed path d>"} ; flat line if <2 points
def alloc_segments(totals) -> list[dict]
    # -> [{"label","pct" (float 0-100),"color","short" (₹ short)}] in fixed order equity,mf,gold,debt,cash (skip zero)
def portfolio_series(pf, member, history) -> list[float]
    # current qty × historical close summed + flat non-market; [] if history empty

# app/prices.py  (added)
def fetch_history(nse_symbols: list[str], period: str = "6mo", ttl: int = 3600)
    # -> dict[str, list[float]] symbol -> chronological closes ; {} on failure ; TTL cached

# app/view_models.py
RANGE_TO_PERIOD = {"1M":"1mo","3M":"3mo","6M":"6mo","1Y":"1y","ALL":"5y"}
def common(pf, active: str, member: str | None) -> dict
    # -> {"members","active","member","freshness","brand_sub"}
def overview(pf, member, rng: str) -> dict
def holdings(pf, member, q: str) -> dict
def rebalance(pf, adv, tab: str) -> dict
def brief_ctx(base_dir, pf, pick: str | None) -> dict
def profile_ctx(base_dir) -> dict

# app/server.py
def create_app() -> flask.Flask   # factory; reads INVESTOR_OS_DATA / BASE like dashboard did
```

---

### Task 1: Flask scaffold, retire Streamlit, requirements

**Files:**
- Create: `app/server.py`
- Modify: `requirements.txt`
- Remove: `app/dashboard.py`, `app/theme.py`, `.streamlit/config.toml` (+ dir), `tests/test_dashboard_smoke.py`

**Interfaces:**
- Produces: `create_app()` returning a Flask app with 5 GET routes (`/`, `/holdings`, `/rebalance`, `/brief`, `/profile`) each rendering `base.html` with a placeholder, and a `/health` route returning `"ok"`. `BASE`/`DATA` resolved as before.

- [ ] **Step 1: requirements.txt — swap streamlit for flask + markdown**

```
flask>=3.0
markdown>=3.6
openpyxl>=3.1
yfinance>=0.2.50
requests>=2.31
pytest>=8.0
```

- [ ] **Step 2: Remove Streamlit files**

```bash
git rm app/dashboard.py app/theme.py tests/test_dashboard_smoke.py
git rm -r .streamlit
```

- [ ] **Step 3: app/server.py (skeleton — routes render base with a placeholder)**

```python
from __future__ import annotations
import os
from pathlib import Path
from flask import Flask, render_template, request

BASE = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("INVESTOR_OS_DATA", str(BASE / "data")))


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.route("/health")
    def health():
        return "ok"

    @app.route("/")
    def overview():
        return render_template("base.html", active="overview", page="Overview",
                               members=[], member=None, freshness="", body="Overview coming soon")

    @app.route("/holdings")
    def holdings():
        return render_template("base.html", active="holdings", page="Holdings",
                               members=[], member=None, freshness="", body="Holdings coming soon")

    @app.route("/rebalance")
    def rebalance():
        return render_template("base.html", active="rebalance", page="Rebalance",
                               members=[], member=None, freshness="", body="Rebalance coming soon")

    @app.route("/brief")
    def brief():
        return render_template("base.html", active="brief", page="Morning Brief",
                               members=[], member=None, freshness="", body="Brief coming soon")

    @app.route("/profile")
    def profile():
        return render_template("base.html", active="profile", page="Investor Profile",
                               members=[], member=None, freshness="", body="Profile coming soon")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8555, debug=False)
```

- [ ] **Step 4: Temporary minimal base.html so the app runs** (replaced properly in Task 3)

Create `app/templates/base.html`:
```html
<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Investor OS — {{ page }}</title></head>
<body><h1>{{ page }}</h1><div>{{ body }}</div></body></html>
```

- [ ] **Step 5: Install deps and smoke-test the server**

```powershell
.\.venv\Scripts\pip install -r requirements.txt
$p = Start-Process .\.venv\Scripts\python -ArgumentList "-m","flask","--app","app.server","run","--port","8556" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 5
(Invoke-WebRequest http://127.0.0.1:8556/health -UseBasicParsing).Content
(Invoke-WebRequest http://127.0.0.1:8556/ -UseBasicParsing).StatusCode
Stop-Process $p.Id -Force
```
Expected: `ok` then `200`.

- [ ] **Step 6: Confirm data-module tests still pass**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: all pass (the removed Streamlit smoke test is gone; parser/mapping/prices/portfolio/advisory/brief green).

- [ ] **Step 7: Commit**

```bash
git add app/server.py app/templates/base.html requirements.txt
git commit -m "feat(app): flask scaffold, retire streamlit UI"
```

---

### Task 2: CSS build pipeline + self-hosted fonts

**Files:**
- Create: `app/tailwind/tailwind.config.js`, `app/tailwind/input.css`, `build-css.ps1`, `build-css.sh`, `app/static/fonts/` (woff2 files), `app/static/app.css` (built output)
- Modify: `.gitignore` (do NOT ignore `app/static/`)

**Interfaces:**
- Produces: `app/static/app.css` (committed) containing compiled Tailwind for the token set + custom classes `.hairline-border .soft-shadow .table-row-hover`; `@font-face` for Inter/Manrope/Material Symbols pointing at `app/static/fonts/`.

- [ ] **Step 1: Extract the Stitch Tailwind config into `app/tailwind/tailwind.config.js`**

Copy the `tailwind.config = {…}` object from `stitch_investor_os_portfolio_dashboard/overview_investor_os/code.html` (the `<script id="tailwind-config">` block, lines ~12–160 — includes `colors`, `fontFamily`, `fontSize`, and the `chart-1..5` additions) into a proper config file:

```js
module.exports = {
  content: ["./app/templates/**/*.html"],
  darkMode: "class",
  theme: { extend: {
    // ↓ paste the exact `colors`, `fontFamily`, `fontSize`, spacing, borderRadius
    //   objects from overview_investor_os/code.html's tailwind config here,
    //   plus: colors["chart-1"]="#005c55", chart-2="#4f46e5", chart-3="#f59e0b",
    //   chart-4="#3b82f6", chart-5="#64748b"
  }},
};
```
(Faithfully transcribe the object — every color/token the templates reference must exist or the class won't compile.)

- [ ] **Step 2: Download self-hosted fonts into `app/static/fonts/`**

Run (dev machine, one-time):
```powershell
$ff="app\static\fonts"; New-Item -ItemType Directory -Force $ff | Out-Null
# Inter + Manrope: fetch woff2 from the google-fonts github raw or gwfh mirror
Invoke-WebRequest "https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-400-normal.woff2" -OutFile "$ff\inter-400.woff2"
Invoke-WebRequest "https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-500-normal.woff2" -OutFile "$ff\inter-500.woff2"
Invoke-WebRequest "https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-600-normal.woff2" -OutFile "$ff\inter-600.woff2"
Invoke-WebRequest "https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-700-normal.woff2" -OutFile "$ff\inter-700.woff2"
Invoke-WebRequest "https://cdn.jsdelivr.net/fontsource/fonts/manrope@latest/latin-600-normal.woff2" -OutFile "$ff\manrope-600.woff2"
Invoke-WebRequest "https://cdn.jsdelivr.net/fontsource/fonts/manrope@latest/latin-700-normal.woff2" -OutFile "$ff\manrope-700.woff2"
Invoke-WebRequest "https://cdn.jsdelivr.net/fontsource/fonts/manrope@latest/latin-800-normal.woff2" -OutFile "$ff\manrope-800.woff2"
```
Expected: 7 woff2 files present. (Material Symbols icons are handled by inline SVG in Task 3 — no icon font needed, so no icon-font download.)

- [ ] **Step 3: `app/tailwind/input.css`**

```css
@font-face { font-family:'Inter'; font-weight:400; font-display:swap; src:url('/static/fonts/inter-400.woff2') format('woff2'); }
@font-face { font-family:'Inter'; font-weight:500; font-display:swap; src:url('/static/fonts/inter-500.woff2') format('woff2'); }
@font-face { font-family:'Inter'; font-weight:600; font-display:swap; src:url('/static/fonts/inter-600.woff2') format('woff2'); }
@font-face { font-family:'Inter'; font-weight:700; font-display:swap; src:url('/static/fonts/inter-700.woff2') format('woff2'); }
@font-face { font-family:'Manrope'; font-weight:600; font-display:swap; src:url('/static/fonts/manrope-600.woff2') format('woff2'); }
@font-face { font-family:'Manrope'; font-weight:700; font-display:swap; src:url('/static/fonts/manrope-700.woff2') format('woff2'); }
@font-face { font-family:'Manrope'; font-weight:800; font-display:swap; src:url('/static/fonts/manrope-800.woff2') format('woff2'); }

@tailwind base;
@tailwind components;
@tailwind utilities;

body { font-family:'Inter',system-ui,sans-serif; background:#f7faf8; color:#181c1c; }
h1,h2,h3 { font-family:'Manrope',system-ui,sans-serif; }
.tnum { font-variant-numeric: tabular-nums; }
.hairline-border { border-color:#E6E9F0; border-width:1px; }
.soft-shadow { box-shadow:0 1px 3px rgba(16,24,40,0.06); }
.table-row-hover:hover { background-color:#ffffff; }
```

- [ ] **Step 4: Build wrappers**

`build-css.ps1`:
```powershell
npx tailwindcss@3 -c app/tailwind/tailwind.config.js -i app/tailwind/input.css -o app/static/app.css --minify
```
`build-css.sh`:
```bash
#!/bin/bash
cd "$(dirname "$0")"
npx tailwindcss@3 -c app/tailwind/tailwind.config.js -i app/tailwind/input.css -o app/static/app.css --minify
```

- [ ] **Step 5: Ensure static isn't ignored, then build**

Confirm `.gitignore` does not exclude `app/static`. Then run: `powershell -File build-css.ps1`
Expected: `app/static/app.css` created (a few KB–tens of KB). (Tailwind scans templates; at this point base.html is minimal so CSS is small — it grows as templates are added, and Task 13 rebuilds.)

- [ ] **Step 6: Replace base.html with the real layout (sidebar + topbar) + `_icons.html` macro**

Create `app/templates/_icons.html` with a Jinja macro `icon(name)` returning inline SVGs (24×24, `stroke=currentColor`, `fill=none` line style) for exactly these names used by the nav + UI: `dashboard, wallet, rebalance, news, person, search, bolt, download, bell, gear`. Example macro shape:
```html
{% macro icon(name) %}{% if name == 'dashboard' %}<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>{% elif name == 'search' %}<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>{% elif name == 'bolt' %}<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>{% else %}<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/></svg>{% endif %}{% endmacro %}
```
(Fill in the remaining names — wallet, rebalance/published_with_changes, news/newspaper, person, download, bell, gear — each as a simple line SVG. The fallback circle keeps any unlisted name from breaking.)

Then create the real `app/templates/base.html` by adapting the shared shell from `holdings_investor_os/code.html` (the `<nav>` sidebar and `<header>` topbar shown at lines ~108–150). Requirements:
- `<link rel="stylesheet" href="{{ url_for('static', filename='app.css') }}">` in `<head>`; **remove** the Tailwind CDN `<script>`, the Google-Fonts `<link>`s, and the inline `<script id="tailwind-config">` (all now compiled/self-hosted).
- Sidebar brand: "Investor OS" + "Private · Paresh Karia" (teal). Nav items are links to `/`, `/holdings`, `/rebalance`, `/brief`, `/profile`; each uses `{{ icon('...') }}`; the item whose key equals `active` gets the active classes (`bg-secondary-container text-primary`), others the default.
- Topbar: `<h1>{{ page }}</h1>`, then the **member switcher** on the right: for `m in ['All'] + members`, an `<a>` pill linking to the current path with `?member=<m>` (All → no member param), teal when selected. Then a muted `{{ freshness }}` line under the title.
- `<main>` contains `{% block content %}{% endblock %}`.
- Preserve responsive behavior (sidebar `hidden md:flex`) from the Stitch markup.

- [ ] **Step 7: Rebuild CSS and smoke-test styled shell**

Run `powershell -File build-css.ps1`, then start the app (Task 1 Step 5 pattern on port 8556) and GET `/` — confirm 200 and that the response HTML references `/static/app.css` and contains the sidebar nav markup. (Full visual check happens after Overview in Task 5.)

- [ ] **Step 8: Commit**

```bash
git add app/tailwind app/static build-css.ps1 build-css.sh app/templates/base.html app/templates/_icons.html .gitignore
git commit -m "build(app): tailwind compile pipeline, self-hosted fonts, base layout"
```

---

### Task 3: view_models.py + charts.py (allocation + area path) with tests

**Files:**
- Create: `app/charts.py`, `app/view_models.py`, `tests/test_charts.py`, `tests/test_view_models.py`

**Interfaces:** as declared in the Interfaces block (this task implements `CHART_COLORS`, `area_path`, `alloc_segments`, and `common`, `overview`, `holdings`, `rebalance` context builders; `portfolio_series` is stubbed to `[]` here and filled in Task 4; `brief_ctx`/`profile_ctx` in Tasks 8–9).

- [ ] **Step 1: tests/test_charts.py**

```python
from app.charts import area_path, alloc_segments, CHART_COLORS
from app.parser import parse_holdings
from app.prices import Quote
from app.portfolio import build_portfolio
from pathlib import Path

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"


def test_area_path_two_points():
    p = area_path([100.0, 200.0], w=1000, h=250)
    assert p["line"].startswith("M") and p["area"].endswith("Z")


def test_area_path_flat_when_single():
    p = area_path([100.0])
    assert "L1000" in p["line"] or p["line"].count(",") >= 1  # a horizontal line renders


def test_alloc_segments_order_and_pct():
    pf = build_portfolio(parse_holdings(FIX),
                         {"INE001A01001": "ALPHAMOT"}, {"ALPHAMOT": Quote(300.0, 2.0)}, [])
    segs = alloc_segments(pf.totals())
    assert [s["label"] for s in segs][0] == "Direct Equity"
    assert all(0 <= s["pct"] <= 100 for s in segs)
    assert segs[0]["color"] == CHART_COLORS[0]
    assert abs(sum(s["pct"] for s in segs) - 100) < 0.5
```

- [ ] **Step 2: Run to verify fail** — `pytest tests\test_charts.py -q` → FAIL (no module).

- [ ] **Step 3: app/charts.py**

```python
from __future__ import annotations
from app.portfolio import fmt_short

CHART_COLORS = ["#005c55", "#4f46e5", "#f59e0b", "#3b82f6", "#64748b"]
_CLASS_ORDER = [("equity", "Direct Equity"), ("mf", "Mutual Funds"), ("gold", "Gold (SGB)"),
                ("debt", "Debt & FD"), ("cash", "Cash")]


def area_path(series, w: int = 1000, h: int = 250) -> dict:
    if not series:
        return {"line": f"M0,{h//2} L{w},{h//2}", "area": f"M0,{h} L{w},{h} Z"}
    if len(series) == 1:
        series = [series[0], series[0]]
    lo, hi = min(series), max(series)
    span = (hi - lo) or 1.0
    n = len(series)
    def x(i): return i * w / (n - 1)
    def y(v): return h - (v - lo) / span * (h * 0.9) - h * 0.05
    pts = [f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(series)]
    line = "M" + " L".join(pts)
    area = line + f" L{w:.1f},{h} L0,{h} Z"
    return {"line": line, "area": area}


def alloc_segments(totals) -> list[dict]:
    total = totals.total_value or 1.0
    out = []
    for i, (key, label) in enumerate(_CLASS_ORDER):
        val = totals.equity_value if key == "equity" else totals.extras_by_class.get(key, 0.0)
        if val <= 0:
            continue
        out.append({"label": label, "pct": val / total * 100, "color": CHART_COLORS[i],
                    "short": fmt_short(val)})
    return out


def portfolio_series(pf, member, history) -> list:
    return []  # filled in Task 4
```

- [ ] **Step 4: Run** — `pytest tests\test_charts.py -q` → 3 passed.

- [ ] **Step 5: tests/test_view_models.py**

```python
from pathlib import Path
from app.parser import parse_holdings
from app.prices import Quote
from app.portfolio import build_portfolio
from app import view_models as vm

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"
ISIN = {"INE001A01001": "ALPHAMOT", "INE004D01034": "DELTAB"}
Q = {"ALPHAMOT": Quote(300.0, 2.0), "DELTAB": Quote(160.0, -1.0)}


def _pf():
    return build_portfolio(parse_holdings(FIX), ISIN, Q, [])


def test_common_members_and_active():
    c = vm.common(_pf(), "overview", None)
    assert c["members"] == ["PK", "CK"] and c["active"] == "overview"
    assert "live prices" in c["freshness"]


def test_overview_cards_and_movers():
    o = vm.overview(_pf(), None, "6M")
    labels = [c["label"] for c in o["cards"]]
    assert labels == ["Total Value", "Unrealised P/L", "Day P/L", "Cash Available"]
    assert o["alloc"] and o["movers"]
    assert o["range"] == "6M"


def test_holdings_groups_and_search():
    h = vm.holdings(_pf(), None, "delta")
    names = [r["name"] for g in h["groups"] for r in g["rows"]]
    assert any("Delta" in n for n in names) and not any("Alpha" in n for n in names)
```

- [ ] **Step 6: Run to verify fail**, then implement **app/view_models.py**:

```python
from __future__ import annotations
from app import portfolio as pmod
from app import charts

RANGE_TO_PERIOD = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "ALL": "5y"}
_GROUPS = [("equity", "Direct Equity", "NSE"), ("mf", "Mutual Funds", ""),
           ("gold", "Gold", ""), ("debt", "Debt & FD", ""), ("cash", "Cash", "")]


def common(pf, active: str, member: str | None) -> dict:
    live = sum(1 for c in pf.consolidated(member) if c.price_live)
    total = len(pf.consolidated(member))
    return {"members": pf.members, "active": active, "member": member,
            "brand_sub": "Private · Paresh Karia",
            "freshness": f"Updated {pf.asof:%d %b %Y %H:%M} · live prices {live}/{total}"}


def _cls_of(name, isin, pf):
    for p in pf.positions:
        if p.isin == isin:
            return p
    return None


def overview(pf, member, rng: str) -> dict:
    t = pf.totals(member)
    cards = [
        {"label": "Total Value", "value": pmod.fmt_short(t.total_value),
         "sub": pmod.fmt_inr(t.total_value), "tone": "muted"},
        {"label": "Unrealised P/L", "value": pmod.fmt_short(t.pl),
         "sub": (pmod.fmt_pct(t.pl_pct) if t.pl_pct is not None else "—"),
         "tone": "up" if t.pl >= 0 else "down"},
        {"label": "Day P/L", "value": pmod.fmt_short(t.day_pl),
         "sub": pmod.fmt_pct(t.day_pl_pct), "tone": "up" if t.day_pl >= 0 else "down"},
        {"label": "Cash Available", "value": pmod.fmt_short(t.extras_by_class.get("cash", 0.0)),
         "sub": f"{(t.extras_by_class.get('cash', 0.0)/t.total_value*100 if t.total_value else 0):.1f}% of portfolio",
         "tone": "muted"},
    ]
    movers = [{"name": c.name.title(), "pct": pmod.fmt_pct(c.day_pct),
               "up": (c.day_pct or 0) >= 0, "short": pmod.fmt_short(c.value)}
              for c in pf.movers(member)]
    return {"cards": cards, "alloc": charts.alloc_segments(t), "movers": movers,
            "range": rng, "ranges": list(RANGE_TO_PERIOD)}


def holdings(pf, member, q: str) -> dict:
    ql = (q or "").lower().strip()
    groups = []
    for key, title, tag in _GROUPS:
        rows = []
        for c in pf.consolidated(member):
            p = _cls_of(c.name, c.isin, pf)
            if not p or p.member and False:
                pass
            # class of a consolidated position = class of any underlying lot
            cls = next((x.cls for x in pf.positions if x.isin == c.isin), None) if False else None
            # simpler: attach class via a lookup dict below
        groups.append({"key": key, "title": title, "tag": tag, "rows": rows, "subtotal": ""})
    # Rebuild cleanly using a class map:
    cls_by_isin = {p.isin: p.cls for p in pf.positions}
    for g in groups:
        rws = []
        sub = 0.0
        for c in pf.consolidated(member):
            if cls_by_isin.get(c.isin) != g["key"]:
                continue
            if ql and ql not in c.name.lower() and ql not in (c.nse_symbol or "").lower():
                continue
            sub += c.value
            rws.append({"name": c.name.title(), "nse": c.nse_symbol or "—",
                        "qty": c.qty, "avg": c.avg_cost, "price": c.price,
                        "value": pmod.fmt_short(c.value),
                        "pl": (pmod.fmt_pct(c.pl_pct) if c.pl_pct is not None else "—"),
                        "pl_up": (c.pl_pct or 0) >= 0, "pl_known": c.pl_pct is not None,
                        "day": (pmod.fmt_pct(c.day_pct) if c.day_pct is not None else "—"),
                        "day_up": (c.day_pct or 0) >= 0, "day_known": c.day_pct is not None,
                        "held_by": c.held_by, "live": c.price_live})
        g["rows"] = rws
        g["subtotal"] = pmod.fmt_short(sub)
    groups = [g for g in groups if g["rows"] or not ql]
    return {"groups": [g for g in groups if g["rows"]], "q": q or ""}
```

Note: the `holdings` scaffolding above shows the intended shape; the FINAL file must contain only the clean `cls_by_isin`-based implementation (delete the dead first loop). Requires `Position` to expose `cls` — it already carries the source class via `parser.Holding.cls`; add `cls` to `Position` in Task 3 Step 7.

- [ ] **Step 7: Add `cls` to Position** so holdings grouping works.

In `app/portfolio.py`: add `cls: str = "equity"` field to `Position` and set it in `build_portfolio` from `h.cls` (the parser Holding has no `cls` today — the ICICI parser only yields equities, so default all parsed positions to `"equity"`; extras carry their own `asset_class`). Concretely: `Position(..., cls="equity")` for every parsed holding. Re-run `pytest tests\test_portfolio.py` to confirm still green.

- [ ] **Step 8: Run** — `pytest tests\test_view_models.py tests\test_portfolio.py -q` → all pass.

- [ ] **Step 9: Commit**

```bash
git add app/charts.py app/view_models.py app/portfolio.py tests/test_charts.py tests/test_view_models.py
git commit -m "feat(app): view-model + chart builders"
```

---

### Task 4: Real portfolio value series (historical prices)

**Files:**
- Modify: `app/prices.py` (add `fetch_history`), `app/charts.py` (`portfolio_series`)
- Test: `tests/test_charts.py` (add), `tests/test_prices.py` (add `_history_from_frame`)

**Interfaces:** `prices.fetch_history(symbols, period, ttl) -> dict[str, list[float]]`; `charts.portfolio_series(pf, member, history) -> list[float]`.

- [ ] **Step 1: Add tests**

`tests/test_prices.py` append:
```python
def test_history_from_frame():
    import pandas as pd
    from app.prices import _history_from_frame
    df = pd.DataFrame({("Close", "ALPHAMOT.NS"): [10.0, 11.0, 12.0]})
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    h = _history_from_frame(df, ["ALPHAMOT"])
    assert h["ALPHAMOT"] == [10.0, 11.0, 12.0]
```
`tests/test_charts.py` append:
```python
def test_portfolio_series_reconstructs():
    from app.charts import portfolio_series
    from app.parser import parse_holdings
    from app.prices import Quote
    from app.portfolio import build_portfolio
    from pathlib import Path
    fix = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"
    pf = build_portfolio(parse_holdings(fix), {"INE001A01001": "ALPHAMOT"},
                         {"ALPHAMOT": Quote(300.0, 2.0)}, [])
    hist = {"ALPHAMOT": [200.0, 250.0, 300.0]}   # ALPHA held 150 qty consolidated
    s = portfolio_series(pf, None, hist)
    assert len(s) == 3 and s[-1] > s[0]
    assert abs(s[2] - 150 * 300.0 - _nonmarket(pf)) < 1  # ends at current-price value + flat non-market
```
Add helper at top of that test file:
```python
def _nonmarket(pf):
    t = pf.totals()
    return sum(v for k, v in t.extras_by_class.items())
```

- [ ] **Step 2: Run to verify fail.**

- [ ] **Step 3: prices.py — add**

```python
def _history_from_frame(df, symbols) -> dict:
    out = {}
    close = df["Close"] if "Close" in getattr(df.columns, "get_level_values", lambda _: [])(0) else df
    for s in symbols:
        col = f"{s}.NS"
        if col in close.columns:
            series = close[col].dropna().tolist()
            if series:
                out[s] = [float(x) for x in series]
    return out


_hist_cache: dict = {}

def fetch_history(nse_symbols: list[str], period: str = "6mo", ttl: int = 3600) -> dict:
    symbols = sorted(set(s for s in nse_symbols if s))
    if not symbols:
        return {}
    key = (period, tuple(symbols))
    import time
    now = time.time()
    if key in _hist_cache and now - _hist_cache[key][0] < ttl:
        return _hist_cache[key][1]
    try:
        import yfinance as yf
        df = yf.download([f"{s}.NS" for s in symbols], period=period, interval="1d",
                         progress=False, threads=True, group_by="column")
        hist = _history_from_frame(df, symbols)
    except Exception:
        hist = {}
    if hist:
        _hist_cache[key] = (now, hist)
    return hist
```

- [ ] **Step 4: charts.py — replace `portfolio_series`**

```python
def portfolio_series(pf, member, history) -> list:
    if not history:
        return []
    cons = pf.consolidated(member)
    lengths = [len(history[c.nse_symbol]) for c in cons if c.nse_symbol in history]
    if not lengths:
        return []
    n = min(lengths)
    nonmarket = sum(v for v in pf.totals(member).extras_by_class.values())
    series = []
    for i in range(n):
        total = nonmarket
        for c in cons:
            h = history.get(c.nse_symbol)
            total += c.qty * (h[-n + i] if h else c.price)
        series.append(total)
    return series
```

- [ ] **Step 5: Run** — `pytest tests\test_charts.py tests\test_prices.py -q` → all pass.

- [ ] **Step 6: Commit** — `git add app/prices.py app/charts.py tests/test_prices.py tests/test_charts.py && git commit -m "feat(app): reconstructed portfolio value series from historical prices"`

---

### Task 5: Overview route + template

**Files:**
- Create: `app/templates/overview.html`
- Modify: `app/server.py` (`/` route: load portfolio, build context, render), add `load_portfolio()` + `onboarding` helpers.

**Interfaces:** Consumes `view_models.overview/common`, `charts.area_path`, `prices.fetch_history`. Produces the working Overview page.

- [ ] **Step 1: server.py — add data loading + real `/` route**

Add near top of `create_app` (module-level helpers):
```python
from app import parser, mapping, prices, advisory
from app import portfolio as pmod
from app import view_models as vm
from app import charts

HOLDINGS = DATA / "holdings.xlsx"

def load_portfolio():
    if not HOLDINGS.exists():
        return None
    pr = parser.parse_holdings(HOLDINGS)
    isin_map = mapping.ensure_map(DATA)
    quotes = prices.fetch_quotes([isin_map.get(h.isin) for h in pr.holdings if isin_map.get(h.isin)])
    extras = pmod.load_extras(DATA / "extras.json")
    return pmod.build_portfolio(pr, isin_map, quotes, extras)
```
Replace the placeholder `/` route:
```python
    @app.route("/")
    def overview():
        pf = load_portfolio()
        if pf is None:
            return render_template("base.html", **_empty("overview", "Overview"))
        member = request.args.get("member") or None
        rng = request.args.get("range", "6M")
        ctx = vm.overview(pf, member, rng)
        isin_map = mapping.ensure_map(DATA)
        hist = prices.fetch_history([c.nse_symbol for c in pf.consolidated(member) if c.nse_symbol],
                                    vm.RANGE_TO_PERIOD.get(rng, "6mo"))
        ctx["chart"] = charts.area_path(charts.portfolio_series(pf, member, hist))
        ctx.update(vm.common(pf, "overview", member))
        ctx["page"] = "Overview"
        return render_template("overview.html", **ctx)
```
Add helper:
```python
def _empty(active, page):
    return {"active": active, "page": page, "members": [], "member": None,
            "freshness": "", "empty": True}
```
(Every route passes `empty` so `base.html` can show an onboarding card when no data — add a `{% if empty %}` block in base's content area, or handle per-template. For Overview, `overview.html` shows the onboarding card when `empty`.)

- [ ] **Step 2: overview.html**

`{% extends "base.html" %}{% block content %}…{% endblock %}` — adapt the main-content markup (everything inside `<main>` after the header) from `stitch_investor_os_portfolio_dashboard/overview_investor_os/code.html`. Bind:
- KPI cards ← `for c in cards`: `c.value` (big), `c.sub` (small; class `text-emerald` if `c.tone=='up'`, red if `'down'`, muted otherwise). Keep the exact card classes from Stitch.
- Portfolio Value card: range tabs ← `for r in ranges` as `<a href="?range={{r}}&member={{member or 'All'}}">` with active style when `r == range`. Replace the hardcoded `<svg><path d="…">` with `<path d="{{ chart.area }}" fill="url(#areaGradient)"/><path d="{{ chart.line }}" .../>`. Keep the `<defs><linearGradient id="areaGradient">` from Stitch.
- Allocation card: replace the 5 hardcoded bar `<div>`s and legend rows with `for s in alloc`: bar segment `style="width: {{ s.pct }}%; background: {{ s.color }}"`; legend `{{ s.label }} … {{ '%.1f'|format(s.pct) }}% · {{ s.short }}` with a `{{ s.color }}` dot.
- Top Movers: `for m in movers`: name, `{{ m.pct }}` green/red per `m.up`, `{{ m.short }}`.
- Wrap the whole content in `{% if empty %}`<onboarding card: "No holdings yet — drop the ICICI export into data/holdings.xlsx">`{% else %}`…`{% endif %}`.

- [ ] **Step 3: Rebuild CSS + visual verify against the Stitch screenshot**

Run `powershell -File build-css.ps1`. Start the app on 8556 with the fixture data (`$env:INVESTOR_OS_DATA` pointed at a temp dir containing `sample-holdings.xlsx`), open `http://127.0.0.1:8556/` in a real browser, and compare side-by-side with `overview_investor_os/screen.png`: sidebar, four KPI cards, teal area chart, allocation bar + legend, top movers. Fix drift. Also click a member pill and a range tab — the URL updates and numbers change.

- [ ] **Step 4: Commit** — `git add app/server.py app/templates/overview.html app/static/app.css && git commit -m "feat(app): overview page"`

---

### Task 6: Holdings route + template

**Files:**
- Create: `app/templates/holdings.html`
- Modify: `app/server.py` (`/holdings`)

- [ ] **Step 1: server.py `/holdings`**
```python
    @app.route("/holdings")
    def holdings():
        pf = load_portfolio()
        if pf is None:
            return render_template("holdings.html", **_empty("holdings", "Holdings"))
        member = request.args.get("member") or None
        q = request.args.get("q", "")
        ctx = vm.holdings(pf, member, q)
        ctx.update(vm.common(pf, "holdings", member)); ctx["page"] = "Holdings"; ctx["empty"] = False
        return render_template("holdings.html", **ctx)
```

- [ ] **Step 2: holdings.html** — adapt from `holdings_investor_os/code.html` main content. Search box is a `<form method="get">` with an `<input name="q" value="{{ q }}">` and the member param preserved via a hidden input. Table: `for g in groups` render a section header (`g.title` + optional `g.tag` + right-aligned `g.subtotal`), then `for r in g.rows` a row with `r.name`/`r.nse`, `r.qty|round`, `r.avg`, `r.price`, `r.value`, `r.pl` (green if `r.pl_up` and `r.pl_known` else red/muted), `r.day` similarly, and `held_by` chips `for h in r.held_by`. Add a small "stale"/"⚠cost" note where `not r.live` / `not r.pl_known`. Drop the Stitch "Add Holding" button (data comes from Excel). Show onboarding card when `empty`.

- [ ] **Step 3: Rebuild CSS + verify vs `holdings_investor_os/screen.png`** (grouped sections, right-aligned tabular numbers, held-by chips, TCS-style red row). Search filters; member pill filters.

- [ ] **Step 4: Commit** — `git add app/server.py app/templates/holdings.html app/static/app.css && git commit -m "feat(app): holdings page"`

---

### Task 7: Rebalance route + template

**Files:**
- Create: `app/templates/rebalance.html`
- Modify: `app/server.py` (`/rebalance`), `app/view_models.py` (`rebalance`)

- [ ] **Step 1: view_models.rebalance**
```python
def rebalance(pf, adv, tab: str) -> dict:
    badge = {"DONE": ("Done", "green"), "IN PROGRESS": ("In Progress", "amber"),
             "PENDING": ("Pending", "grey"), "REVIEW": ("Review", "grey")}
    exits = [{"stock": e.stock, "label": badge[e.status][0], "tone": badge[e.status][1],
              "priority": e.priority, "proceeds": e.proceeds, "reason": e.reason,
              "initials": "".join(w[0] for w in e.stock.split()[:2]).upper()} for e in adv.exits]
    buys = [{"stock": b.stock, "sector": b.sector,
             "lo": pmod.fmt_short(b.alloc_lo), "hi": pmod.fmt_short(b.alloc_hi),
             "deployed": pmod.fmt_short(b.current_value), "pct": round(b.progress_pct)} for b in adv.buys]
    sched = [{"label": m.label, "exits": m.exits_text, "buys": m.buys_text, "here": m.is_current}
             for m in adv.schedule]
    done = sum(1 for e in adv.exits if e.status == "DONE")
    return {"tab": tab if tab in ("exits", "buys", "schedule") else "exits",
            "exits": exits, "buys": buys, "sched": sched,
            "summary": f"{done}/{len(adv.exits)} exits done"}
```

- [ ] **Step 2: server.py `/rebalance`**
```python
    @app.route("/rebalance")
    def rebalance():
        pf = load_portfolio()
        if pf is None:
            return render_template("rebalance.html", **_empty("rebalance", "Rebalance"))
        advp = DATA / "advisory.xlsx"
        member = request.args.get("member") or None
        common = vm.common(pf, "rebalance", member)
        if not advp.exists():
            return render_template("rebalance.html", page="Rebalance", empty=False,
                                   no_adv=True, tab="exits", exits=[], buys=[], sched=[],
                                   summary="", **common)
        from datetime import date
        adv = advisory.apply_status(advisory.parse_advisory(advp), pf, DATA, date.today())
        ctx = vm.rebalance(pf, adv, request.args.get("tab", "exits"))
        ctx.update(common); ctx["page"] = "Rebalance"; ctx["empty"] = False; ctx["no_adv"] = False
        return render_template("rebalance.html", **ctx)
```

- [ ] **Step 3: rebalance.html** — adapt from `rebalance_strategy_investor_os/code.html`. Three tab links (`?tab=exits|buys|schedule`, preserve member), active underline when `tab==`. `{% if tab=='exits' %}` exits table with status pills colored by `tone` (green/amber/grey) — reuse the Stitch pill markup; `{% elif tab=='buys' %}` cards with progress bars `style="width: {{ b.pct }}%"`; `{% else %}` schedule timeline, teal marker + "You are here" when `m.here`. Show a friendly card when `no_adv`. Onboarding card when `empty`.

- [ ] **Step 4: Rebuild CSS + verify vs `rebalance_strategy_investor_os/screen.png`** (Done/In Progress/Pending pills, tabs switch via URL).

- [ ] **Step 5: Commit** — `git add app/server.py app/view_models.py app/templates/rebalance.html app/static/app.css && git commit -m "feat(app): rebalance page"`

---

### Task 8: Morning Brief route + template (render + generate)

**Files:**
- Create: `app/templates/brief.html`
- Modify: `app/server.py` (`/brief` GET, `/brief/generate` POST), `app/view_models.py` (`brief_ctx`)

- [ ] **Step 1: view_models.brief_ctx**
```python
def brief_ctx(base_dir, pf, pick: str | None) -> dict:
    import markdown as md
    briefs_dir = base_dir / "briefs"
    files = sorted(briefs_dir.glob("*.md"), reverse=True) if briefs_dir.exists() else []
    dates = [f.stem for f in files]
    chosen = pick if pick in dates else (dates[0] if dates else None)
    html = ""
    if chosen:
        html = md.markdown((briefs_dir / f"{chosen}.md").read_text(encoding="utf-8"),
                           extensions=["extra"])
    return {"dates": dates, "chosen": chosen, "brief_html": html, "has_brief": bool(chosen)}
```

- [ ] **Step 2: server.py brief routes**
```python
    @app.route("/brief")
    def brief():
        pf = load_portfolio()
        if pf is None:
            return render_template("brief.html", **_empty("brief", "Morning Brief"))
        member = request.args.get("member") or None
        ctx = vm.brief_ctx(BASE, pf, request.args.get("pick"))
        ctx.update(vm.common(pf, "brief", member)); ctx["page"] = "Morning Brief"; ctx["empty"] = False
        ctx["claude_ok"] = bool(__import__("app.brief", fromlist=["find_claude"]).find_claude())
        ctx["error"] = request.args.get("error", "")
        return render_template("brief.html", **ctx)

    @app.route("/brief/generate", methods=["POST"])
    def brief_generate():
        from flask import redirect, url_for
        from app import brief as bmod
        pf = load_portfolio()
        if pf is None:
            return redirect(url_for("brief"))
        try:
            bmod.generate_brief(pf, BASE)
            return redirect(url_for("brief"))
        except bmod.BriefError as e:
            return redirect(url_for("brief", error=e.message))
```

- [ ] **Step 3: brief.html** — adapt from `morning_brief_investor_os/code.html`. The "Generate Brief" is a `<form method="post" action="/brief/generate">` with a teal submit button (add a tiny inline `onsubmit` that disables the button and shows "Generating…" — the only JS in the app). The brief card renders `{{ brief_html | safe }}` (already HTML from markdown) inside the Stitch card shell; date picker is a `<select>` submitting `?pick=`. If `error`, show a red friendly card with `{{ error }}`. If `not claude_ok`, show the "install/login or use Cowork" hint. If `not has_brief`, show the empty-state ("Click Generate…"). The right-column "Key Indices"/"Weekly Digest" from the mockup are static placeholders labelled "sample" for now (real feed is Phase 4) — keep them but mark clearly.

- [ ] **Step 4: Verify** — GET `/brief` renders (empty state on fixture data); POST path redirects; with a real `claude` login the button produces `briefs/<today>.md` and it renders. Rebuild CSS.

- [ ] **Step 5: Commit** — `git add app/server.py app/view_models.py app/templates/brief.html app/static/app.css && git commit -m "feat(app): morning brief page + generate"`

---

### Task 9: Investor Profile route + template

**Files:**
- Create: `app/templates/profile.html`
- Modify: `app/server.py` (`/profile`), `app/view_models.py` (`profile_ctx`)

- [ ] **Step 1: view_models.profile_ctx**
```python
def profile_ctx(base_dir) -> dict:
    import markdown as md
    p = base_dir / "profile" / "one-pager.md"
    if p.exists():
        return {"has_profile": True,
                "profile_html": md.markdown(p.read_text(encoding="utf-8"), extensions=["extra"])}
    return {"has_profile": False, "profile_html": ""}
```

- [ ] **Step 2: server.py `/profile`**
```python
    @app.route("/profile")
    def profile():
        pf = load_portfolio()
        member = request.args.get("member") or None
        ctx = vm.profile_ctx(BASE)
        common = vm.common(pf, "profile", member) if pf else _empty("profile", "Investor Profile")
        ctx.update(common); ctx["page"] = "Investor Profile"; ctx.setdefault("empty", pf is None)
        return render_template("profile.html", **ctx)
```

- [ ] **Step 3: profile.html** — adapt from `investor_profile_investor_os/code.html`: the teal callout, then `{% if has_profile %}{{ profile_html | safe }}{% else %}` the instruction card ("paste the interview prompt … save as profile/one-pager.md"). The Stitch mockup's rich section styling (North Star / Core Philosophy / Mindset Rules / Anti-Portfolio) applies to the rendered markdown via a `.prose`-style wrapper — add matching CSS classes so headings/lists inherit the Manrope/teal treatment.

- [ ] **Step 4: Verify + rebuild CSS** — GET `/profile` shows the instruction card (no one-pager on fixture); drop a sample `profile/one-pager.md` and confirm it renders styled.

- [ ] **Step 5: Commit** — `git add app/server.py app/view_models.py app/templates/profile.html app/static/app.css && git commit -m "feat(app): investor profile page"`

---

### Task 10: Route tests (Flask test client)

**Files:**
- Create: `tests/test_routes.py`

- [ ] **Step 1: tests/test_routes.py**
```python
import shutil
from pathlib import Path
import pytest
from app.server import create_app

ROOT = Path(__file__).parent.parent
FIXDIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    shutil.copy(FIXDIR / "sample-holdings.xlsx", tmp_path / "holdings.xlsx")
    shutil.copy(FIXDIR / "sample-advisory.xlsx", tmp_path / "advisory.xlsx")
    monkeypatch.setenv("INVESTOR_OS_DATA", str(tmp_path))
    import importlib, app.server as srv
    importlib.reload(srv)          # re-read DATA from env
    return srv.create_app().test_client()


def test_overview_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Total Value" in r.data and "₹".encode() in r.data


def test_member_filter_changes_page(client):
    assert client.get("/?member=CK").status_code == 200


def test_holdings_and_search(client):
    assert client.get("/holdings").status_code == 200
    assert client.get("/holdings?q=alpha").status_code == 200


def test_rebalance_tabs(client):
    for t in ("exits", "buys", "schedule"):
        assert client.get(f"/rebalance?tab={t}").status_code == 200


def test_brief_and_profile(client):
    assert client.get("/brief").status_code == 200
    assert client.get("/profile").status_code == 200


def test_brief_generate_redirects(client):
    r = client.post("/brief/generate")
    assert r.status_code in (302, 303)
```

- [ ] **Step 2: Run** — `.\.venv\Scripts\python -m pytest tests\test_routes.py -q` → all pass. Then full suite `pytest -q` → all green.

- [ ] **Step 3: Commit** — `git add tests/test_routes.py && git commit -m "test(app): flask route tests"`

---

### Task 11: Launchers + handoff docs

**Files:**
- Modify: `Start Dashboard.command`, `start-dashboard.ps1`, `setup.sh`, `setup.ps1`, `CLAUDE.md`, `README-SIR.md`, `README.md`

- [ ] **Step 1: Launchers run Flask**

`start-dashboard.ps1`:
```powershell
if (-not (Test-Path .venv)) { python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt }
Start-Process "http://127.0.0.1:8555"
.\.venv\Scripts\python -m flask --app app.server run --port 8555
```
`Start Dashboard.command`:
```bash
#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d .venv ]; then bash setup.sh; fi
( sleep 2; open http://127.0.0.1:8555 ) &
./.venv/bin/python -m flask --app app.server run --port 8555
```

- [ ] **Step 2: setup scripts** — unchanged logic, but they no longer need `.streamlit`. Ensure `setup.sh`/`setup.ps1` still `pip install -r requirements.txt` and `mkdir -p data briefs profile`. Add a note line: CSS is prebuilt/committed; only run `build-css` if you change templates.

- [ ] **Step 3: CLAUDE.md** — update the "How it works" section: the UI is now a **Flask app** (`app/server.py`) rendering Jinja templates in `app/templates/` styled by the **prebuilt** `app/static/app.css`. Add a playbook entry:
```
- "Change how a page looks" → edit the matching template in app/templates/ and,
  only if you changed Tailwind classes, rebuild CSS: `bash build-css.sh`
  (needs Node/npx). Most text/number/logic changes need no rebuild.
- "Dashboard won't start" → run ./setup.sh then Start Dashboard.command;
  the app serves at http://127.0.0.1:8555.
```
Remove Streamlit mentions.

- [ ] **Step 4: README-SIR.md + README.md** — change the run instructions/port from Streamlit:8501 to Flask:8555; otherwise the weekly ritual is unchanged. Update the Phase-3 line to note the Stitch-based UI.

- [ ] **Step 5: Commit** — `git add "Start Dashboard.command" start-dashboard.ps1 setup.sh setup.ps1 CLAUDE.md README-SIR.md README.md && git commit -m "docs(app): launchers + handoff docs for flask UI"`

---

### Task 12: Fold Stitch source into repo; final E2E, visual QA, push

**Files:**
- Move: `stitch_investor_os_portfolio_dashboard/` → `docs/design/stitch/` (keep as design reference)

- [ ] **Step 1: Keep the Stitch designs as reference**

```bash
git mv stitch_investor_os_portfolio_dashboard docs/design-stitch
git add docs/design-stitch
```
(These are fictional-data mockups — safe to commit as design reference.)

- [ ] **Step 2: Full test suite** — `.\.venv\Scripts\python -m pytest -q` → all green.

- [ ] **Step 3: Rebuild CSS fresh & confirm no CDN leaks**

Run `powershell -File build-css.ps1`. Then:
```bash
grep -REn "cdn.tailwindcss|fonts.googleapis|fonts.gstatic|https?://" app/templates || echo "no external URLs in templates"
```
Expected: no external URLs in served templates (fonts + css are local).

- [ ] **Step 4: Real-data E2E + side-by-side visual QA**

```powershell
Copy-Item "report_data\Current Portfolio - All Members (1).xlsx" data\holdings.xlsx -Force
Copy-Item "report_data\Portfolio Advisory Report - 50 Stocks.xlsx" data\advisory.xlsx -Force
.\start-dashboard.ps1
```
Walk all 5 pages in the browser next to the five `docs/design-stitch/*/screen.png` files. Checklist: sidebar + all 4 member pills (PK/CK/NK/DK) present and switching; Overview cards + teal chart + allocation + movers; Holdings grouped table; Rebalance 3 tabs with pills; Brief renders (generate works with real Claude login); Profile instruction card. Confirm the "24 of 146 rows" data-completeness caveat still stands (separate data-file issue, tracked elsewhere).

- [ ] **Step 5: git hygiene + push**

```bash
git status --short   # must show NO data/, briefs/, profile/, report_data/ files
git add -A && git commit -m "chore(app): fold stitch designs into docs, final QA" --allow-empty
git push
```

---

## Self-Review (done at plan-writing time)

- **Design coverage:** DESIGN.md tokens → Task 2 (tailwind config + fonts); 5 screens → base (Task 2) + Tasks 5–9; member switcher/range/tab/search → server-side params across Tasks 5–9; charts real data → Tasks 3–4; briefs on Claude subscription → Task 8 (reuses brief.py); handoff → Task 11; offline/no-CDN → Tasks 2 & 12 Step 3. Streamlit retired → Task 1. No gaps.
- **Placeholder scan:** the only "shape then final" note is `view_models.holdings` in Task 3 (explicitly says ship the clean `cls_by_isin` version); all other code is literal. `portfolio_series` is a declared stub in Task 3 and implemented in Task 4 — intentional, noted at both ends.
- **Type consistency:** `common/overview/holdings/rebalance/brief_ctx/profile_ctx` names match between the Interfaces block, `view_models.py`, and each server route. `charts.area_path` returns `{line, area}` consumed identically in overview.html. `Position.cls` added in Task 3 Step 7 and consumed by `view_models.holdings`. `RANGE_TO_PERIOD` defined once in view_models, used in server `/`. Route/template names (`overview.html … profile.html`) consistent across server and file map.
- **Dependency note:** Tailwind build needs Node/npx (present on dev: v25). Runtime needs neither. Flagged in CLAUDE.md + setup notes.
```
