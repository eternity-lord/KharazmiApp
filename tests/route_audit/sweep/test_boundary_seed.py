from __future__ import annotations

import json
from pathlib import Path


REPORT = Path(__file__).with_name("boundary-report.json")


def test_boundary_seed_route_and_gson_contracts():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert len(report["routes"]) == 4
    assert not [row for row in report["routes"] if row["status_500"]]
    assert report["values"] == {
        "exam_99_max_score": 12.5,
        "transaction_99_amount": 2**31 + 1,
        "transaction_99_date": "",
        "transaction_99_description": None,
        "homework_99_description": "",
        "homework_99_due_date": "",
        "incomplete_students_preview_are_lists": True,
    }
    assert report["gson_issue_count"] == 0
    assert all(not issues for issues in report["gson_vectors"].values())
