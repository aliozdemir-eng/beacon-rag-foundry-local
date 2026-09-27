"""A tiny JSON-backed store for the assignment's Phase 3 test set.

Each test case is a question plus an optional note on what's expected
("should cite the SQLite doc", "should say it doesn't know", ...). Running a
case calls the same answer_question() pipeline used everywhere else and
records the result; grading whether that result was actually correct is left
to a human (a free-text answer can't be graded automatically), captured as a
pass/fail/None verdict.
"""

import json
import time
import uuid

from . import config

TESTS_PATH = config.BASE_DIR / "data" / "test_cases.json"


def _load() -> list[dict]:
    if not TESTS_PATH.exists():
        return []
    return json.loads(TESTS_PATH.read_text(encoding="utf-8"))


def _save(cases: list[dict]) -> None:
    TESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TESTS_PATH.write_text(json.dumps(cases, indent=2, ensure_ascii=False), encoding="utf-8")


def list_cases() -> list[dict]:
    return _load()


def add_case(question: str, expected_note: str = "") -> dict:
    cases = _load()
    case = {
        "id": uuid.uuid4().hex[:8],
        "question": question,
        "expected_note": expected_note,
        "verdict": None,  # "pass" | "fail" | None
        "last_answer": None,
        "last_sources": [],
        "last_run_at": None,
    }
    cases.append(case)
    _save(cases)
    return case


def delete_case(case_id: str) -> None:
    _save([c for c in _load() if c["id"] != case_id])


def get_case(case_id: str) -> dict | None:
    return next((c for c in _load() if c["id"] == case_id), None)


def update_result(case_id: str, answer: str, sources: list[str]) -> dict | None:
    cases = _load()
    updated = None
    for c in cases:
        if c["id"] == case_id:
            c["last_answer"] = answer
            c["last_sources"] = sources
            c["last_run_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            c["verdict"] = None  # a fresh run invalidates any prior verdict
            updated = c
    _save(cases)
    return updated


def set_verdict(case_id: str, verdict: str | None) -> dict | None:
    cases = _load()
    updated = None
    for c in cases:
        if c["id"] == case_id:
            c["verdict"] = verdict
            updated = c
    _save(cases)
    return updated
