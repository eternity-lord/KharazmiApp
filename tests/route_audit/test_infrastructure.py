from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from .kotlin_contract import audit_payload, discover_models
from .oracle import assert_invariants, build_oracle


def test_seed_is_isolated_and_has_required_states(audit_context):
    path = Path(audit_context["path"])
    assert path.name != "gaj_db.db"
    assert audit_context["manifest"]["counts"]["students"] == 30
    assert audit_context["manifest"]["counts"]["courses"] >= 6
    con = sqlite3.connect(path)
    try:
        assert con.execute("select count(*) from transactions").fetchone()[0] >= 5
        assert con.execute("select count(*) from installments").fetchone()[0] >= 4
    finally:
        con.close()


def test_oracle_does_not_need_production_db(db):
    snapshot = build_oracle(db)
    assert snapshot.enrollments[1].net_tuition == 1_000_000
    assert snapshot.enrollments[1].due == 700_000
    assert_invariants(snapshot)


def test_kotlin_contract_detects_known_contract_risk():
    models = discover_models()
    # ParentExamItem is the known max_score Int/decimal mismatch when present.
    if "ParentExamItem" in models:
        issues = audit_payload("ParentExamItem", {"max_score": 12.5})
        assert any(issue.kind == "int-parse" and issue.field == "max_score" for issue in issues)
    else:
        pytest.skip("ParentExamItem is not present in the checked-out Android source")
