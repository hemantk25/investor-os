# Google Drive Handoff Notes

Use this when preparing the folder for the CEO.

## Best Folder Shape

Keep:
- `app/`
- `data/` only if the CEO is allowed to see the current private data
- `briefs/` only if old generated briefs should travel with the handoff
- `profile/`
- `requirements.txt`
- `setup.ps1`
- `start-dashboard.ps1`
- `README-SIR.md`
- `CLAUDE.md`
- `PROMPT_FOR_CLAUDE_DASHBOARD.md`
- `PROMPT_DAILY_START.md`
- `daily-start.ps1` and `Daily Start.command`

Do not upload:
- `.venv/`
- `.git/`
- `.pytest_cache/`
- `__pycache__/`
- temporary screenshots or `output/`

## Create A Clean Copy

From PowerShell:

```powershell
.\prepare-drive-handoff.ps1
```

That creates a clean timestamped folder next to this project and excludes
technical/generated folders.

By default it does not copy private financial folders. To include private data:

```powershell
.\prepare-drive-handoff.ps1 -IncludePrivateData
```

Only use `-IncludePrivateData` if the Google Drive folder is restricted to people
who may see the portfolio.

## CEO Workflow

1. Upload/open the clean handoff folder in Google Drive.
2. Drop the latest ICICI export into `data/holdings/` (any filename).
3. Open the folder in Claude Code/Codex.
4. Paste the contents of `PROMPT_FOR_CLAUDE_DASHBOARD.md`.
5. Start the dashboard and use `http://127.0.0.1:8555`.

## Important

Google Drive is only file sharing. The dashboard still runs on the local
computer. It is not a website deployment, and `127.0.0.1` means "this computer".
Phone/QR access needs a local network launcher or a tunnel and should be handled
as a separate small task.

