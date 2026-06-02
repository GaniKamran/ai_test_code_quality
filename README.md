# ai_test_code_quality

A self-contained **Software-Engineering Evaluation** sample project built for the
[Mindrift / Toloka](https://toloka.ai/mindrift/) AI model training programme.

It demonstrates the exact skills listed in the job description:
`pytest` · `Docker` · `Linux/Bash` · production-quality test design.

---

## Project layout

```
ai_test_code_quality/
├── app/
│   ├── models.py        # Domain: Task dataclass, Priority / TaskStatus enums
│   ├── repository.py    # In-memory store  ← contains 5 intentional bugs
│   └── service.py       # Business logic   ← contains 3 intentional bugs
├── test/
│   ├── conftest.py      # Shared fixtures (session / function scope, DI)
│   ├── test_models.py   # Pure unit tests for models
│   ├── test_repository.py  # Repository tests — exposes BUG-2,3,4,5
│   └── test_service.py  # Service tests  — exposes BUG-5,6,7,8
│                          # incl. monkeypatch (frozen datetime)
├── checker/
│   ├── run_checks.sh    # Bash gate: install deps → run pytest → colour report
│   └── bug_report.py   # Maps failing test names → Bug IDs (--json flag)
├── Dockerfile           # Multi-stage build, pinned deps, non-root user
├── pytest.ini           # pythonpath=. so app/ is importable without install
└── requirements.txt
```

---

## Quick start (local venv)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# run the full suite (11 intentional failures expected)
pytest

# run the bash checker (colour-coded output + bug list)
bash checker/run_checks.sh

# parse last_run.txt into a structured bug report
python3 checker/bug_report.py
python3 checker/bug_report.py --json
```

---

## Quick start (Docker)

```bash
docker build -t ai_test_quality .
docker run --rm ai_test_quality                       # run tests
docker run --rm ai_test_quality bash checker/run_checks.sh
```

---

## Intentional bugs (exercise)

| Bug ID | Location | Description |
|--------|----------|-------------|
| BUG-2 | `repository.py` `list_by_priority()` | Uses `>` instead of `>=` — exact-match priority excluded |
| BUG-3 | `repository.py` `delete()` | Returns `False` for missing ID instead of raising `KeyError` |
| BUG-4 | `repository.py` `search()` | Case-sensitive — "fix" doesn't match "Fix" |
| BUG-5 | `repository.py` `count_by_status()` | Raises `NotImplementedError` — not implemented |
| BUG-6 | `service.py` `create_task()` | Accepts empty / whitespace-only title |
| BUG-7 | `service.py` `close_task()` | Sets `CANCELLED` instead of `DONE` |
| BUG-8 | `service.py` `get_overdue_tasks()` | Includes tasks with `due_at=None` (logic inverted) |

---

## pytest techniques demonstrated

| Technique | Where |
|-----------|-------|
| `@pytest.fixture` (function scope) | `conftest.py` |
| Fixture composition (DI chain) | `conftest.py` → `service` uses `repo_with_tasks` |
| `@pytest.mark.parametrize` | `test_models.py`, `test_repository.py` |
| `monkeypatch` — frozen `datetime.utcnow` | `test_service.py::test_monkeypatch_frozen_time` |
| `pytest.raises` with `match=` | `test_service.py::TestCreateTask` |
| Class-grouped tests | All test files |
| `conftest.py` shared across modules | `test/conftest.py` |
