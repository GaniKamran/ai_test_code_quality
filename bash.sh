#!/usr/bin/env bash
set -e

PYTHONPATH=".:train_station_app"
export PYTHONPATH

echo "=== [1/3] DB setup ==="
python setup_db.py



echo ""
echo "=== [3/3] Starting app ==="
exec python -m uvicorn train_station_app.app:app --host 0.0.0.0 --port 8000


echo ""
echo "=== [2/3] Running tests ==="
python -m pytest test/ -v --tb=short -s
