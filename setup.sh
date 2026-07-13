#!/bin/bash
cd "$(dirname "$0")"
PY=$(command -v python3.12 || command -v python3.11 || command -v python3)
"$PY" -m venv .venv
./.venv/bin/pip install -r requirements.txt
mkdir -p data/holdings data/advisory briefs profile
echo "Setup complete. Double-click 'Start Dashboard.command' to launch."
echo "CSS is prebuilt. Rebuild with 'npx tailwindcss@3 -c app/tailwind/tailwind.config.js -i app/tailwind/input.css -o app/static/app.css --minify' only after changing template classes."
