# Investor OS Demo Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pitch/demo package for Paresh Karia: one self-contained interactive HTML dashboard mockup (fictional Indian portfolio, ₹), three prompt MD files, and a README with demo script — per the approved spec at `docs/superpowers/specs/2026-07-06-investor-os-demo-package-design.md`.

**Architecture:** The dashboard is ONE static HTML file with all CSS/JS/data inline — no libraries, no network requests. A single `PORTFOLIO` data object drives every number on screen (JS computes totals/percentages so nothing is inconsistent). Charts are hand-built inline SVG. The prompt files are adaptations of the two reference MDs already in the repo root.

**Tech Stack:** Vanilla HTML/CSS/JS (single file, inline SVG charts, system font stack). Markdown for prompts/README. No build step, no dependencies.

## Global Constraints

- `demo/investor-os-dashboard.html` must make **zero network requests** (no CDN, no fonts, no images by URL; emoji + inline SVG only).
- All data is **fictional** and every dashboard view shows a "DEMO — SAMPLE DATA" badge in the header.
- Currency: Indian formatting everywhere — `₹24,60,000` style grouping (en-IN) and `₹2.41 Cr` / `₹24.6 L` short forms.
- Demo "today" is **Monday, 6 July 2026** (hardcode; do not use `new Date()` so the demo never goes stale).
- Dark premium private-banking aesthetic: charcoal/navy base, gold + emerald accents. Use the `frontend-design` skill when styling (spec §3).
- Every interactive element must do something visible — no dead buttons.
- Commit after every task. Repo root: `c:\Users\Hemant\Downloads\Investment_portfolio_dashboard`.

## Canonical Sample Data (used by Tasks 2–8 — single source of truth)

Holdings (equity: qty × LTP; MF: units × NAV; gold: grams × ₹/g):

| Instrument | Class | Qty | Avg cost | Current | Day % |
|---|---|---|---|---|---|
| RELIANCE | equity | 500 | 2,450 | 2,912 | +0.8 |
| HDFCBANK | equity | 800 | 1,520 | 1,748 | +1.2 |
| TCS | equity | 120 | 3,650 | 3,418 | −4.2 |
| INFY | equity | 300 | 1,385 | 1,624 | −0.6 |
| ITC | equity | 1,500 | 412 | 465 | +0.4 |
| TATAPOWER | equity | 2,000 | 285 | 342 | +2.1 |
| UTI Nifty 50 Index Fund (Direct-G) | mf | 18,500 units | 148.20 | 172.40 | +0.5 |
| Parag Parikh Flexi Cap (Direct-G) | mf | 22,000 units | 71.50 | 82.90 | +0.5 |
| Sovereign Gold Bonds (2019–22 tranches) | gold | 550 g | 5,100/g | 7,420/g | +0.2 |
| Bank FDs + AAA corporate bonds | debt | — | — | value 74,00,000 | 0 |
| Savings + liquid fund | cash | — | — | value 24,60,000 | 0 |

Derived (JS computes; these are the expected results for verification):
- Equity value ₹51,33,260 · MF ₹50,13,200 · Gold ₹40,81,000 · Debt ₹74,00,000 · Cash ₹24,60,000
- **Total ₹2,40,87,460 → "₹2.41 Cr"**
- Invested (equity+MF+gold) ₹1,16,02,200 → Unrealised P/L **+₹26,25,260 (+22.6%)**
- Allocation: equity 21.3% · MF 20.8% · gold 16.9% · debt 30.7% · cash 10.2%
- Top movers: ▲ TATAPOWER +2.1%, HDFCBANK +1.2% · ▼ TCS −4.2%, INFY −0.6%

Narrative facts reused across views (keep consistent): TCS −6.4% vs cost (Q1 miss); gold 16.9% vs one-pager band 10–14% → trim ~₹8L; cash 10.2% vs 8% floor; SGB +45.5%.

---

### Task 1: Dashboard scaffold — shell, tokens, sidebar navigation

**Files:**
- Create: `demo/investor-os-dashboard.html`

**Interfaces:**
- Produces: view containers `#view-overview`, `#view-holdings`, `#view-brief`, `#view-alerts`, `#view-profile` (one visible at a time via class `active`); function `switchView(id)`; CSS custom properties listed below. Later tasks fill the empty views and append `<script>` logic before `</body>`.

- [x] **Step 1: Create the file with shell, tokens, nav, and view switching**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paresh Karia — Investor OS (Demo)</title>
<style>
:root{
  --bg:#0c1017; --panel:#131a26; --panel-2:#1a2333; --line:#243044;
  --text:#e8ecf4; --muted:#8b98ad; --gold:#d4af6a; --emerald:#3ecf8e;
  --red:#f0655f; --font:"Segoe UI",-apple-system,"Inter",system-ui,sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:var(--font);min-height:100vh}
.app{display:grid;grid-template-columns:230px 1fr;min-height:100vh}
.sidebar{background:var(--panel);border-right:1px solid var(--line);padding:24px 14px;position:sticky;top:0;height:100vh}
.brand{font-size:15px;font-weight:600;letter-spacing:.04em;color:var(--gold);margin-bottom:2px}
.brand-sub{font-size:11px;color:var(--muted);margin-bottom:28px}
.nav-btn{display:flex;align-items:center;gap:10px;width:100%;padding:11px 14px;margin-bottom:4px;
  background:none;border:none;border-radius:10px;color:var(--muted);font-family:var(--font);
  font-size:13.5px;cursor:pointer;text-align:left}
.nav-btn:hover{background:var(--panel-2);color:var(--text)}
.nav-btn.active{background:var(--panel-2);color:var(--gold);font-weight:600}
.main{padding:26px 34px;max-width:1180px}
.topbar{display:flex;align-items:baseline;gap:14px;margin-bottom:24px;flex-wrap:wrap}
.topbar h1{font-size:20px;font-weight:600}
.topbar .date{color:var(--muted);font-size:13px}
.badge-demo{margin-left:auto;font-size:10.5px;letter-spacing:.12em;color:var(--gold);
  border:1px solid var(--gold);border-radius:99px;padding:4px 12px;opacity:.85}
.view{display:none}
.view.active{display:block;animation:fade .25s ease}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
@media (max-width:860px){.app{grid-template-columns:1fr}.sidebar{position:static;height:auto;display:flex;overflow-x:auto;padding:10px}.brand,.brand-sub{display:none}.main{padding:18px}}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand">INVESTOR OS</div>
    <div class="brand-sub">Private · Paresh Karia</div>
    <button class="nav-btn active" data-view="view-overview">◈ Overview</button>
    <button class="nav-btn" data-view="view-holdings">▤ Holdings</button>
    <button class="nav-btn" data-view="view-brief">⚡ Morning Brief</button>
    <button class="nav-btn" data-view="view-alerts">📱 Alerts &amp; Phone</button>
    <button class="nav-btn" data-view="view-profile">👤 Investor Profile</button>
  </aside>
  <main class="main">
    <div class="topbar">
      <h1>Paresh Karia — Investor OS</h1>
      <span class="date">Monday, 6 July 2026 · 7:00 AM IST</span>
      <span class="badge-demo">DEMO — SAMPLE DATA</span>
    </div>
    <section id="view-overview" class="view active"></section>
    <section id="view-holdings" class="view"></section>
    <section id="view-brief" class="view"></section>
    <section id="view-alerts" class="view"></section>
    <section id="view-profile" class="view"></section>
  </main>
</div>
<script>
function switchView(id){
  document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id===id));
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.toggle('active',b.dataset.view===id));
}
document.querySelectorAll('.nav-btn').forEach(b=>b.addEventListener('click',()=>switchView(b.dataset.view)));
</script>
</body>
</html>
```

- [x] **Step 2: Verify in browser**

Run: `start demo\investor-os-dashboard.html` (PowerShell). Expected: dark shell renders, header shows name/date/DEMO badge, all 5 sidebar buttons switch the (empty) views with the active highlight following.

- [x] **Step 3: Commit**

```bash
git add demo/investor-os-dashboard.html
git commit -m "feat(demo): dashboard shell, design tokens, sidebar navigation"
```

---

### Task 2: Data layer — portfolio object, INR formatters, series generator, self-tests

**Files:**
- Modify: `demo/investor-os-dashboard.html` (append a `<script>` block BEFORE the Task-1 script)

**Interfaces:**
- Produces (used by Tasks 3–6): `PORTFOLIO` (object), `inr(n)`, `inrShort(n)`, `pct(n)`, `computeTotals()` → `{totalValue, invested, unrealPL, unrealPLPct, dayPL, dayPLPct, cash, byClass:{equity,mf,gold,debt,cash}}`, `genSeries(points, startVal, endVal, seed)` → `number[]`, `SERIES` = `{ '1M':[], '3M':[], '6M':[], '1Y':[], 'ALL':[] }` all ending at `totalValue`.

- [x] **Step 1: Add the data + utils script**

```html
<script>
const PORTFOLIO = {
  holdings: [
    {name:'RELIANCE', cls:'equity', qty:500,  avg:2450, ltp:2912, day:0.8},
    {name:'HDFCBANK', cls:'equity', qty:800,  avg:1520, ltp:1748, day:1.2},
    {name:'TCS',      cls:'equity', qty:120,  avg:3650, ltp:3418, day:-4.2},
    {name:'INFY',     cls:'equity', qty:300,  avg:1385, ltp:1624, day:-0.6},
    {name:'ITC',      cls:'equity', qty:1500, avg:412,  ltp:465,  day:0.4},
    {name:'TATAPOWER',cls:'equity', qty:2000, avg:285,  ltp:342,  day:2.1},
    {name:'UTI Nifty 50 Index Fund (Direct-G)',   cls:'mf',   qty:18500, avg:148.20, ltp:172.40, day:0.5},
    {name:'Parag Parikh Flexi Cap (Direct-G)',    cls:'mf',   qty:22000, avg:71.50,  ltp:82.90,  day:0.5},
    {name:'Sovereign Gold Bonds (2019–22)',       cls:'gold', qty:550,   avg:5100,   ltp:7420,   day:0.2},
    {name:'Bank FDs + AAA corporate bonds',       cls:'debt', qty:1, avg:7400000, ltp:7400000, day:0},
    {name:'Savings + liquid fund',                cls:'cash', qty:1, avg:2460000, ltp:2460000, day:0},
  ]
};
const val = h => h.qty*h.ltp, cost = h => h.qty*h.avg;
function inr(n){ return '₹' + Math.round(n).toLocaleString('en-IN'); }
function inrShort(n){
  const a = Math.abs(n);
  if(a >= 1e7) return '₹' + (n/1e7).toFixed(2) + ' Cr';
  if(a >= 1e5) return '₹' + (n/1e5).toFixed(1) + ' L';
  return inr(n);
}
function pct(n){ return (n>=0?'+':'') + n.toFixed(1) + '%'; }
function computeTotals(){
  const byClass = {equity:0, mf:0, gold:0, debt:0, cash:0};
  let totalValue=0, invested=0, dayPL=0;
  for(const h of PORTFOLIO.holdings){
    const v = val(h); byClass[h.cls]+=v; totalValue+=v;
    if(['equity','mf','gold'].includes(h.cls)) invested += cost(h);
    dayPL += v - v/(1+h.day/100);
  }
  const marketVal = byClass.equity + byClass.mf + byClass.gold;
  const unrealPL = marketVal - invested;
  return { totalValue, invested, unrealPL,
    unrealPLPct: unrealPL/invested*100,
    dayPL, dayPLPct: dayPL/totalValue*100,
    cash: byClass.cash, byClass };
}
function genSeries(points, startVal, endVal, seed){
  let s = seed, out = [], v = startVal;
  const rand = () => (s = (s*1103515245 + 12345) % 2147483648) / 2147483648;
  for(let i=0;i<points;i++){
    const drift = (endVal-v)/(points-i);
    v += drift + (rand()-0.5) * startVal * 0.008;
    out.push(v);
  }
  out[points-1] = endVal;
  return out;
}
const T = computeTotals();
const SERIES = {
  '1M':  genSeries(22,  T.totalValue*0.985, T.totalValue, 7),
  '3M':  genSeries(64,  T.totalValue*0.952, T.totalValue, 11),
  '6M':  genSeries(126, T.totalValue*0.90,  T.totalValue, 13),
  '1Y':  genSeries(250, T.totalValue*0.82,  T.totalValue, 17),
  'ALL': genSeries(360, T.totalValue*0.62,  T.totalValue, 23),
};
function runSelfTests(){
  const t = computeTotals(), r = [];
  const eq = (name,got,want) => r.push([name, Math.round(got)===want, Math.round(got), want]);
  eq('totalValue', t.totalValue, 24087460);
  eq('equity',     t.byClass.equity, 5133260);
  eq('mf',         t.byClass.mf, 5013200);
  eq('gold',       t.byClass.gold, 4081000);
  eq('invested',   t.invested, 11602200);
  eq('unrealPL',   t.unrealPL, 2625260);
  const fails = r.filter(x=>!x[1]);
  const div = document.createElement('div');
  div.style.cssText='position:fixed;bottom:0;left:0;right:0;padding:8px 16px;font:12px monospace;z-index:99;background:'+(fails.length?'#7a1f1f':'#14532d');
  div.textContent = 'SELFTEST: ' + (r.length-fails.length) + '/' + r.length + ' passed ' +
    fails.map(f=>` | FAIL ${f[0]}: got ${f[2]} want ${f[3]}`).join('');
  document.body.appendChild(div);
}
if(location.hash === '#selftest') addEventListener('DOMContentLoaded', runSelfTests);
</script>
```

- [x] **Step 2: Run the self-tests (this is the failing-test/passing-test cycle for a static page)**

Run: `start "" "demo\investor-os-dashboard.html#selftest"`
Expected: green banner **"SELFTEST: 6/6 passed"**. If red, the data object has a typo — fix until 6/6.

- [x] **Step 3: Commit**

```bash
git add demo/investor-os-dashboard.html
git commit -m "feat(demo): portfolio data layer, INR formatters, chart series, self-tests"
```

---

### Task 3: Overview view — hero metrics, area chart with range tabs, donut, top movers

**Files:**
- Modify: `demo/investor-os-dashboard.html` (fill `#view-overview`; append render script after Task-2 script; add view CSS to the `<style>` block)

**Interfaces:**
- Consumes: `computeTotals()`, `SERIES`, `inrShort`, `inr`, `pct`, `PORTFOLIO`, `val`.
- Produces: `renderAreaChart(rangeKey)` and `renderDonut()` (only used within this view).

- [x] **Step 1: Add Overview markup inside `#view-overview`**

```html
<div class="cards" id="hero-cards"></div>
<div class="panel">
  <div class="panel-head">
    <h2>Portfolio Value</h2>
    <div class="range-tabs" id="range-tabs">
      <button data-r="1M">1M</button><button data-r="3M">3M</button>
      <button data-r="6M" class="active">6M</button><button data-r="1Y">1Y</button>
      <button data-r="ALL">ALL</button>
    </div>
  </div>
  <svg id="area-chart" viewBox="0 0 720 240" preserveAspectRatio="none" style="width:100%;height:240px"></svg>
</div>
<div class="two-col">
  <div class="panel"><h2>Asset Allocation</h2><div class="donut-wrap">
    <svg id="donut" viewBox="0 0 160 160" style="width:160px;height:160px"></svg>
    <div id="donut-legend"></div></div></div>
  <div class="panel"><h2>Top Movers Today</h2><div id="movers"></div></div>
</div>
```

- [x] **Step 2: Add Overview CSS to the style block**

```css
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 20px}
.card .lbl{font-size:11.5px;letter-spacing:.08em;color:var(--muted);text-transform:uppercase;margin-bottom:8px}
.card .num{font-size:24px;font-weight:650}
.card .sub{font-size:12.5px;margin-top:4px}
.up{color:var(--emerald)} .down{color:var(--red)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:18px}
.panel h2{font-size:14px;font-weight:600;color:var(--muted);letter-spacing:.05em;text-transform:uppercase;margin-bottom:14px}
.panel-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.range-tabs button{background:none;border:1px solid var(--line);color:var(--muted);border-radius:8px;
  padding:4px 12px;margin-left:6px;font-size:12px;cursor:pointer;font-family:var(--font)}
.range-tabs button.active{border-color:var(--gold);color:var(--gold)}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media (max-width:860px){.two-col{grid-template-columns:1fr}}
.donut-wrap{display:flex;gap:22px;align-items:center;flex-wrap:wrap}
.legend-row{display:flex;align-items:center;gap:8px;font-size:13px;margin-bottom:7px}
.legend-dot{width:10px;height:10px;border-radius:3px;flex:none}
.mover{display:flex;justify-content:space-between;padding:9px 2px;border-bottom:1px solid var(--line);font-size:13.5px}
.mover:last-child{border-bottom:none}
```

- [x] **Step 3: Add the Overview render script**

```html
<script>
(function(){
  const t = computeTotals();
  document.getElementById('hero-cards').innerHTML = `
    <div class="card"><div class="lbl">Total Value</div><div class="num">${inrShort(t.totalValue)}</div>
      <div class="sub muted">${inr(t.totalValue)}</div></div>
    <div class="card"><div class="lbl">Unrealised P/L</div>
      <div class="num up">${inrShort(t.unrealPL)}</div><div class="sub up">${pct(t.unrealPLPct)} on invested</div></div>
    <div class="card"><div class="lbl">Today</div>
      <div class="num ${t.dayPL>=0?'up':'down'}">${inrShort(t.dayPL)}</div>
      <div class="sub ${t.dayPL>=0?'up':'down'}">${pct(t.dayPLPct)}</div></div>
    <div class="card"><div class="lbl">Cash Available</div><div class="num">${inrShort(t.cash)}</div>
      <div class="sub muted">${(t.cash/t.totalValue*100).toFixed(1)}% of portfolio · floor 8%</div></div>`;

  window.renderAreaChart = function(key){
    const s = SERIES[key], W=720, H=240, P=10;
    const min = Math.min(...s)*0.998, max = Math.max(...s)*1.002;
    const x = i => P + i*(W-2*P)/(s.length-1);
    const y = v => H-P - (v-min)*(H-2*P)/(max-min);
    const pts = s.map((v,i)=>`${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    document.getElementById('area-chart').innerHTML = `
      <defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#d4af6a" stop-opacity="0.35"/>
        <stop offset="1" stop-color="#d4af6a" stop-opacity="0"/></linearGradient></defs>
      <polygon points="${x(0)},${H-P} ${pts} ${x(s.length-1)},${H-P}" fill="url(#ag)"/>
      <polyline points="${pts}" fill="none" stroke="#d4af6a" stroke-width="2"/>`;
    document.querySelectorAll('#range-tabs button').forEach(b=>b.classList.toggle('active',b.dataset.r===key));
  };
  document.querySelectorAll('#range-tabs button').forEach(b=>b.addEventListener('click',()=>renderAreaChart(b.dataset.r)));
  renderAreaChart('6M');

  const CLS = [['equity','Direct Equity','#d4af6a'],['mf','Mutual Funds','#3ecf8e'],
               ['gold','Gold (SGB)','#e8c987'],['debt','Debt & FD','#5b8dd6'],['cash','Cash','#8b98ad']];
  window.renderDonut = function(){
    const C=2*Math.PI*58; let off=0, seg='', leg='';
    for(const [k,label,color] of CLS){
      const frac = t.byClass[k]/t.totalValue;
      seg += `<circle r="58" cx="80" cy="80" fill="none" stroke="${color}" stroke-width="20"
        stroke-dasharray="${(frac*C).toFixed(1)} ${C.toFixed(1)}" stroke-dashoffset="${(-off*C).toFixed(1)}"
        transform="rotate(-90 80 80)"/>`;
      leg += `<div class="legend-row"><span class="legend-dot" style="background:${color}"></span>
        ${label} — ${(frac*100).toFixed(1)}% <span style="color:var(--muted)">· ${inrShort(t.byClass[k])}</span></div>`;
      off += frac;
    }
    document.getElementById('donut').innerHTML = seg;
    document.getElementById('donut-legend').innerHTML = leg;
  };
  renderDonut();

  const movers = PORTFOLIO.holdings.filter(h=>h.cls==='equity')
    .sort((a,b)=>b.day-a.day);
  const pick = [...movers.slice(0,2), ...movers.slice(-2)];
  document.getElementById('movers').innerHTML = pick.map(h=>
    `<div class="mover"><span>${h.name}</span>
     <span class="${h.day>=0?'up':'down'}">${pct(h.day)} · ${inrShort(val(h))}</span></div>`).join('');
})();
</script>
```

- [x] **Step 4: Verify**

Open the file. Expected on Overview: Total Value **₹2.41 Cr**, Unrealised P/L **₹26.25 L (+22.6%)**, Cash **₹24.6 L (10.2%)**; gold area chart redraws when clicking 1M/3M/6M/1Y/ALL; donut legend shows equity 21.3 / MF 20.8 / gold 16.9 / debt 30.7 / cash 10.2; movers show TATAPOWER +2.1% and TCS −4.2%. Re-open with `#selftest` → still 6/6.

- [x] **Step 5: Commit**

```bash
git add demo/investor-os-dashboard.html
git commit -m "feat(demo): overview view — hero metrics, SVG area chart, donut, movers"
```

---

### Task 4: Holdings view

**Files:**
- Modify: `demo/investor-os-dashboard.html` (fill `#view-holdings`; append script; reuse existing CSS + add table CSS)

**Interfaces:**
- Consumes: `PORTFOLIO`, `val`, `cost`, `inr`, `inrShort`, `pct`.

- [x] **Step 1: Add markup + CSS**

Markup inside `#view-holdings`:
```html
<div id="holdings-groups"></div>
```
CSS to add:
```css
.htable{width:100%;border-collapse:collapse;font-size:13.5px}
.htable th{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);
  text-align:right;padding:8px 10px;border-bottom:1px solid var(--line)}
.htable th:first-child,.htable td:first-child{text-align:left}
.htable td{padding:10px;text-align:right;border-bottom:1px solid var(--line)}
.htable tr:last-child td{border-bottom:none}
.grp-title{font-size:13px;color:var(--gold);letter-spacing:.06em;margin:4px 0 10px;text-transform:uppercase}
```

- [x] **Step 2: Add render script**

```html
<script>
(function(){
  const GROUPS = [['equity','Direct Equity (NSE)'],['mf','Mutual Funds'],['gold','Gold'],['debt','Debt & FD'],['cash','Cash']];
  let html = '';
  for(const [k,title] of GROUPS){
    const rows = PORTFOLIO.holdings.filter(h=>h.cls===k);
    const sub = rows.reduce((a,h)=>a+val(h),0);
    html += `<div class="panel"><div class="grp-title">${title} — ${inrShort(sub)}</div>
      <div style="overflow-x:auto"><table class="htable">
      <tr><th>Instrument</th><th>Qty</th><th>Avg Cost</th><th>LTP / NAV</th><th>Value</th><th>P/L %</th><th>Day</th></tr>` +
      rows.map(h=>{
        const plPct = (h.ltp-h.avg)/h.avg*100;
        const simple = (k==='debt'||k==='cash');
        return `<tr><td>${h.name}</td>
          <td>${simple?'—':h.qty.toLocaleString('en-IN')}</td>
          <td>${simple?'—':'₹'+h.avg.toLocaleString('en-IN')}</td>
          <td>${simple?'—':'₹'+h.ltp.toLocaleString('en-IN')}</td>
          <td>${inrShort(val(h))}</td>
          <td class="${plPct>=0?'up':'down'}">${simple?'—':pct(plPct)}</td>
          <td class="${h.day>=0?'up':'down'}">${simple?'—':pct(h.day)}</td></tr>`;
      }).join('') + '</table></div></div>';
  }
  document.getElementById('holdings-groups').innerHTML = html;
})();
</script>
```

- [x] **Step 3: Verify**

Holdings view shows 5 grouped panels; TCS row red at **−6.4%** P/L and **−4.2%** day; SGB shows **+45.5%**; debt/cash rows show em-dashes. Table scrolls horizontally on narrow window rather than breaking layout.

- [x] **Step 4: Commit**

```bash
git add demo/investor-os-dashboard.html
git commit -m "feat(demo): holdings view grouped by asset class"
```

---

### Task 5: Morning Brief view — typewriter brief + weekly newsletter sample

**Files:**
- Modify: `demo/investor-os-dashboard.html` (fill `#view-brief`; append script + CSS)

**Interfaces:**
- Consumes: none beyond Task-1 shell (copy is static).
- Produces: `typewriteBrief()` bound to the generate button.

- [x] **Step 1: Add markup + CSS**

Markup inside `#view-brief`:
```html
<div class="panel">
  <div class="panel-head"><h2>AI Morning Brief</h2>
    <button id="gen-brief" class="btn-gold">⚡ Generate Morning Brief</button></div>
  <pre id="brief-out" class="brief-out muted">Click “Generate Morning Brief” — the AI reads your portfolio, your investor one-pager, and overnight markets, then writes this for you every morning.</pre>
</div>
<div class="panel">
  <h2>Weekly Newsletter (sample)</h2>
  <div class="news">
    <div class="news-head">THE WEEKLY BRIEF — Week 27, 2026</div>
    <div class="news-sub">Portfolio ₹2.41 Cr · +0.9% this week · +22.6% unrealised overall</div>
    <div class="news-sec">WHAT MOVED</div>
    <p><span class="up">▲ TATAPOWER +5.2%</span> — capex approval for 2 GW solar pipeline</p>
    <p><span class="up">▲ RELIANCE +2.1%</span> — AGM expectations building</p>
    <p><span class="down">▼ TCS −6.8%</span> — Q1 miss; downgrades from 3 brokerages</p>
    <div class="news-sec">NEWS YOU MAY HAVE MISSED</div>
    <p>• SEBI circular on F&amp;O position limits — no impact on your cash-only book.</p>
    <p>• New SGB redemption window opens 15 July — relevant to your 2019 tranche.</p>
    <p>• Parag Parikh Flexi Cap raised overseas allocation to 28% — adds slight USD exposure to your MF book.</p>
    <div class="news-sec">ONE THING TO ACT ON</div>
    <p>Gold allocation at 16.9% vs your 10–14% band — trim decision pending your review.</p>
  </div>
</div>
```
CSS:
```css
.btn-gold{background:linear-gradient(135deg,#d4af6a,#b8934e);color:#14100a;border:none;border-radius:10px;
  padding:10px 18px;font-family:var(--font);font-size:13.5px;font-weight:650;cursor:pointer}
.btn-gold:hover{filter:brightness(1.08)}
.brief-out{white-space:pre-wrap;font-family:var(--font);font-size:13.5px;line-height:1.65;min-height:120px}
.muted{color:var(--muted)}
.news{font-size:13.5px;line-height:1.7}
.news p{margin:2px 0}
.news-head{font-weight:700;letter-spacing:.06em;color:var(--gold)}
.news-sub{color:var(--muted);font-size:12.5px;margin-bottom:10px}
.news-sec{font-size:11px;letter-spacing:.1em;color:var(--muted);margin:14px 0 4px}
```

- [x] **Step 2: Add the brief text + typewriter script (this exact copy)**

```html
<script>
const BRIEF_TEXT = `MORNING BRIEF — Monday, 6 July 2026 · 7:00 AM IST

MARKETS OVERNIGHT
• Nifty 50 closed Friday at 26,840 (+0.4%); GIFT Nifty indicates a flat-to-positive open.
• US markets mixed — S&P 500 +0.2%, Nasdaq −0.3% ahead of the July Fed minutes.
• Brent at $78.4 (+1.8% for the week); gold at ₹7,420/g near all-time highs.

IMPACT ON YOUR PORTFOLIO
• TCS (120 shares, −4.2% Friday) — Q1 missed street estimates on BFSI weakness. You are now −6.4% vs cost. IT commentary pushes recovery to H2. Thesis check due.
• RELIANCE (500 shares, +19% vs cost) — AGM next month; street expects new-energy capex announcements. No action needed.
• HDFCBANK (800 shares) — RBI held the repo rate Friday; NIM pressure easing. Thesis intact.
• Gold SGBs (+45.5%) — now 16.9% of portfolio vs your 10–14% band. The 2019 tranche is past its 5-year exit window; redemption is tax-free.

SUGGESTED ACTIONS — checked against your one-pager
1. TCS: your Rule 2 — “cut losers on thesis break, not price action.” Thesis strained, not broken. Wait for management commentary Wednesday; no panic action today.
2. Gold: a ~₹8L trim from the 2019 SGB tranche brings allocation back inside band via the tax-free route.
3. Cash at ₹24.6L (10.2%) is above your 8% floor — dry powder available if IT weakness spreads to quality names.

Generated from: your holdings + your investor one-pager + overnight market data. (Demo — sample data.)`;

function typewriteBrief(){
  const out = document.getElementById('brief-out');
  const btn = document.getElementById('gen-brief');
  btn.disabled = true; btn.textContent = 'Analysing portfolio…';
  out.classList.remove('muted'); out.textContent = '';
  let i = 0;
  const step = () => {
    out.textContent = BRIEF_TEXT.slice(0, i);
    i += 3;
    if(i <= BRIEF_TEXT.length + 2) requestAnimationFrame(step);
    else { btn.disabled = false; btn.textContent = '⚡ Generate Morning Brief'; }
  };
  setTimeout(step, 600);
}
document.getElementById('gen-brief').addEventListener('click', typewriteBrief);
</script>
```

- [x] **Step 3: Verify**

Click the button: label flips to "Analysing portfolio…", brief types out smoothly (~4–6 s), button re-enables after. Newsletter card renders below with gold/emerald/red accents. Numbers agree with Overview (16.9%, ₹24.6L, −6.4%).

- [x] **Step 4: Commit**

```bash
git add demo/investor-os-dashboard.html
git commit -m "feat(demo): morning brief typewriter + weekly newsletter sample"
```

---

### Task 6: Alerts & Phone view — phone frame with sequenced Telegram messages

**Files:**
- Modify: `demo/investor-os-dashboard.html` (fill `#view-alerts`; append script + CSS)

**Interfaces:**
- Consumes: Task-1 `switchView` behaviour (animation triggers when view becomes visible).
- Produces: `playAlerts()`; nav button for `view-alerts` gets an extra listener to replay the sequence.

- [x] **Step 1: Add markup + CSS**

Markup inside `#view-alerts`:
```html
<div class="alerts-grid">
  <div class="phone">
    <div class="phone-notch"></div>
    <div class="phone-screen">
      <div class="tg-header">✈️ Investor OS Bot</div>
      <div id="tg-feed"></div>
    </div>
  </div>
  <div class="panel">
    <h2>How this works</h2>
    <ol class="howto">
      <li>A free Telegram bot is created once (via BotFather — takes ~3 minutes).</li>
      <li>Every morning at 7:00 AM the AI reads your portfolio + your one-pager + overnight news, and sends the brief to your phone.</li>
      <li>Price and news alerts fire during market hours only for things that touch <em>your</em> holdings — no noise.</li>
      <li>You reply to the bot to ask follow-up questions; answers use your full investor profile.</li>
    </ol>
    <p class="muted" style="font-size:12.5px;margin-top:12px">No app to build — Telegram is free and already on the phone. WhatsApp is possible later via the Business API.</p>
  </div>
</div>
```
CSS:
```css
.alerts-grid{display:grid;grid-template-columns:300px 1fr;gap:22px;align-items:start}
@media (max-width:860px){.alerts-grid{grid-template-columns:1fr}}
.phone{background:#05070b;border:2px solid var(--line);border-radius:34px;padding:12px;width:300px;margin:0 auto}
.phone-notch{width:90px;height:18px;background:#05070b;border:2px solid var(--line);border-top:none;
  border-radius:0 0 12px 12px;margin:-12px auto 8px}
.phone-screen{background:#0e1621;border-radius:22px;min-height:480px;padding:12px;overflow:hidden}
.tg-header{font-size:13px;font-weight:650;padding:6px 4px 12px;border-bottom:1px solid #1c2a3a;margin-bottom:12px}
.tg-msg{background:#182533;border-radius:12px 12px 12px 4px;padding:10px 12px;font-size:12.5px;
  line-height:1.55;margin-bottom:10px;opacity:0;transform:translateY(8px);transition:all .4s ease}
.tg-msg.show{opacity:1;transform:none}
.tg-time{display:block;font-size:10.5px;color:#6d829b;margin-top:6px;text-align:right}
.howto{padding-left:18px;font-size:13.5px;line-height:1.9}
```

- [x] **Step 2: Add messages + sequencing script (this exact copy)**

```html
<script>
const TG_MSGS = [
  {t:'7:00 AM', txt:'☀️ <b>Morning Brief — Mon 6 Jul</b><br>• Nifty flat-to-positive open expected<br>• TCS −4.2% Friday (you hold 120)<br>• Gold now 16.9% of portfolio — above your band<br>• Cash ₹24.6L (10.2%) — above floor<br>Full brief on your dashboard →'},
  {t:'9:47 AM', txt:'⚠️ <b>Price alert: TCS ₹3,418 (−4.2%)</b> on Q1 earnings miss.<br>Your position: 120 shares, −6.4% vs cost.<br>Rule 2 reminder: thesis break, not price action.'},
  {t:'1:15 PM', txt:'📰 <b>News: RBI keeps repo at 5.25%.</b><br>HDFCBANK +1.2%. NIM pressure easing — holding thesis intact.'},
];
function playAlerts(){
  const feed = document.getElementById('tg-feed');
  feed.innerHTML = TG_MSGS.map(m=>
    `<div class="tg-msg">${m.txt}<span class="tg-time">${m.t} ✓✓</span></div>`).join('');
  feed.querySelectorAll('.tg-msg').forEach((el,i)=>setTimeout(()=>el.classList.add('show'), 500 + i*900));
}
document.querySelector('[data-view="view-alerts"]').addEventListener('click', playAlerts);
</script>
```

- [x] **Step 3: Verify**

Click "Alerts & Phone" in the sidebar: three Telegram bubbles slide in one after another inside the phone frame; timestamps + ✓✓ ticks visible; clicking the nav button again replays. "How this works" panel renders beside (stacks below on narrow width).

- [x] **Step 4: Commit**

```bash
git add demo/investor-os-dashboard.html
git commit -m "feat(demo): alerts view — phone frame with sequenced Telegram messages"
```

---

### Task 7: Sample investor one-pager MD

**Files:**
- Create: `prompts/sample-investor-one-pager.md`

**Interfaces:**
- Produces: the sample profile content. Task 8 renders a condensed version of THIS content in the dashboard — keep names/numbers identical (bands 10–14% gold, 8% cash floor, Rule 2 wording, no-F&O rule).

- [x] **Step 1: Create the file with exactly this content**

```markdown
# Investor One-Pager — A. Mehta  *(SAMPLE — fictional profile for demonstration)*

**Last updated:** 2026-07-06
**Operating base:** Mumbai, India · Resident · New tax regime

---

## North Star
Compound the equity and gold books aggressively till 2032, then shift toward income and preservation. Keep a floor of FDs and gold that covers five years of family expenses, so no market event ever forces a distressed sale. The business funds life; the portfolio compounds untouched.

---

## Core Philosophy
- **Quality compounders over story stocks** — 8–10 positions I understand end to end.
- **Cycles, not tips** — no position ever originates from a WhatsApp or Telegram tip.
- **Gold is insurance, not a trade** — held in SGBs for the tax-free maturity; rebalanced yearly.
- **Dry powder is a position** — a cash floor is maintained at all times, deployed only into broad corrections.
- **The business is the biggest asset** — portfolio risk is sized after accounting for business risk, not before.

---

## Time Horizon
Three books. Tactical (under 1 year) — small, opportunistic, capped. Core (5–10 years) — direct equity and flexi-cap funds, the compounding engine. Generational (10+ years) — index funds and SGBs, never touched for lifestyle. Capital does not move between books except at the yearly review.

---

## Mindset Rules
1. Never buy on a tip. A written two-line thesis must exist before money moves.
2. Cut losers on thesis break, not on price action.
3. No leverage, no F&O, no intraday. Ever.
4. Sleep test — any single position above 15% of the portfolio must justify itself in writing.
5. Rebalance to bands, not feelings: equity+MF 35–45%, gold 10–14%, debt+cash 40–50%, cash floor 8%.
6. Full portfolio review every October — before Diwali, not during it.
7. Tax planning happens in March by calendar, not in a crash by panic.

---

## Personal Nuances
- **Tax:** New regime. Equity LTCG above ₹1.25L taxed at 12.5%; STCG 20% — prefer holding periods past one year. SGB redemption at maturity is tax-free — the preferred exit route for gold.
- **Income & liquidity:** Business income funds the household entirely. The portfolio is locked-up growth capital — no withdrawals. ₹3L/month DCA into index funds on the last business day.
- **Time budget:** Maximum 3 hours/week. Anything needing more attention than that is automatically disqualified.
- **Family:** Spouse prefers guaranteed instruments — the FD floor is non-negotiable regardless of opportunity cost.
- **Public exposure:** CEO profile — no public discussion of specific positions that could constrain future exits.

---

## Anti-Portfolio
- No F&O, no intraday, no leveraged products — regardless of upside.
- No unlisted "pre-IPO opportunities" pitched by acquaintances.
- No crypto beyond a 1% experiment, if at all.
- No single stock above 15% of the portfolio.
- Nothing I cannot explain to my family in two minutes.

---

*Reviewed quarterly. Material changes require a 7-day cooldown before execution.*
```

- [x] **Step 2: Verify**

Read the file once top-to-bottom: no `[bracketed]` placeholders remain; the numbers match the dashboard narrative (gold band 10–14%, cash floor 8%, Rule 2 = thesis-break rule, 15% position cap).

- [x] **Step 3: Commit**

```bash
git add prompts/sample-investor-one-pager.md
git commit -m "feat(prompts): sample investor one-pager (fictional, Indian context)"
```

---

### Task 8: Investor Profile view in dashboard

**Files:**
- Modify: `demo/investor-os-dashboard.html` (fill `#view-profile`; static HTML, no script needed)

**Interfaces:**
- Consumes: content of `prompts/sample-investor-one-pager.md` (Task 7) — condensed, verbatim phrasing.

- [x] **Step 1: Add markup inside `#view-profile` + CSS**

```html
<div class="callout">
  <b>The point of this page:</b> everything the AI says on this dashboard — every brief, every alert, every suggestion — is filtered through <b>one editable file that you own</b>. Edit the file, and the advice changes. This sample profile below was generated by a 20-minute AI interview.
</div>
<div class="panel op">
  <div class="op-title">Investor One-Pager — A. Mehta <span class="badge-demo" style="margin-left:8px">SAMPLE</span></div>
  <p class="muted" style="font-size:12.5px;margin:4px 0 16px">Last updated 2026-07-06 · Mumbai, India · New tax regime</p>

  <div class="news-sec">NORTH STAR</div>
  <p>Compound the equity and gold books aggressively till 2032, then shift toward income and preservation. Keep a floor of FDs and gold covering five years of family expenses, so no market event ever forces a distressed sale. The business funds life; the portfolio compounds untouched.</p>

  <div class="news-sec">CORE PHILOSOPHY</div>
  <p>• <b>Quality compounders over story stocks</b> — 8–10 positions understood end to end.</p>
  <p>• <b>Cycles, not tips</b> — no position ever originates from a WhatsApp or Telegram tip.</p>
  <p>• <b>Gold is insurance, not a trade</b> — SGBs for the tax-free maturity; rebalanced yearly.</p>
  <p>• <b>Dry powder is a position</b> — cash floor at all times, deployed only into broad corrections.</p>
  <p>• <b>The business is the biggest asset</b> — portfolio risk is sized after business risk.</p>

  <div class="news-sec">MINDSET RULES</div>
  <p>1. Never buy on a tip — a written two-line thesis before money moves.</p>
  <p>2. Cut losers on thesis break, not on price action.</p>
  <p>3. No leverage, no F&amp;O, no intraday. Ever.</p>
  <p>4. Sleep test — any position above 15% must justify itself in writing.</p>
  <p>5. Rebalance to bands: equity+MF 35–45% · gold 10–14% · debt+cash 40–50% · cash floor 8%.</p>
  <p>6. Full review every October — before Diwali, not during it.</p>
  <p>7. Tax planning in March by calendar, not in a crash by panic.</p>

  <div class="news-sec">ANTI-PORTFOLIO</div>
  <p>No F&amp;O / intraday / leverage · no unlisted "pre-IPO" pitches from acquaintances · no crypto beyond a 1% experiment · no single stock above 15% · nothing that can't be explained to family in two minutes.</p>
</div>
<div class="callout gold">
  <b>How Sir gets his own version:</b> paste our interview prompt into Claude or ChatGPT → answer questions for ~20 minutes (voice input works well) → receive this exact document about yourself → edit it anytime in Word or any text editor. The dashboard and alerts then obey it.
</div>
```
CSS:
```css
.callout{background:var(--panel-2);border:1px solid var(--line);border-left:3px solid var(--emerald);
  border-radius:12px;padding:14px 18px;font-size:13.5px;line-height:1.6;margin-bottom:18px}
.callout.gold{border-left-color:var(--gold)}
.op p{font-size:13.5px;line-height:1.7;margin:3px 0}
.op-title{font-size:16px;font-weight:650}
```

- [x] **Step 2: Verify**

Profile view shows the green intro callout, the condensed one-pager, and the gold "how Sir gets his own version" callout. Wording matches Task 7's file (bands, rules).

- [x] **Step 3: Commit**

```bash
git add demo/investor-os-dashboard.html
git commit -m "feat(demo): investor profile view with one-pager and explainer callouts"
```

---

### Task 9: India-adapted interview prompt

**Files:**
- Create: `prompts/investor-interview-prompt.md` (start from a copy of `ASSET INVESTOR PROMPT.md` in repo root; apply the exact edits below, keep everything else verbatim)

**Interfaces:**
- Consumes: `ASSET INVESTOR PROMPT.md` (repo root, reference — do not modify it).
- Produces: the file Paresh pastes into Claude.ai/ChatGPT.

- [x] **Step 1: Copy the reference file**

```bash
cp "ASSET INVESTOR PROMPT.md" prompts/investor-interview-prompt.md
```

- [x] **Step 2: Apply these exact edits**

**(a)** Insert at the very top, BEFORE `# System Prompt — Investor Strategy Architect`:

```markdown
<!--
HOW TO USE (for Paresh Sir):
1. Open a NEW chat in Claude (claude.ai) or ChatGPT.
2. Paste this ENTIRE file as the first message. Send.
3. The AI will interview you — one question at a time, ~20–30 minutes.
   TIP: use voice input (the mic button) to answer faster.
4. At the end it produces your "Investor One-Pager". Save it as a .md file
   (or paste into Word). You own and edit this file — it becomes the
   system prompt for every future portfolio analysis, brief, and alert.
-->
```

**(b)** In **Phase 1 — Situation & Constraints**, replace the line
`- Operating base, residency, tax regime, expected duration of current setup`
with:

```markdown
- Operating base, residency status (Resident / NRI / RNOR), and tax regime (old vs new); expected duration of current setup
- Nature of income: business income vs salary vs professional fees — and how that affects tax treatment
```

**(c)** In **Phase 2 — Capital & Horizon**, after the line `- Rough capital base (bands are fine; exact figures unnecessary)`, insert:

```markdown
- Current spread across Indian asset classes: direct equity, mutual funds / PMS / AIF, gold (physical / SGB), real estate, FDs & debt, EPF/PPF/NPS, US or global investing via LRS, crypto if any
```

**(d)** In **Phase 5 — Preferences & Anti-Preferences**, replace
`- Sources they trust and sources they actively distrust`
with:

```markdown
- Sources they trust and sources they actively distrust (brokerage research, TV channels, WhatsApp/Telegram tip groups, finfluencers, friends' recommendations)
```

**(e)** In the **Output Specification** one-pager template, replace the `**Operating base:**` line with:

```markdown
**Operating base:** [City, India · residency status · old/new tax regime]
```

and in the `## Personal Nuances` block of the template, replace the description with:

```markdown
[Bulleted list. Tax (regime, LTCG/STCG treatment, SGB/EPF/PPF specifics), income & liquidity in ₹, time budget, family constraints, behavioural blind spots, routines, public-exposure rules. The constraints that make this strategy *theirs* and not transferable to anyone else. All amounts in ₹ (lakh/crore).]
```

- [x] **Step 3: Verify by live test**

Paste the full file into a fresh Claude chat (claude.ai). Expected: it responds ONLY with the opening line ("Let's build your investor one-pager. Start by telling me where you live…") and waits — no document dump, no multiple questions. If it dumps the document or asks 3+ questions at once, the edits broke the structure; diff against the reference and fix.

- [x] **Step 4: Commit**

```bash
git add prompts/investor-interview-prompt.md
git commit -m "feat(prompts): India-adapted chat interview prompt for investor one-pager"
```

---

### Task 10: Investor OS builder prompt (Cowork version)

**Files:**
- Create: `prompts/investor-os-builder-prompt.md` (start from a copy of `cowork-investor-os-system-prompt.md` in repo root; apply the exact edits below, keep everything else verbatim)

**Interfaces:**
- Consumes: `cowork-investor-os-system-prompt.md` (repo root, reference — do not modify it).
- Produces: the prompt Hemant uses with Paresh in Claude Cowork/Code in Phase 2.

- [x] **Step 1: Copy the reference file**

```bash
cp cowork-investor-os-system-prompt.md prompts/investor-os-builder-prompt.md
```

- [x] **Step 2: Apply these exact edits**

**(a)** Insert at the very top, BEFORE the first heading:

```markdown
<!--
WHEN TO USE (for Hemant): Phase 2 of the Investor OS project — the sit-down
session with Paresh Sir in Claude Cowork or Claude Code. This builds the full
memory folder on his machine (instructions.md, memory.md, one-pager,
financials/). If Sir already completed the chat interview
(investor-interview-prompt.md), give this prompt his finished one-pager and
tell it to skip re-asking answered questions — it should confirm, not repeat.
-->
```

**(b)** In **Phase 1 — Identity & Operating Base**, replace
`- City, country, residency status, tax regime`
with:

```markdown
- City, country, residency status (Resident / NRI / RNOR), tax regime (old vs new)
```

**(c)** In **Phase 1**, replace `- Primary currency` with:

```markdown
- Primary currency (default ₹; note any USD exposure via LRS)
```

**(d)** In the `pnl-summary.md` template, replace the line
`Rolling 6-month view. All figures [currency]. Updated monthly after month-end close.`
with:

```markdown
Rolling 6-month view. All figures in ₹ (lakh/crore where natural). Updated monthly after month-end close.
```

- [x] **Step 3: Verify**

Read the diff vs the reference (`git diff --no-index cowork-investor-os-system-prompt.md prompts/investor-os-builder-prompt.md`): only the four edits above appear; the file templates, rules, and final instructions are otherwise byte-identical.

- [x] **Step 4: Commit**

```bash
git add prompts/investor-os-builder-prompt.md
git commit -m "feat(prompts): India-adapted Investor OS builder prompt for Cowork phase"
```

---

### Task 11: README with demo script and roadmap

**Files:**
- Create: `README.md` (repo root)

**Interfaces:**
- Consumes: everything built in Tasks 1–10 (file names must match exactly).

- [x] **Step 1: Create README.md with exactly this content**

```markdown
# Investor OS — Demo Package for Paresh Karia

An AI-powered personal investment system, modelled on the "AI Financial
Advisor" architecture (AI Edge, https://youtu.be/VvuHr46wF-4). This repo is
**Phase 1: the demo/pitch package** — everything here uses fictional sample
data.

## What's in here

| File | What it is |
|---|---|
| `demo/investor-os-dashboard.html` | Interactive dashboard mockup — double-click to open, works offline |
| `prompts/investor-interview-prompt.md` | Paste into Claude/ChatGPT → AI interviews Sir → produces his investor one-pager |
| `prompts/investor-os-builder-prompt.md` | For Phase 2: builds the full memory folder in Claude Cowork/Code |
| `prompts/sample-investor-one-pager.md` | Filled fictional example of what the interview produces |
| `docs/superpowers/specs/` · `docs/superpowers/plans/` | Design spec and implementation plan |

## Demo script (10 minutes, in this order)

1. **Open the dashboard** (`demo/investor-os-dashboard.html`).
2. **Overview** — "your whole net worth in one place, in ₹, updated live in
   the real version" (charts, allocation donut, top movers).
3. **Holdings** — grouped by asset class; point at TCS in red.
4. **Morning Brief** — click ⚡ Generate. While it types: "every morning at
   7 AM this reads your portfolio, YOUR rules, and overnight news — this is
   the newsletter, personalised to you." Scroll to the weekly newsletter.
5. **Alerts & Phone** — the Telegram sequence plays; "this is your phone at
   7 AM — free, no app to build."
6. **Investor Profile** — the punchline: "all of this obeys ONE file that
   you own and can edit in Word. The AI writes that file by interviewing
   you for 20 minutes." Show `prompts/investor-interview-prompt.md`.
7. Ask for approval to proceed to Phase 2.

## Roadmap

- **Phase 1 (this repo):** demo package → Sir's approval.
- **Phase 2:** run the real interview with Sir (chat prompt), then build his
  memory folder in Cowork (`investor-os-builder-prompt.md`). Output:
  his real one-pager + instructions.md + memory.md + financials/.
- **Phase 3:** working dashboard — Streamlit + Python per
  `AI-Advisor-Build-Guide.pdf`: live NSE prices via yfinance (`.NS`
  tickers), Anthropic API for briefs/chat, SQLite memory.
- **Phase 4:** Telegram bot (BotFather), scheduled 7 AM morning brief,
  price/news alerts, weekly newsletter.

## Notes

- All names, holdings, and figures in the demo are fictional.
- Reference material from the video sits in the repo root
  (`ASSET INVESTOR PROMPT.md`, `cowork-investor-os-system-prompt.md`,
  `AI-Advisor-Build-Guide.pdf`).
```

- [x] **Step 2: Verify**

Every path named in the README exists (`demo/investor-os-dashboard.html`, three files under `prompts/`, both docs folders).

- [x] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README with demo script and phased roadmap"
```

---

### Task 12: Final verification pass (spec §7–§8)

**Files:**
- Modify: `demo/investor-os-dashboard.html` (only if fixes needed)

- [x] **Step 1: No-network check**

Run: `grep -Eo "https?://[^\"' ]+" demo/investor-os-dashboard.html`
Expected: **no output** (zero external URLs in the HTML). Also confirm no `<link>`, `<img src=`, `@import`, or `fetch(` in the file: `grep -En "<link|<img|@import|fetch\(" demo/investor-os-dashboard.html` → no output.

- [x] **Step 2: Self-test + full manual walkthrough**

Open `demo/investor-os-dashboard.html#selftest` → banner **6/6 passed**. Then walk all 5 views per the README demo script; press F12 → Console shows no errors; Network tab shows zero requests besides the file itself.

- [x] **Step 3: Responsive sanity**

Narrow the window below ~860px: sidebar collapses to a horizontal strip, two-column grids stack, holdings table scrolls horizontally inside its panel (page itself must not scroll horizontally).

- [x] **Step 4: Consistency sweep**

The same facts appear identically in all views: total ₹2.41 Cr · gold 16.9% vs 10–14% band · cash ₹24.6L / 10.2% vs 8% floor · TCS −4.2% day / −6.4% vs cost · Rule 2 wording. Fix any drift.

- [x] **Step 5: Commit any fixes and tag done**

```bash
git add -A
git commit -m "chore: final verification fixes for demo package" --allow-empty
```

---

## Self-Review (done at plan-writing time)

- **Spec coverage:** §2 layout → Tasks 1–11 · §3 constraints/views → Tasks 1–6, 8 · §4 prompts → Tasks 7, 9, 10 · §5 README → Task 11 · §6 out-of-scope respected (no APIs, no real data) · §7–§8 verification → Task 12 + per-task verify steps. No gaps.
- **Placeholder scan:** all copy, data, code, and edit instructions are literal; no TBDs.
- **Type consistency:** `computeTotals()/inr/inrShort/pct/val/SERIES` defined in Task 2, consumed with same names in Tasks 3–4; view IDs from Task 1 used in Tasks 3–8; sample one-pager numbers (10–14% band, 8% floor, Rule 2) consistent across Tasks 5, 6, 7, 8.
```
