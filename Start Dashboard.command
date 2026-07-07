#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d .venv ]; then bash setup.sh; fi
./.venv/bin/python -m streamlit run app/dashboard.py
