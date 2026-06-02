"""
database/mock_data/seed.py  —  Idempotent database seeder

Loads mock data from JSON files and inserts them into the database
ONLY IF the target table is empty (idempotent — safe to run multiple times).

Usage (from project root):
    python -m database.mock_data.seed
    python -m database.mock_data.seed --force   # re-seed even if data exists
    python -m database.mock_data.seed --dry-run # preview without inserting

Exit codes:
    0 — success (seeded or already seeded)
    1 — error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ── Make sure project root is on sys.path ─────────────────────────── #
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.session import Base, engine, get_session          # noqa: E402
from database.train.model import Train                          # noqa: E402
from database.train.repository import TrainRepository           # noqa: E402
from database.train.schemas import TrainCreate                  # noqa: E402

# ── Path to JSON fixtures ──────────────────────────────────────────── #
MOCK_DIR = Path(__file__).parent
TRAINS_JSON = MOCK_DIR / "trains.json"


# ═══════════════════════════════════════════════════════════════════════ #
#  Colour helpers (no external deps)                                     #
# ═══════════════════════════════════════════════════════════════════════ #
GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def _ok(msg: str)    -> None: print(f"  {GREEN}✔{RESET}  {msg}")
def _skip(msg: str)  -> None: print(f"  {YELLOW}⊘{RESET}  {msg}")
def _info(msg: str)  -> None: print(f"  {CYAN}ℹ{RESET}  {msg}")
def _err(msg: str)   -> None: print(f"  {RED}✗{RESET}  {msg}", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════ #
#  Core seeding logic                                                    #
# ═══════════════════════════════════════════════════════════════════════ #

def _load_json(path: Path) -> list[dict]:
    """Load and parse a JSON file. Raises on missing / malformed files."""
    if not path.exists():
        raise FileNotFoundError(f"Mock data file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def seed_trains(
    force: bool = False,
    dry_run: bool = False,
) -> int:
    """
    Seed the `trains` table.

    Args:
        force   — truncate existing data before seeding
        dry_run — parse & validate data without touching the DB

    Returns:
        number of records inserted (0 if skipped)
    """
    records = _load_json(TRAINS_JSON)
    _info(f"Loaded {len(records)} train records from {TRAINS_JSON.name}")

    if dry_run:
        # Validate each record against the Pydantic schema
        errors: list[str] = []
        for i, raw in enumerate(records, start=1):
            try:
                TrainCreate(**raw)
            except Exception as exc:
                errors.append(f"  Record #{i} ({raw.get('train_id', '?')}): {exc}")
        if errors:
            _err("Validation errors:")
            for e in errors:
                print(e, file=sys.stderr)
            return 0
        _ok(f"Dry-run OK — all {len(records)} records pass schema validation")
        return 0

    with get_session() as db:
        repo = TrainRepository(db)

        # ── Idempotency check ──────────────────────────────────────── #
        existing_count = repo.count()
        if existing_count > 0 and not force:
            _skip(
                f"trains table already has {existing_count} row(s). "
                f"Use --force to re-seed."
            )
            return 0

        # ── Truncate if --force ────────────────────────────────────── #
        if force and existing_count > 0:
            db.query(Train).delete()
            db.flush()
            _info(f"Truncated {existing_count} existing train record(s)")

        # ── Insert ────────────────────────────────────────────────────#
        inserted = 0
        skipped  = 0
        for raw in records:
            try:
                schema = TrainCreate(**raw)
                # Skip if train_id already exists (edge-case in force mode)
                if repo.get_by_train_id(schema.train_id):
                    _skip(f"train_id={schema.train_id!r} already exists — skipped")
                    skipped += 1
                    continue
                repo.create(schema)
                inserted += 1
            except Exception as exc:
                _err(f"Failed to insert {raw.get('train_id', '?')}: {exc}")

    _ok(f"Inserted {inserted} train record(s)  |  skipped {skipped}")
    return inserted


# ═══════════════════════════════════════════════════════════════════════ #
#  Entry point                                                           #
# ═══════════════════════════════════════════════════════════════════════ #

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the database with mock data."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-seed even if data already exists (truncates existing rows)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate mock data without writing to the database",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    print(f"\n{CYAN}{BOLD}╔══════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BOLD}║        Train Station DB Seeder           ║{RESET}")
    print(f"{CYAN}{BOLD}╚══════════════════════════════════════════╝{RESET}\n")

    # Ensure schema exists
    Base.metadata.create_all(engine)
    _info("Schema verified / created")
    print()

    # Seed trains
    print(f"{BOLD}── Trains ───────────────────────────────────{RESET}")
    try:
        count = seed_trains(force=args.force, dry_run=args.dry_run)
    except Exception as exc:
        _err(str(exc))
        sys.exit(1)

    # Summary
    print()
    if args.dry_run:
        print(f"{YELLOW}{BOLD}Dry-run complete — no data was written.{RESET}\n")
    else:
        print(f"{GREEN}{BOLD}Seeding complete — {count} train(s) added.{RESET}\n")


if __name__ == "__main__":
    main()
