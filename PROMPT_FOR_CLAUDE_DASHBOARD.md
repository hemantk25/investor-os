# Prompt For Claude/Codex To Start Investor OS

Paste this prompt after opening this folder in Claude Code, Codex, or another
coding assistant.

```text
You are inside the Investor OS folder. Please do the following carefully:

1. Read CLAUDE.md, README-SIR.md, README.md, and the current project files.
2. Confirm that the private data files exist:
   - data/holdings.xlsx
   - profile/one-pager.md
   - data/advisory.xlsx if available
3. Do not commit, upload, print, or expose private data from data/, briefs/,
   profile/, or report_data/.
4. Refresh local data if safe by running:
   .\.venv\Scripts\python -m app.refresh
   If .venv is missing, run .\setup.ps1 first.
5. Start the dashboard with:
   .\start-dashboard.ps1
6. Open or report the local URL:
   http://127.0.0.1:8555
7. If anything fails, explain the exact error in simple language and fix it
   without changing the core data model unless I explicitly approve it.

Current intended workflow:
- Holdings are read-only from data/holdings.xlsx.
- Watchlists are local/private in data/investor_os.sqlite.
- Morning Brief uses the local Claude CLI; if login/usage fails, show a clear
  diagnostic and keep the dashboard usable.
- This is local-first. Do not deploy it or add external paid APIs.
```

