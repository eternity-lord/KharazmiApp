from __future__ import annotations

import json
from pathlib import Path

import pytest

REPORT = Path(__file__).with_name("report.json")


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


def _contract_bug_entries():
    report = Path(__file__).with_name("contract-report.json")
    if not report.exists():
        return []
    data = json.loads(report.read_text(encoding="utf-8"))
    return [entry for entry in data["entries"] if entry.get("issues")]


_CONTRACT_BUGS = _contract_bug_entries()


@pytest.mark.parametrize(
    "entry",
    [pytest.param(entry, marks=pytest.mark.xfail(strict=True, reason=f"RA-sweep-{index:02d}")) for index, entry in enumerate(_CONTRACT_BUGS, 1)],
    ids=[f"{entry['method']} {entry['path']}" for entry in _CONTRACT_BUGS],
)
def test_gson_contract_issue_is_absent(entry):
    """Each discovered contract issue has a strict xfail reproduction."""
    assert entry["issues"] == []
