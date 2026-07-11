# Investor OS — How to use (1 page)

## Every week (2 minutes)
1. Log in to ICICI Direct → Portfolio → download the holdings Excel (all members).
2. Drag the file into the `data` folder, replacing `holdings.xlsx`.
3. Double-click **Start Dashboard** — your browser opens at http://127.0.0.1:8555 with everything updated.
4. Click **Refresh local data** on Overview if you want fresh watchlist prices,
   portfolio snapshots, news, and goal metadata immediately.

## Every morning (optional)
Open the dashboard → **Morning Brief** → click **⚡ Generate Morning Brief**.
Claude reads your rules, your live portfolio and stored news, then writes your brief.

## What each page is for
- **Overview:** market pulse, portfolio KPIs, family/asset allocation, movers, and watchlist preview.
- **Holdings:** Groww-style holdings view; add manual holdings, edit them, or record sells/reductions without changing the ICICI Excel.
- **Watchlist:** TradingView-style local watchlist boards for India, US, UAE, Canada, and global symbols, with TXT import/export.
- **Morning Brief:** generate and read the daily three-part brief: Market Brief, My Stocks, and Impact Notes.
- **News:** refresh/read market and portfolio-related news with real links.
- **Rebalance:** track advisory exits, buys, schedule, and status.
- **Goal:** see progress toward the long-term target, required path, implied CAGR, and large/mid/small-cap discipline.

## Switching family members
The chips at the top — All / PK / CK / NK / DK — switch every number on the page.

## Your goal
The Goal page creates `data/goal.json` the first time it opens. Change target
amount, date, SIP, or allocation bands there if your rules change.

## If something breaks
Open this folder in Claude Cowork (or type `claude` in Terminal here) and simply
describe the problem in plain English. The system documentation (CLAUDE.md) tells
Claude how everything works. Example: "the dashboard shows a stale price for
Tata Power — fix it."

## Your rules file
`profile/one-pager.md` is YOUR document — open it in any editor and change your
rules anytime. Every brief obeys whatever it says.
