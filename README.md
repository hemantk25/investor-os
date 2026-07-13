# Investor OS — Local Investment Dashboard for Paresh Karia

An AI-powered personal investment system, modelled on the "AI Financial
Advisor" architecture (AI Edge, https://youtu.be/VvuHr46wF-4). This repo now
contains the current local-first Flask dashboard plus historical reference
material from the earlier demo/build phases.

## What's in here

| File | What it is |
|---|---|
| `app/` | Real Flask/Jinja/Tailwind dashboard |
| `data/` | Private local financial data folder, gitignored |
| `briefs/` | Locally generated morning briefs, gitignored |
| `profile/` | Owner profile/rules, gitignored |
| `demo/investor-os-dashboard.html` | Historical offline mockup/reference |
| `prompts/investor-interview-prompt.md` | Paste into Claude/ChatGPT → AI interviews Sir → produces his investor one-pager |
| `prompts/investor-os-builder-prompt.md` | For Phase 2: builds the full memory folder in Claude Cowork/Code |
| `prompts/sample-investor-one-pager.md` | Filled fictional example of what the interview produces |
| `docs/superpowers/specs/` · `docs/superpowers/plans/` | Design spec and implementation plan |
| `PROMPT_FOR_CLAUDE_DASHBOARD.md` | Paste into Claude/Codex to refresh/start the local dashboard |
| `GOOGLE_DRIVE_HANDOFF.md` | Notes for preparing a clean Google Drive handoff |

Private financial files are intentionally not committed. Tests use fake fixture
data from `tests/fixtures/`.

For Google Drive handoff, read `GOOGLE_DRIVE_HANDOFF.md` first. The large
`.venv/` folder and Git/caches should not be uploaded.

## Current dashboard features

- **Overview:** market pulse, portfolio KPI cards, asset-class split, and family
  split visuals.
- **Holdings:** searchable brokerage-style read-only holdings page driven by
  `data/holdings.xlsx`.
- **Watchlist:** TradingView-inspired multi-board workspace with country,
  named watchlists, latest quote snapshots, and TradingView TXT import/export.
- **Morning Brief:** local Claude CLI generation with Market Brief and a measured
  portfolio-impact table with future-impact signals.
- **News:** local news store populated from Google News RSS/Yahoo feeds, with
  market tabs and portfolio-news filtering.
- **Rebalance:** advisory exits/buys/schedule tracking from the ICICI advisory
  workbook plus local status overrides.
- **Goal:** target-path tracker using `data/goal.json`, portfolio snapshots,
  implied CAGR, market-cap bands, and compliance checks.
- **Profile:** `/profile` renders the owner one-pager used by briefs; it is
  intentionally linked from other pages rather than shown in the side nav.

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
   (and the advisory report into `data/advisory.xlsx` if available).
2. macOS: double-click **Start Dashboard.command**. Windows: `./start-dashboard.ps1`.
3. The browser opens at http://127.0.0.1:8555.
4. Optional refresh from the UI, or run `python -m app.refresh` to update
   watchlist quote snapshots, portfolio snapshots, news, security metadata, and
   last-refresh state.

CSS is prebuilt and committed in `app/static/app.css`. Only rebuild it after
changing Tailwind classes in templates.

Holdings are file-only in the dashboard. The source of truth is
`data/holdings.xlsx`; old manual holding records may remain in SQLite but are
ignored for totals and UI.

The one-page owner guide is `README-SIR.md`; the maintenance playbook for
Claude Code is `CLAUDE.md`. For Drive sharing, use
`PROMPT_FOR_CLAUDE_DASHBOARD.md` and `GOOGLE_DRIVE_HANDOFF.md`. Design/build
history:
`docs/superpowers/specs/` and `docs/superpowers/plans/`.

## Notes

- All names, holdings, and figures in the demo are fictional.
- Reference material from the video sits in the repo root
  (`ASSET INVESTOR PROMPT.md`, `cowork-investor-os-system-prompt.md`,
  `AI-Advisor-Build-Guide.pdf`).
