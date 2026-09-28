from __future__ import annotations

import json
from pathlib import Path

import pytest

REPORT = Path(__file__).with_name("report.json")
CONTRACT_REPORT = Path(__file__).with_name("contract-report.json")


def _report():
    if not REPORT.exists():
        pytest.skip("run `python -m tests.route_audit.sweep.run_sweep` first")
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_sweep_has_all_221_routes():
    report = _report()
    assert report["route_count"] == 221
    assert len(report["routes"]) == 221


def test_sweep_route_statuses_and_json_shape():
    report = _report()
    failures = [f"{r['method']} {r['path']} => {r.get('status')}" for r in report["routes"] if r.get("status_500")]
    assert not failures, failures


def test_sweep_invalid_inputs_never_500():
    report = _report()
    failures = [f"{r['method']} {r['path']} invalid => {r.get('invalid', {}).get('status')}" for r in report["routes"] if r.get("invalid", {}).get("status_500")]
    assert report["invalid_target_count"] == 220
    assert not failures, failures


def test_sweep_empty_probes_have_no_null_list_shape():
    report = _report()
    assert report["empty_probe_count"] == 11
    assert not [r for r in report["routes"] if (r.get("empty") or {}).get("is_null_list")]


# These are the four contract regressions found by the exhaustive Retrofit/Gson
# sweep.  A fixed case is deliberately a normal assertion; unfixed cases remain
# strict xfail until their own server/client contract is corrected.
_CONTRACT_CASES = [
    ("RA-sweep-01", "POST", "classes/pending_approval/bulk_approve"),
    ("RA-sweep-02", "GET", "exams/student/list"),
    ("RA-sweep-03", "GET", "homework/parent/child/{student_id}"),
    ("RA-sweep-04", "GET", "teachers/{id}/incomplete_classes"),
]
_FIXED_CONTRACT_CASES = {"RA-sweep-01"}


def _contract_entry(method: str, path: str) -> dict:
    if not CONTRACT_REPORT.exists():
        pytest.skip("run `python -m tests.route_audit.sweep.run_contract` first")
    report = json.loads(CONTRACT_REPORT.read_text(encoding="utf-8"))
    return next(entry for entry in report["entries"] if entry["method"] == method and entry["path"] == path)


@pytest.mark.parametrize(
    "bug_id,method,path",
    [
        pytest.param(bug_id, method, path, marks=pytest.mark.xfail(strict=True, reason=bug_id))
        for bug_id, method, path in _CONTRACT_CASES
        if bug_id not in _FIXED_CONTRACT_CASES
    ]
    + [pytest.param(bug_id, method, path) for bug_id, method, path in _CONTRACT_CASES if bug_id in _FIXED_CONTRACT_CASES],
    ids=[bug_id for bug_id, _, _ in _CONTRACT_CASES if bug_id not in _FIXED_CONTRACT_CASES]
    + [bug_id for bug_id, _, _ in _CONTRACT_CASES if bug_id in _FIXED_CONTRACT_CASES],
)
def test_gson_contract_issue_is_absent(bug_id, method, path):
    """Each discovered contract issue becomes a normal regression after its fix."""
    entry = _contract_entry(method, path)
    assert entry["issues"] == []
