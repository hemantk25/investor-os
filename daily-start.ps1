if (-not (Test-Path .venv)) { python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt }
.\.venv\Scripts\python -m app.refresh
Start-Process "http://127.0.0.1:8555"
.\.venv\Scripts\python -m flask --app app.server run --port 8555
