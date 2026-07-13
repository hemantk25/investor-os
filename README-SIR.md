# Investor OS — CEO Handoff Guide

This is a local dashboard. It is not deployed, and the financial files stay in
this folder.

## Each Use
1. Download the latest ICICI Direct holdings export.
2. Put it here, replacing `data/holdings.xlsx`.
3. Optional: replace `data/advisory.xlsx` if there is a new advisory report.
4. Double-click **start-dashboard.ps1** on Windows.
5. Open http://127.0.0.1:8555 if the browser does not open automatically.
6. Click **Refresh local data** on Overview when you want prices, watchlists,
   portfolio snapshots, news, and goal metadata refreshed immediately.

## Every morning (optional)
Open **Morning Brief** and click **Generate Morning Brief**. Claude reads:
`data/holdings.xlsx`, `profile/one-pager.md`, stored news, watchlists, and the
dashboard logic, then writes the brief into `briefs/`.

## What each page is for
- **Overview:** market pulse, portfolio KPIs, asset-class split, and family split.
- **Holdings:** read-only brokerage-style view from `data/holdings.xlsx`.
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
