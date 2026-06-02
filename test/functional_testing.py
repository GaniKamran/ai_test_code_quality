"""
test/functional_testing.py  —  Functional CRUD Tests (Service Layer)

Tests the TrainService directly (no HTTP overhead).
Each test class focuses on one operation group.

Pytest techniques used:
  ✔ @pytest.mark.{crud, functional, negative, smoke}
  ✔ @pytest.mark.parametrize  — multiple inputs in one test
  ✔ pytest.raises             — expected exceptions
  ✔ yield fixture             — via conftest (train_service, seeded_service)
  ✔ fixture composition       — seeded_service depends on train_service
  ✔ assert with messages      — clear failure descriptions
"""
from __future__ import annotations

import pytest

from database.train.schemas import TrainCreate, TrainUpdate
from database.train.service import TrainService


# ═══════════════════════════════════════════════════════════════════════ #
#  Helpers                                                               #
# ═══════════════════════════════════════════════════════════════════════ #

def _create(svc: TrainService, **overrides) -> dict:
    """Create a train with sensible defaults + overrides."""
    defaults = dict(
        train_name="Test Train",
        train_speed="fast",
        train_category="passenger",
        train_priority="medium",
        train_status="pending",
    )
    defaults.update(overrides)
    return svc.create(TrainCreate(**defaults))


# ═══════════════════════════════════════════════════════════════════════ #
#  SMOKE                                                                 #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.smoke
class TestServiceSmoke:
    """Minimal sanity checks — run first to catch import / wiring errors."""

    def test_service_instantiates(self, train_service):
        assert isinstance(train_service, TrainService)

    def test_empty_db_returns_zero_count(self, train_service):
        page = train_service.get_all()
        assert page["total"] == 0
        assert page["data"] == []

    def test_create_returns_dict_with_id(self, train_service):
        result = _create(train_service)
        assert "_id" in result
        assert result["_id"] != ""


# ═══════════════════════════════════════════════════════════════════════ #
#  CREATE                                                                #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.crud
class TestCreate:

    def test_create_sets_default_status_pending(self, train_service):
        t = _create(train_service)
        assert t["train_status"] == "pending"

    def test_create_stores_all_fields(self, train_service):
        t = _create(
            train_service,
            train_name="Baku Express",
            train_speed="express",
            train_category="cargo",
            train_priority="critical",
            train_status="active",
            task_id="TASK-99",
        )
        assert t["train_name"]     == "Baku Express"
        assert t["train_speed"]    == "express"
        assert t["train_category"] == "cargo"
        assert t["train_priority"] == "critical"
        assert t["train_status"]   == "active"
        assert t["task_id"]        == "TASK-99"

    def test_create_auto_generates_uuid_id(self, train_service):
        t1 = _create(train_service)
        t2 = _create(train_service)
        assert t1["_id"] != t2["_id"], "_id must be unique per record"

    def test_create_custom_train_id_preserved(self, train_service):
        t = _create(train_service, train_id="CUSTOM-42")
        assert t["train_id"] == "CUSTOM-42"

    @pytest.mark.negative
    def test_create_duplicate_train_id_raises(self, train_service):
        _create(train_service, train_id="DUPE-001")
        with pytest.raises(ValueError, match="DUPE-001"):
            _create(train_service, train_id="DUPE-001")

    @pytest.mark.parametrize("status", ["pending", "active", "delayed", "done", "cancelled"])
    def test_create_accepts_all_valid_statuses(self, train_service, status):
        t = _create(train_service, train_status=status)
        assert t["train_status"] == status

    @pytest.mark.parametrize("priority", ["low", "medium", "high", "critical"])
    def test_create_accepts_all_priorities(self, train_service, priority):
        t = _create(train_service, train_priority=priority)
        assert t["train_priority"] == priority

    @pytest.mark.parametrize("category", ["passenger", "freight", "cargo"])
    def test_create_accepts_all_categories(self, train_service, category):
        t = _create(train_service, train_category=category)
        assert t["train_category"] == category

    @pytest.mark.parametrize("speed", ["slow", "fast", "express"])
    def test_create_accepts_all_speeds(self, train_service, speed):
        t = _create(train_service, train_speed=speed)
        assert t["train_speed"] == speed


# ═══════════════════════════════════════════════════════════════════════ #
#  READ                                                                  #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.crud
class TestRead:

    def test_get_by_id_returns_correct_record(self, train_service):
        created = _create(train_service, train_name="Findable")
        fetched = train_service.get_by_id(created["_id"])
        assert fetched["train_name"] == "Findable"
        assert fetched["_id"] == created["_id"]

    @pytest.mark.negative
    def test_get_by_id_missing_raises_key_error(self, train_service):
        with pytest.raises(KeyError):
            train_service.get_by_id("non-existent-uuid")

    def test_get_by_train_id(self, train_service):
        _create(train_service, train_id="TR-FIND-ME")
        result = train_service.get_by_train_id("TR-FIND-ME")
        assert result["train_id"] == "TR-FIND-ME"

    @pytest.mark.negative
    def test_get_by_train_id_missing_raises(self, train_service):
        with pytest.raises(KeyError):
            train_service.get_by_train_id("GHOST-TRAIN")

    def test_get_all_returns_all_trains(self, seeded_service):
        page = seeded_service.get_all()
        assert page["total"] == 3
        assert len(page["data"]) == 3

    def test_get_all_pagination_limit(self, seeded_service):
        page = seeded_service.get_all(limit=2, offset=0)
        assert len(page["data"]) == 2
        assert page["total"] == 3      # total unchanged

    def test_get_all_pagination_offset(self, seeded_service):
        page = seeded_service.get_all(limit=10, offset=2)
        assert len(page["data"]) == 1  # 3 total − 2 offset = 1

    def test_get_all_empty_beyond_offset(self, seeded_service):
        page = seeded_service.get_all(limit=10, offset=100)
        assert page["data"] == []
        assert page["total"] == 3

    def test_get_by_task_id(self, seeded_service):
        """Two trains share TASK-A — both must be returned."""
        result = seeded_service.get_by_task_id("TASK-A")
        assert result["total"] == 2
        task_ids = {t["task_id"] for t in result["data"]}
        assert task_ids == {"TASK-A"}

    def test_get_by_task_id_returns_empty_for_unknown(self, seeded_service):
        result = seeded_service.get_by_task_id("TASK-UNKNOWN")
        assert result["total"] == 0
        assert result["data"] == []


# ═══════════════════════════════════════════════════════════════════════ #
#  SEARCH                                                                #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.crud
class TestSearch:

    def test_search_by_name_case_insensitive(self, seeded_service):
        res = seeded_service.search("baku")          # lowercase matches "Baku Express"
        assert res["total"] >= 1
        assert any("Baku" in t["train_name"] for t in res["data"])

    def test_search_by_train_id(self, seeded_service):
        res = seeded_service.search("TEST-001")
        assert res["total"] == 1
        assert res["data"][0]["train_id"] == "TEST-001"

    def test_search_by_category(self, seeded_service):
        res = seeded_service.search("freight")
        assert res["total"] >= 1
        assert all(t["train_category"] == "freight" for t in res["data"])

    def test_search_no_match_returns_empty(self, seeded_service):
        res = seeded_service.search("xyzzy_no_match_123")
        assert res["total"] == 0
        assert res["data"] == []

    @pytest.mark.negative
    def test_search_empty_query_raises(self, seeded_service):
        with pytest.raises(ValueError):
            seeded_service.search("   ")

    def test_search_limit_respected(self, seeded_service):
        # All 3 match "TEST" but we limit to 1
        res = seeded_service.search("TEST", limit=1)
        assert len(res["data"]) == 1


# ═══════════════════════════════════════════════════════════════════════ #
#  FILTER                                                                #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.crud
class TestFilter:

    @pytest.mark.parametrize("status,expected_count", [
        ("active",   1),
        ("pending",  1),
        ("delayed",  1),
        ("done",     0),
        ("cancelled",0),
    ])
    def test_filter_by_status(self, seeded_service, status, expected_count):
        result = seeded_service.filter(train_status=status)
        assert result["total"] == expected_count

    @pytest.mark.parametrize("priority,expected_count", [
        ("high",     1),
        ("medium",   1),
        ("critical", 1),
        ("low",      0),
    ])
    def test_filter_by_priority(self, seeded_service, priority, expected_count):
        result = seeded_service.filter(train_priority=priority)
        assert result["total"] == expected_count

    def test_filter_by_category_freight(self, seeded_service):
        result = seeded_service.filter(train_category="freight")
        assert result["total"] == 1
        assert result["data"][0]["train_category"] == "freight"

    def test_filter_is_blocked_true(self, seeded_service):
        result = seeded_service.filter(is_blocked=True)
        assert result["total"] == 1
        assert result["data"][0]["train_id"] == "TEST-003"

    def test_filter_is_blocked_false(self, seeded_service):
        result = seeded_service.filter(is_blocked=False)
        assert result["total"] == 2

    def test_filter_by_task_id(self, seeded_service):
        result = seeded_service.filter(task_id="TASK-B")
        assert result["total"] == 1
        assert result["data"][0]["task_id"] == "TASK-B"

    def test_filter_no_params_returns_all(self, seeded_service):
        result = seeded_service.filter()
        assert result["total"] == 3

    def test_filter_combined_category_and_priority(self, seeded_service):
        result = seeded_service.filter(train_category="cargo", train_priority="critical")
        assert result["total"] == 1

    def test_filter_pagination_limit(self, seeded_service):
        result = seeded_service.filter(limit=1)
        assert len(result["data"]) == 1
        assert result["total"] == 3

    def test_filter_combined_no_match(self, seeded_service):
        # freight + critical doesn't exist in seed
        result = seeded_service.filter(train_category="freight", train_priority="critical")
        assert result["total"] == 0


# ═══════════════════════════════════════════════════════════════════════ #
#  UPDATE                                                                #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.crud
class TestUpdate:

    def test_update_single_field(self, train_service):
        t = _create(train_service, train_status="pending")
        updated = train_service.update(t["_id"], TrainUpdate(train_status="active"))
        assert updated["train_status"] == "active"

    def test_update_multiple_fields(self, train_service):
        t = _create(train_service)
        updated = train_service.update(
            t["_id"],
            TrainUpdate(train_priority="critical", train_speed="express", is_blocked=True),
        )
        assert updated["train_priority"] == "critical"
        assert updated["train_speed"]    == "express"
        assert updated["is_blocked"]     is True

    def test_update_does_not_change_untouched_fields(self, train_service):
        t = _create(train_service, train_name="Original Name")
        train_service.update(t["_id"], TrainUpdate(train_status="done"))
        fetched = train_service.get_by_id(t["_id"])
        assert fetched["train_name"] == "Original Name"   # unchanged

    @pytest.mark.negative
    def test_update_nonexistent_raises_key_error(self, train_service):
        with pytest.raises(KeyError):
            train_service.update("ghost-id", TrainUpdate(train_status="done"))

    def test_update_by_task_id_updates_all_in_task(self, seeded_service):
        """TASK-A has 2 trains — both must be updated at once."""
        result = seeded_service.update_by_task_id(
            "TASK-A", TrainUpdate(train_status="done")
        )
        assert result["count"] == 2
        assert all(t["train_status"] == "done" for t in result["data"])

    def test_update_by_task_id_unknown_returns_empty(self, seeded_service):
        result = seeded_service.update_by_task_id("TASK-GHOST", TrainUpdate(train_status="done"))
        assert result["count"] == 0

    @pytest.mark.parametrize("new_status", ["pending", "active", "delayed", "done", "cancelled"])
    def test_update_all_status_transitions(self, train_service, new_status):
        t = _create(train_service)
        updated = train_service.update(t["_id"], TrainUpdate(train_status=new_status))
        assert updated["train_status"] == new_status


# ═══════════════════════════════════════════════════════════════════════ #
#  DELETE                                                                #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.mark.crud
class TestDelete:

    def test_delete_removes_record(self, train_service):
        t = _create(train_service)
        train_service.delete(t["_id"])
        with pytest.raises(KeyError):
            train_service.get_by_id(t["_id"])

    def test_delete_reduces_total_count(self, seeded_service):
        before = seeded_service.get_all()["total"]
        first_id = seeded_service.get_all()["data"][0]["_id"]
        seeded_service.delete(first_id)
        after = seeded_service.get_all()["total"]
        assert after == before - 1

    @pytest.mark.negative
    def test_delete_nonexistent_raises_key_error(self, train_service):
        with pytest.raises(KeyError):
            train_service.delete("does-not-exist")

    def test_delete_one_does_not_affect_others(self, seeded_service):
        data = seeded_service.get_all()["data"]
        to_delete = data[0]["_id"]
        remaining_ids = {d["_id"] for d in data[1:]}
        seeded_service.delete(to_delete)
        page = seeded_service.get_all()
        current_ids = {d["_id"] for d in page["data"]}
        assert remaining_ids == current_ids

    def test_double_delete_raises_on_second(self, train_service):
        t = _create(train_service)
        train_service.delete(t["_id"])
        with pytest.raises(KeyError):
            train_service.delete(t["_id"])   # second delete must fail