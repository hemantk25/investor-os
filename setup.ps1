python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
New-Item -ItemType Directory -Force data, briefs, profile | Out-Null
Write-Host "Setup complete. Run .\start-dashboard.ps1 to launch."
