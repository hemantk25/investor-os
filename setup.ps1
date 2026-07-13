python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
New-Item -ItemType Directory -Force "data/holdings", "data/advisory", "briefs", "profile" | Out-Null
Write-Host "Setup complete. Run .\daily-start.ps1 to refresh data and launch."
Write-Host "CSS is prebuilt. Rebuild with npx tailwindcss@3 only after changing template classes."
