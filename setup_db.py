"""
setup_db.py  —  Create SQLite schema + seed mock data.
Run once after environment is ready:
    python setup_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "train_station_app"))

from database.session import Base, engine
from database.mock_data.seed import seed_trains

Base.metadata.create_all(bind=engine)
print("✅ Schema created")

count = seed_trains(force=False)
print(f"✅ Seeded {count} train(s)")
