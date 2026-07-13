# Investor OS — CEO Handoff Guide

This is a local dashboard. It is not deployed, and the financial files stay in
this folder.

## The daily ritual (3 steps)
1. **When you have new data:** download the ICICI Direct holdings export and
   drag it into `data/holdings/` — **any filename is fine, never rename it**.
   The newest file in that folder always wins. Same for advisory reports →
   `data/advisory/`.
2. **Start:** open this folder in Claude Code and paste the prompt from
   `PROMPT_DAILY_START.md` — Claude will load everything, fetch live prices
   and news, explain the data freshness to you, and hand you the dashboard
   link. (Prefer no typing? Double-click **Daily Start.command** on Mac /
   **daily-start.ps1** on Windows — same result, without the explanation.)
3. **Read:** by the time the browser opens, every number is live and
   preloaded.

## Adding a TradingView watchlist (the one extra thing to learn)
TradingView's export needs a paid plan, so do this instead: take a
**screenshot** of your watchlist in TradingView, paste the image into Claude
Code, and say "add this watchlist to the dashboard (market: India)". Claude
reads the symbols from the picture and imports them.

## Every morning (optional)
Open **Morning Brief** and click **Generate Morning Brief**. Claude reads your
newest holdings file, `profile/one-pager.md`, stored news, watchlists, and the
dashboard logic, then writes the brief into `briefs/`.

## What each page is for
- **Overview:** market pulse, portfolio KPIs, asset-class split, and family split.
- **Holdings:** read-only brokerage-style view from the newest file in `data/holdings/`.
- **Watchlist:** TradingView-style local watchlist boards for India, US, UAE, Canada, and global symbols.
- **Morning Brief:** Market Brief plus portfolio Impact table.
- **News:** refresh/read market and portfolio-related news with real links.
- **Rebalance:** track advisory exits, buys, schedule, and status.
- **Goal:** see progress toward the long-term target, required path, implied CAGR, and large/mid/small-cap discipline.

## Switching family members
The chips at the top — All / PK / CK / NK / DK — switch every number on the page.

## Google Drive Use
If this folder is shared in Google Drive, anyone with access to the folder can
see files inside `data/`, `briefs/`, and `profile/`. Only share the folder with
people who are allowed to see the portfolio.

Do not upload `.venv`, `.git`, `.pytest_cache`, or `__pycache__` folders. They
are technical/generated files and make the folder much larger.

## Claude Prompt
Open `PROMPT_FOR_CLAUDE_DASHBOARD.md`, paste it into Claude Code/Codex from
inside this folder, and Claude will inspect the latest data, refresh the local
system, and start the dashboard.

## QR Code Note
The dashboard currently opens on the same computer at `127.0.0.1:8555`. A QR
code for phone/tablet access needs a local-network launcher or tunnel. That is
separate from deployment and can be added later.

## If something breaks
Open this folder in Claude Cowork (or type `claude` in Terminal here) and simply
describe the problem in plain English. The system documentation (CLAUDE.md) tells
Claude how everything works. Example: "the dashboard shows a stale price for
Tata Power — fix it."

## Your rules file
`profile/one-pager.md` is YOUR document — open it in any editor and change your
rules anytime. Every brief obeys whatever it says.
