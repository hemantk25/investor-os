#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d .venv ]; then bash setup.sh; fi
./.venv/bin/python -m app.refresh
( sleep 2; open http://127.0.0.1:8555 ) &
./.venv/bin/python -m flask --app app.server run --port 8555
