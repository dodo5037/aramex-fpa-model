#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/src"
python fpa.py
python excel_model.py
python charts.py
cd .. && python -m pytest -q
