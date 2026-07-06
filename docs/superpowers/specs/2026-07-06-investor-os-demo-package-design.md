# Design — Investor OS Demo Package for Paresh Karia

**Date:** 2026-07-06
**Author:** Hemant (with Claude)
**Status:** Approved pending user spec review

---

## 1. Background & Purpose

Paresh Karia (CEO, Acquest Advisors) wants a personal AI-powered investment
system modelled on the "AI Financial Advisor" build from the AI Edge YouTube
video (https://youtu.be/VvuHr46wF-4). The reference architecture (from the
video, the two system-prompt MD files, and `AI-Advisor-Build-Guide.pdf` in
this folder):

1. An AI **interview prompt** that asks the investor questions across 7
   phases and produces an editable **investor one-pager MD file** (North
   Star, Core Philosophy, Time Horizon, Mindset Rules, Personal Nuances,
   Anti-Portfolio). This file is injected as system context into every
   future AI analysis.
2. A **file-based memory system** the investor owns (instructions.md,
   memory.md, one-pager, financials folder).
3. A **portfolio dashboard** (Streamlit in the reference) with live prices,
   morning brief generation, market scan, and chat.
4. **Phone alerts** via a Telegram bot (daily morning brief, news alerts) —
   which also covers the "newsletter" requirement.

**This phase does NOT build the real system.** It builds a pitch/demo
package: a polished interactive mockup + the prompt files, so Paresh can
approve the direction before we invest in the real build.

## 2. Deliverables & File Layout

```
Investment_portfolio_dashboard/
├── demo/
│   └── investor-os-dashboard.html      # self-contained interactive mockup
├── prompts/
│   ├── investor-interview-prompt.md    # chat-friendly, India-adapted interview
│   ├── investor-os-builder-prompt.md   # Cowork/Claude Code OS-builder version
│   └── sample-investor-one-pager.md    # filled fictional example output
└── README.md                           # how pieces fit + demo script + roadmap
```

## 3. Dashboard Mockup (`demo/investor-os-dashboard.html`)

### Constraints
- Single self-contained HTML file: all CSS/JS/data inline, no external
  requests (works offline, double-click to open, sendable over
  email/WhatsApp, publishable as a Claude Artifact link).
- All data is fictional sample data, clearly marked "DEMO — sample data".
- Currency formatting in Indian style (₹, lakh/crore).
- Responsive enough to look good on a laptop and acceptable on a phone.

### Look & feel
Dark premium private-banking aesthetic: deep charcoal/navy base, gold +
emerald accents, refined typography. Header: "Paresh Karia — Investor OS"
with current date and DEMO badge. Not a generic admin-template look.
(Implementation will use the frontend-design skill and dataviz skill for
chart styling.)

### Views (sidebar navigation, 5 views)

1. **Overview**
   - Hero metrics: Total Value (~₹2.4 Cr), Unrealised P/L (₹ + %),
     Today's Change, Cash available.
   - Portfolio value area chart with 1M/3M/6M/1Y/ALL range selector
     (pre-generated static series per range).
   - Asset-class donut: Indian equities / mutual funds / gold (SGB) /
     debt & FD / cash.
   - Top movers today (2 gainers, 2 losers from holdings).

2. **Holdings**
   - Table grouped by asset class. Columns: instrument, qty, avg cost,
     LTP, current value, P/L %, day change.
   - Sample composition (realistic, fictional): NSE large-caps
     (RELIANCE, HDFCBANK, TCS, INFY, ITC), a Nifty 50 index fund,
     Sovereign Gold Bonds, FD/debt, cash. One holding (TCS) shown in
     loss to support the alert/brief narrative.

3. **Morning Brief** (showpiece)
   - "⚡ Generate Morning Brief" button → typewriter animation reveals a
     pre-written McKinsey-style brief: overnight markets → impact on his
     specific positions → suggested actions → key headlines (RBI policy,
     TCS earnings miss, etc.).
   - Below: a sample weekly newsletter layout (digest of the week's
     portfolio performance + prominent news on holdings).

4. **Alerts & Phone**
   - Phone-frame mockup rendering Telegram-style messages: 7:00 AM
     morning brief ping, price alert ("TCS −4.2% on earnings miss — you
     hold 120 shares"), news alert on a holding.
   - Short caption: how it works (free Telegram bot via BotFather,
     scheduled daily).

5. **Investor Profile**
   - Rendered view of the sample investor one-pager (North Star, Core
     Philosophy, Mindset Rules, Anti-Portfolio…).
   - Callout: "Everything this system says is driven by one editable MD
     file that you own" — connects the questionnaire deliverable to the
     dashboard deliverable.

### Interactivity (all fake, no backend)
- Sidebar view switching.
- Range-selector tabs swap pre-generated chart series.
- Generate Morning Brief typewriter animation.
- Phone frame may animate messages appearing in sequence.
- No live prices, no API calls, no persistence.

## 4. Prompt Files

### 4.1 `prompts/investor-interview-prompt.md`
Adapted from `ASSET INVESTOR PROMPT.md`. Keeps: the McKinsey-caliber
advisor role, 7-phase interview structure, one-question-at-a-time rule,
push-back-on-vague-answers behaviour, stress tests, exact output
structure (the one-pager). Changes:
- India-aware context: tax regime questions (LTCG/STCG, old vs new
  regime, business income), Indian asset classes (direct equity, MF /
  PMS / AIF, gold/SGB, real estate, FD, US investing via LRS), ₹.
- Works pasted into Claude.ai or ChatGPT chat (no file access needed).
- Usage note at top for Paresh: paste, answer by voice input for speed,
  ~20–30 minutes, save the output as his editable MD (or Word) file.

### 4.2 `prompts/investor-os-builder-prompt.md`
Adapted from `cowork-investor-os-system-prompt.md` (the version that
builds the full folder: instructions.md, memory.md, one-pager,
financials/). Lightly India-adapted (currency, tax phrasing). Reserved
for Phase 2 when Hemant sits with Paresh in Claude Cowork/Code.

### 4.3 `prompts/sample-investor-one-pager.md`
A fully filled, clearly-fictional example (not Paresh's real profile) in
the exact output structure, Indian context, so Paresh sees what the
interview produces before he does it. Same content rendered in the
dashboard's Investor Profile view.

## 5. README.md
One page for Hemant: what each file is, suggested demo flow (open
dashboard → Overview → Holdings → Generate Morning Brief → phone alerts →
Investor Profile → show the interview prompt), and the phased roadmap:
- **Phase 1 (this):** demo package, get Paresh's approval.
- **Phase 2:** run the real interview with Paresh → his one-pager +
  memory folder (Cowork, using the OS-builder prompt).
- **Phase 3:** working dashboard (Streamlit per the build guide; NSE
  prices via yfinance `.NS` tickers; Anthropic API; SQLite memory).
- **Phase 4:** Telegram bot alerts, scheduled morning briefs, weekly
  newsletter.

## 6. Out of Scope (this phase)
- Live market data, broker/exchange APIs, Google Sheets integration.
- Real Telegram bot, scheduling, notifications.
- Any real personal/financial data of Paresh (all sample data fictional).
- Streamlit/Python build (Phase 3).
- Cloud memory (Supabase/pgvector — mentioned in reference guide only).

## 7. Error Handling & Edge Cases
Static mockup → minimal surface. Requirements:
- HTML must render with no console errors and no network requests
  (strict-CSP/offline safe).
- Graceful at common laptop widths (≥1280px) and readable on mobile.
- All interactive elements must do something visible (no dead buttons).

## 8. Verification
- Open the HTML file locally (offline) — all 5 views render, all
  interactions work, no external requests (check DevTools network tab).
- INR formatting spot-check (e.g. ₹2,41,00,000 / ₹2.41 Cr style).
- Prompt files: paste interview prompt into a fresh Claude chat and
  confirm it starts the Phase-1 interview correctly (one question, no
  document dump).
- README demo flow followed start-to-finish by Hemant before showing
  Paresh.
