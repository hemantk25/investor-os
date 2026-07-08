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

Tip: the dashboard supports deep links — open it with `#view-brief`,
`#view-alerts`, etc. to land on a specific view, or `#selftest` to see the
data-consistency checks pass.

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
- **Phase 3 (in progress, `phase3-dashboard` branch):** the real local-first
  dashboard — Flask + Stitch-style Jinja/Tailwind UI, yfinance, ICICI Excel
  ingestion, member switcher, rebalance tracker, morning briefs via Claude Code. See
  "Running the real dashboard" below.
- **Phase 4:** Telegram bot (BotFather), scheduled 7 AM morning brief,
  price/news alerts, weekly newsletter.

## Running the real dashboard (Phase 3)

The real dashboard lives in `app/` and runs locally in Flask — no cloud server,
no API keys, no cost beyond the owner's existing Claude subscription. Real financial data
stays on the machine (the `data/`, `briefs/`, `profile/` folders are
gitignored and never leave it).

**One-time setup**

- macOS: `bash setup.sh` (or just double-click **Start Dashboard.command** —
  it self-installs on first run).
- Windows (dev): `./setup.ps1`.

**Each use**

1. Drop the weekly ICICI Direct holdings export into `data/holdings.xlsx`
   (and the advisory report into `data/advisory.xlsx`).
2. macOS: double-click **Start Dashboard.command**. Windows: `./start-dashboard.ps1`.
3. The browser opens at http://127.0.0.1:8555.

CSS is prebuilt and committed in `app/static/app.css`. Only rebuild it after
changing Tailwind classes in templates.

The one-page owner guide is `README-SIR.md`; the maintenance playbook for
Claude Code is `CLAUDE.md`. Design and build detail:
`docs/superpowers/specs/2026-07-07-*` and `docs/superpowers/plans/2026-07-07-*`.

## Notes

- All names, holdings, and figures in the demo are fictional.
- Reference material from the video sits in the repo root
  (`ASSET INVESTOR PROMPT.md`, `cowork-investor-os-system-prompt.md`,
  `AI-Advisor-Build-Guide.pdf`).
