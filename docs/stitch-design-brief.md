# Stitch Design Brief — Investor OS Dashboard

**How to use:** Paste the **Design System + App Overview** block into Google
Stitch first to set the style. Then generate each screen using its block below
(Stitch does one screen at a time — keep them in the same project so the style
carries over). Everything is desktop-first web.

---

## 1) Design System + App Overview (paste this first)

Design a clean, modern **fintech web dashboard** called **Investor OS** — a
private portfolio dashboard for an Indian family investor. Desktop-first,
responsive. The feeling is a premium private-banking web portal (think
INDmoney / Groww / a modern wealth-management app): calm, spacious, trustworthy,
easy on the eyes. NOT dark, NOT flashy. Light and quiet.

**Color palette (use these exactly):**
- Page background: `#F5F7FA` (soft cool grey)
- Cards / surfaces: `#FFFFFF`
- Borders / dividers: `#E6E9F0` (hairline, subtle)
- Primary text: `#111827` (near-black slate)
- Secondary / muted text: `#6B7280`
- Primary accent (brand, active nav, buttons, links): `#0F766E` (deep teal)
- Accent tint (selected / active backgrounds): `#E6F4F1` (very light teal)
- Gains / positive: `#059669` (emerald green) with a ▲
- Losses / negative: `#DC2626` (red) with a ▼
- Chart / allocation categories (distinct, harmonious): teal `#0F766E`,
  indigo `#6366F1`, amber `#D97706`, blue `#3B82F6`, slate `#94A3B8`

**Typography:**
- Headings: **Manrope**, weights 600–700.
- Body, labels, and all numbers: **Inter**, 400–500, with **tabular figures**
  (numbers align in columns).
- Big KPI numbers are large and confident; labels are small, uppercase, muted,
  with wide letter-spacing.

**Style rules:**
- Rounded corners: 12px on cards, 8px on inputs/buttons/pills.
- Very soft shadows (e.g. `0 1px 3px rgba(16,24,40,0.06)`), thin `#E6E9F0`
  borders — depth comes from whitespace, not heavy shadows.
- Generous padding and breathing room. Nothing cramped.
- Money is Indian format: `₹` with lakh/crore short forms (e.g. `₹2.41 Cr`,
  `₹24.6 L`) and Indian digit grouping (`₹2,40,87,460`).

**Global layout (every screen):**
- **Left sidebar** (approx 240px, white, hairline right border): the wordmark
  **Investor OS** at top in teal with a small "Private · Paresh Karia" subtitle,
  then a vertical nav with 5 items — **Overview, Holdings, Rebalance,
  Morning Brief, Investor Profile**. Active item: teal text on a light-teal
  (`#E6F4F1`) rounded background. Simple line icons.
- **Top of content area:** the page title (Manrope, large), and on the right a
  small **member switcher** — a pill/segmented control with **All · PK · CK ·
  NK · DK** (All selected by default, selected pill in teal). Below the title,
  a small muted line showing data freshness ("Updated 7 Jul 2026 · live prices").

---

## 2) Screen: Overview

The landing screen. Top to bottom:

- **Four KPI stat cards** in a row (white cards, subtle border):
  1. **Total Value** — `₹2.41 Cr` large, with `₹2,40,87,460` small & muted below.
  2. **Unrealised P/L** — `₹26.3 L` in green, `▲ +22.6%` below.
  3. **Day P/L** — `₹57,149` in green, `▲ +0.1%` below.
  4. **Cash Available** — `₹24.6 L`, "10.2% of portfolio" muted below.
- **Portfolio value chart** — a smooth **area/line chart** in teal with a soft
  teal gradient fill, on a white card. Range tabs top-right: `1M 3M 6M 1Y ALL`
  (6M selected). Recessive gridlines, tabular-number axis, a hover tooltip.
- Two cards side by side below:
  - **Asset Allocation** — a **donut chart** using the category colors, with a
    legend: Direct Equity 21.3%, Mutual Funds 20.8%, Gold (SGB) 16.9%,
    Debt & FD 30.7%, Cash 10.2%.
  - **Top Movers Today** — a compact list: TATA POWER ▲ +2.1%, HDFC BANK
    ▲ +1.2%, INFY ▼ −0.6%, TCS ▼ −4.2% (gains green, losses red, value on right).
- Keep it airy — this screen should feel calm and scannable.

---

## 3) Screen: Holdings

A clean **data table** screen, white card.
- A **search box** top-left ("Filter by name or symbol…").
- Table grouped into labelled sections by asset class: **Direct Equity (NSE)**,
  **Mutual Funds**, **Gold**, **Debt & FD**, **Cash** — each section header shows
  the section subtotal (e.g. "Direct Equity — ₹51.3 L").
- Columns: **Stock · NSE symbol · Qty · Avg Cost · Price · Value · P/L % ·
  Day % · Held By**. Numbers right-aligned, tabular. P/L% and Day% colored
  green/red. "Held By" shows chips like `PK` `CK`.
- Sample rows: Reliance, HDFC Bank, TCS (show TCS in red, −6.4%), Infosys, ITC,
  Tata Power; UTI Nifty 50 Index Fund, Parag Parikh Flexi Cap; Sovereign Gold
  Bonds; Bank FDs; Savings.
- Quiet zebra striping or hairline row dividers — no heavy grid.

---

## 4) Screen: Rebalance

Tracks progress against a target 50-stock plan. Three **tabs**: **Exits ·
New Buys · Schedule**.
- **Exits tab:** a table of stocks to sell, each with a **status pill** —
  `Done` (green), `In Progress` (amber), `Pending` (grey). Columns: Stock,
  Status, Priority, Est. Proceeds, Reason. e.g. Gensol · Done, Yes Bank ·
  Pending.
- **New Buys tab:** cards, each with a stock, a target allocation ("₹5–7 L"),
  and a **progress bar** (teal) showing how much is deployed. e.g. Apollo
  Hospitals, Bharat Dynamics, JSW Energy.
- **Schedule tab:** a vertical **month timeline** — Jul 2026, Aug 2026, Sep
  2026… each with a short "exits / buys this month" note. Highlight the current
  month with a teal marker and a "You are here" label.

---

## 5) Screen: Morning Brief

- A prominent **primary button** (teal, rounded): **"⚡ Generate Morning Brief"**,
  and a small date picker for past briefs.
- Below, a **brief card** (white, generous padding) rendering an AI-written
  brief with clear sections: **Markets Overnight**, **Impact on Your Portfolio**,
  **Suggested Actions** — headings in Manrope, body readable, key numbers in
  teal/green/red.
- A second card: **Weekly Newsletter** — a digest with "What moved", "News you
  may have missed", and "One thing to act on".

---

## 6) Screen: Investor Profile

A rendered one-page document (like a clean article/doc view on a white card):
- A short teal **callout** at top: "Everything on this dashboard is driven by
  this one editable file — your investor rules."
- Sections styled as a document: **North Star** (a short paragraph),
  **Core Philosophy** (bullets), **Mindset Rules** (numbered), **Anti-Portfolio**
  (bullets). Calm typography, comfortable line length, plenty of whitespace.

---

## Tone notes for any generated copy
Indian investor context, ₹ throughout, plain and confident language, no
jargon-for-its-own-sake. Green = up, red = down, teal = brand/interactive.
