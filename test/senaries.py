"""
test/senaries.py  —  End-to-End Business Scenario Tests

Tests complete multi-step workflows that simulate real usage patterns.
Each scenario class represents a distinct business use-case.

Pytest techniques used:
  ✔ @pytest.mark.scenario     — business workflow marker
  ✔ @pytest.mark.slow         — long multi-step tests
  ✔ @pytest.mark.parametrize  — same scenario with different data
  ✔ monkeypatch               — simulate external state / time changes
  ✔ tmp_path (built-in)       — isolated file output
  ✔ fixture ordering          — scenario depends on seeded_service
  ✔ step-by-step assertions   — every state transition verified
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from database.train.schemas import TrainCreate, TrainUpdate
from database.train.service import TrainService


# ═══════════════════════════════════════════════════════════════════════ #
#  SCENARIO 1: Full train lifecycle                                      #
#  Create → Activate → Delay → Complete → Verify                        #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.scenario
class TestTrainLifecycle:
    """
    Simulates the complete operational lifecycle of a single train:
    PENDING → ACTIVE → DELAYED → DONE
    """

    def test_step1_create_pending(self, train_service):
        t = train_service.create(TrainCreate(
            train_id="LC-001",
            train_name="Lifecycle Train",
            train_status="pending",
            train_priority="high",
        ))
        assert t["train_status"] == "pending"
        assert t["train_name"] == "Lifecycle Train"

    def test_step2_full_lifecycle_sequence(self, train_service):
        """End-to-end in one test to guarantee ordering."""
        # 1. Create
        t = train_service.create(TrainCreate(
            train_id="LC-SEQ-001",
            train_name="Sequence Train",
            train_status="pending",
            train_priority="critical",
            train_category="passenger",
        ))
        _id = t["_id"]
        assert t["train_status"] == "pending"

        # 2. Activate
        t = train_service.update(_id, TrainUpdate(train_status="active"))
        assert t["train_status"] == "active"

        # 3. Delay (operational issue)
        t = train_service.update(_id, TrainUpdate(
            train_status="delayed",
            alert_count=1,
            alert_time="14:30",
        ))
        assert t["train_status"] == "delayed"
        assert t["alert_count"] == 1

        # 4. Resolve delay → back to active
        t = train_service.update(_id, TrainUpdate(
            train_status="active",
            alert_count=2,
        ))
        assert t["train_status"] == "active"

        # 5. Complete
        t = train_service.update(_id, TrainUpdate(
            train_status="done",
            end_time="18:45",
        ))
        assert t["train_status"] == "done"
        assert t["end_time"] == "18:45"

        # 6. Verify persistence
        fetched = train_service.get_by_id(_id)
        assert fetched["train_status"] == "done"
        assert fetched["alert_count"] == 2

    @pytest.mark.parametrize("terminal_status", ["done", "cancelled"])
    def test_terminal_status_variants(self, train_service, terminal_status):
        """Both 'done' and 'cancelled' are valid terminal states."""
        t = train_service.create(TrainCreate(
            train_status="active",
            train_name=f"Terminal-{terminal_status}",
        ))
        updated = train_service.update(t["_id"], TrainUpdate(train_status=terminal_status))
        assert updated["train_status"] == terminal_status


# ═══════════════════════════════════════════════════════════════════════ #
#  SCENARIO 2: Task-based bulk operations                               #
#  Assign trains to task → bulk update → verify group state            #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.scenario
class TestTaskGroupOperations:
    """
    Simulates dispatching multiple trains under one task,
    then updating them as a group.
    """

    @pytest.fixture()
    def task_trains(self, train_service):
        """Create 4 trains all linked to TASK-DISPATCH."""
        trains = []
        for i in range(1, 5):
            t = train_service.create(TrainCreate(
                train_id=f"DISP-{i:03d}",
                train_name=f"Dispatch Train {i}",
                train_status="pending",
                train_priority="medium",
                task_id="TASK-DISPATCH",
            ))
            trains.append(t)
        return trains

    def test_get_all_trains_by_task(self, train_service, task_trains):
        result = train_service.get_by_task_id("TASK-DISPATCH")
        assert result["total"] == 4

    def test_bulk_activate_all_trains_in_task(self, train_service, task_trains):
        result = train_service.update_by_task_id(
            "TASK-DISPATCH",
            TrainUpdate(train_status="active"),
        )
        assert result["count"] == 4
        statuses = {t["train_status"] for t in result["data"]}
        assert statuses == {"active"}

    def test_bulk_block_task_trains(self, train_service, task_trains):
        result = train_service.update_by_task_id(
            "TASK-DISPATCH",
            TrainUpdate(is_blocked=True, train_status="delayed"),
        )
        assert all(t["is_blocked"] for t in result["data"])
        assert all(t["train_status"] == "delayed" for t in result["data"])

    def test_bulk_complete_all_task_trains(self, train_service, task_trains):
        # Activate first
        train_service.update_by_task_id("TASK-DISPATCH", TrainUpdate(train_status="active"))
        # Then complete
        result = train_service.update_by_task_id(
            "TASK-DISPATCH",
            TrainUpdate(train_status="done", is_blocked=False),
        )
        assert result["count"] == 4
        done_count = sum(1 for t in result["data"] if t["train_status"] == "done")
        assert done_count == 4

    def test_bulk_update_unknown_task_returns_empty(self, train_service, task_trains):
        result = train_service.update_by_task_id("TASK-GHOST", TrainUpdate(train_status="done"))
        assert result["count"] == 0


# ═══════════════════════════════════════════════════════════════════════ #
#  SCENARIO 3: Search & filter discovery workflows                      #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.scenario
class TestDiscoveryWorkflows:
    """
    Simulates an operator searching for trains by various criteria.
    """

    @pytest.fixture()
    def mixed_fleet(self, train_service):
        fleet = [
            TrainCreate(train_id="FLT-001", train_name="Alpha Express",   train_speed="express", train_category="passenger", train_priority="high",     train_status="active",    task_id="TASK-X"),
            TrainCreate(train_id="FLT-002", train_name="Beta Freight",    train_speed="slow",    train_category="freight",   train_priority="low",      train_status="pending",   task_id="TASK-X"),
            TrainCreate(train_id="FLT-003", train_name="Gamma Cargo",     train_speed="fast",    train_category="cargo",     train_priority="medium",   train_status="delayed",   task_id="TASK-Y", is_blocked=True),
            TrainCreate(train_id="FLT-004", train_name="Delta Passenger", train_speed="fast",    train_category="passenger", train_priority="critical", train_status="done",      task_id="TASK-Y"),
            TrainCreate(train_id="FLT-005", train_name="Echo Express",    train_speed="express", train_category="cargo",     train_priority="high",     train_status="cancelled", task_id="TASK-Z"),
        ]
        for tc in fleet:
            train_service.create(tc)
        return train_service

    def test_search_finds_by_partial_name(self, mixed_fleet):
        res = mixed_fleet.search("express")
        assert res["total"] == 2
        names = {t["train_name"] for t in res["data"]}
        assert "Alpha Express" in names
        assert "Echo Express" in names

    def test_filter_active_passenger_trains(self, mixed_fleet):
        res = mixed_fleet.filter(train_status="active", train_category="passenger")
        assert res["total"] == 1
        assert res["data"][0]["train_name"] == "Alpha Express"

    def test_filter_blocked_trains(self, mixed_fleet):
        res = mixed_fleet.filter(is_blocked=True)
        assert res["total"] == 1
        assert res["data"][0]["train_id"] == "FLT-003"

    def test_filter_by_task_x(self, mixed_fleet):
        res = mixed_fleet.filter(task_id="TASK-X")
        assert res["total"] == 2

    def test_filter_high_priority_active(self, mixed_fleet):
        res = mixed_fleet.filter(train_priority="high", train_status="active")
        assert res["total"] == 1
        assert res["data"][0]["train_id"] == "FLT-001"

    @pytest.mark.parametrize("query,min_expected", [
        ("FLT",        5),  # all match by train_id prefix
        ("Alpha",      1),
        ("passenger",  2),  # category search
        ("cargo",      2),  # FLT-003 + FLT-005
    ])
    def test_search_various_queries(self, mixed_fleet, query, min_expected):
        res = mixed_fleet.search(query)
        assert res["total"] >= min_expected, (
            f"Query '{query}' should match >= {min_expected} trains, got {res['total']}"
        )


# ═══════════════════════════════════════════════════════════════════════ #
#  SCENARIO 4: Deletion & cleanup workflow                              #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.scenario
class TestCleanupWorkflow:
    """
    Simulates removing completed / cancelled trains from the system.
    """

    @pytest.fixture()
    def mixed_status_fleet(self, train_service):
        statuses = ["done", "done", "cancelled", "active", "pending"]
        for i, st in enumerate(statuses, start=1):
            train_service.create(TrainCreate(
                train_id=f"CLN-{i:03d}",
                train_name=f"Cleanup-{i}",
                train_status=st,
            ))
        return train_service

    def test_delete_all_done_trains(self, mixed_status_fleet):
        svc = mixed_status_fleet
        # Find all 'done' trains
        done = svc.filter(train_status="done")
        assert done["total"] == 2

        for t in done["data"]:
            svc.delete(t["_id"])

        # Verify they're gone
        remaining = svc.get_all()
        statuses = {t["train_status"] for t in remaining["data"]}
        assert "done" not in statuses

    def test_system_total_after_cleanup(self, mixed_status_fleet):
        svc = mixed_status_fleet
        initial = svc.get_all()["total"]

        # Delete done + cancelled
        for st in ["done", "cancelled"]:
            for t in svc.filter(train_status=st)["data"]:
                svc.delete(t["_id"])

        final = svc.get_all()["total"]
        assert final == initial - 3   # 2 done + 1 cancelled


# ═══════════════════════════════════════════════════════════════════════ #
#  SCENARIO 5: monkeypatch — simulate alert escalation                  #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.scenario
class TestAlertEscalation:
    """
    Uses monkeypatch to simulate a fixed alert count threshold,
    verifying that trains with high alert_count are blocked.
    """

    ALERT_THRESHOLD = 3

    def _should_block(self, train: dict, threshold: int) -> bool:
        """Business rule: block if alert_count >= threshold."""
        return (train.get("alert_count") or 0) >= threshold

    @pytest.mark.parametrize("alert_count,should_block", [
        (0, False),
        (2, False),
        (3, True),
        (5, True),
    ])
    def test_alert_threshold_logic(
        self, train_service, alert_count, should_block
    ):
        t = train_service.create(TrainCreate(
            train_name=f"Alert-{alert_count}",
            train_status="active",
            alert_count=alert_count,
        ))
        # Apply business rule
        if self._should_block(t, self.ALERT_THRESHOLD):
            updated = train_service.update(t["_id"], TrainUpdate(is_blocked=True))
            assert updated["is_blocked"] is True
        else:
            assert t["is_blocked"] is False

    def test_monkeypatch_alert_threshold(self, train_service, monkeypatch):
        """
        monkeypatch: lower the threshold to 1 — even 1 alert blocks.
        Demonstrates replacing a module-level constant in tests.
        """
        # Patch the class attribute to threshold=1
        monkeypatch.setattr(TestAlertEscalation, "ALERT_THRESHOLD", 1)

        t = train_service.create(TrainCreate(
            train_name="One-Alert Train",
            train_status="active",
            alert_count=1,
        ))
        should_block = self._should_block(t, self.ALERT_THRESHOLD)
        assert should_block is True   # threshold=1 → 1 alert triggers block


# ═══════════════════════════════════════════════════════════════════════ #
#  SCENARIO 6: tmp_path — export train data to JSON report             #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.scenario
@pytest.mark.slow
class TestDataExport:
    """
    Uses pytest's built-in tmp_path fixture to test a JSON export
    workflow — trains are fetched, serialised and written to a file.
    Demonstrates: tmp_path + service + file I/O in one scenario.
    """

    def _export_to_json(self, trains: list[dict], path: Path) -> None:
        """Simulate an export function."""
        with path.open("w", encoding="utf-8") as f:
            json.dump(trains, f, indent=2, default=str)

    def test_export_all_trains_to_json(self, seeded_service, tmp_path):
        export_file = tmp_path / "trains_export.json"
        page = seeded_service.get_all()
        self._export_to_json(page["data"], export_file)

        assert export_file.exists()
        content = json.loads(export_file.read_text())
        assert len(content) == 3
        assert content[0]["train_id"].startswith("TEST-")

    def test_export_filtered_trains(self, seeded_service, tmp_path):
        export_file = tmp_path / "active_trains.json"
        filtered = seeded_service.filter(train_status="active")
        self._export_to_json(filtered["data"], export_file)

        content = json.loads(export_file.read_text())
        assert all(t["train_status"] == "active" for t in content)

    def test_export_empty_result(self, train_service, tmp_path):
        export_file = tmp_path / "empty.json"
        page = train_service.get_all()
        self._export_to_json(page["data"], export_file)
        content = json.loads(export_file.read_text())
        assert content == []
