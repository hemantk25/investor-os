# Daily Start — paste this into Claude Code (opened on this folder)

Start my Investor OS dashboard. The app is COMPLETE — do not build or
implement anything, and ignore any plan/spec files in docs/. Just do these
steps in order and don't skip the report:

1. Run the refresh: `./.venv/bin/python -m app.refresh` (Windows:
   `.\.venv\Scripts\python -m app.refresh`). If the venv is missing, run
   `bash setup.sh` (Windows: `./setup.ps1`) first.
2. Read the freshness report it prints and explain it to me in plain English:
   which holdings file was used and how old it is, how many rows loaded and
   skipped, live-price coverage, how many news items came in, and EVERY
   warning — especially "incomplete export" or "file is old". If the holdings
   file is old or incomplete, remind me to download a fresh full export from
   ICICI Direct and drop it into `data/holdings/` (no renaming needed).
3. Start the dashboard in the background:
   `./.venv/bin/python -m flask --app app.server run --port 8555`
   (Windows: `.\.venv\Scripts\python -m flask --app app.server run --port 8555`),
   then give me the link http://127.0.0.1:8555 and a one-line summary of my
   portfolio today.

If I say "I updated the data folder", do the same three steps again.

If I paste a screenshot of a TradingView watchlist: read the symbols from the
image, convert them to EXCHANGE:SYMBOL form (e.g. NSE:RELIANCE), and run:

    python -m app.watchlist_cli import "SYM1,SYM2,..." --market <India|US|UAE|Canada|Global> --category Stocks --group Custom

then tell me how many were added.
