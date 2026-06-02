"""
main.py  —  Project root entry point

Adds both the project root and train_station_app to sys.path
so all imports (database.* and api.*) resolve correctly.

Usage:
    python main.py
    python main.py --port 8080
    python main.py --host 0.0.0.0 --port 8000 --no-reload
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── Path setup (must happen before any project import) ───────────── #
ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "train_station_app"

for p in (str(ROOT), str(APP_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# ── Seed mock data if DB is empty ────────────────────────────────── #
from database.session import Base, engine                           # noqa: E402
from database.mock_data.seed import seed_trains                     # noqa: E402
from database.train.schemas import TrainCreate                      # noqa: E402

Base.metadata.create_all(bind=engine)
seeded = seed_trains(force=False)
if seeded:
    print(f"  ✔ Auto-seeded {seeded} train record(s) into the database")

# ── Start server ──────────────────────────────────────────────────── #
import uvicorn                                                       # noqa: E402


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train Station API server")
    p.add_argument("--host",     default="127.0.0.1", help="Bind host")
    p.add_argument("--port",     default=8000, type=int, help="Bind port")
    p.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse()
    print(f"\n  🚂  Train Station API")
    print(f"  ➜  http://{args.host}:{args.port}/docs\n")
    uvicorn.run(
        "train_station_app.app:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        reload_dirs=[str(ROOT)],
    )
