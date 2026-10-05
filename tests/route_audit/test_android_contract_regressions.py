from __future__ import annotations

import pytest

from .kotlin_contract import audit_payload, discover_models


@pytest.mark.xfail(strict=True, reason="RA-finance-02")
def test_parent_financial_dashboard_accepts_a_valid_parent_session(client, auth_headers):
    # This call proves the selected parent role/session maps to student 1 before
    # testing the parallel parent-finance dashboard response.
    homework = client.get("/homework/parent/child/1", headers=auth_headers["parent"])
    assert homework.status_code == 200
    response = client.get("/finance/parent/dashboard", headers=auth_headers["parent"])
    assert response.status_code == 200
    assert response.json()["wallet"]["balance"] == -5_000


def test_student_financial_dashboard_screen_fields_are_present(client, auth_headers):
    """StudentProfileActivity currently consumes enrollments, not recent_transactions (Q-008)."""
    response = client.get("/finance/student/1/dashboard", headers=auth_headers["student"])
    assert response.status_code == 200
    body = response.json()
    assert body["enrollments"]
    assert {row["enrollment_id"] for row in body["enrollments"]} == {1, 2}
    assert all(row.get("course_title") for row in body["enrollments"])


@pytest.mark.xfail(strict=True, reason="RA-homework-01")
def test_parent_homework_wire_items_match_android_display_model(client, auth_headers, db):
    """A graded item displays score/max_score; the model contract must carry both."""
    import models

    submission = db.query(models.HomeworkSubmission).filter_by(homework_id=1, student_id=1).one()
    original = (submission.status, submission.score)
    try:
        submission.status, submission.score = "graded", 17.0
        db.commit()
        response = client.get("/homework/parent/child/1", headers=auth_headers["parent"])
        assert response.status_code == 200
        item = next(row for row in response.json() if row["id"] == 1)
        assert item["score"] == 17.0
        issues = audit_payload("HomeworkItem", item, discover_models())
        assert issues == []
    finally:
        submission.status, submission.score = original
        db.commit()


@pytest.mark.parametrize(
    "path,role,model",
    [
        pytest.param("/attendance/live/current", "teacher", "LiveCurrentResponse", marks=pytest.mark.xfail(strict=True, reason="RA-attendance-01"), id="teacher-current-live"),
        pytest.param("/admin/live_sessions", "admin", "LiveSessionItem", marks=pytest.mark.xfail(strict=True, reason="RA-attendance-02"), id="admin-live-list"),
        pytest.param("/admin/live_sessions/1/roster", "admin", "LiveRosterResponse", marks=pytest.mark.xfail(strict=True, reason="RA-attendance-03"), id="admin-live-roster"),
        pytest.param("/teachers/1/today_summary", "teacher", "TeacherTodaySummary", marks=pytest.mark.xfail(strict=True, reason="RA-teachers-01"), id="teacher-today-summary"),
    ],
)
def test_live_timestamp_values_deserialize_as_android_long(client, auth_headers, path, role, model):
    response = client.get(path, headers=auth_headers[role])
    assert response.status_code == 200
    payload = response.json()
    if model == "LiveSessionItem":
        assert payload
        payloads = payload
    else:
        assert payload is not None
        payloads = [payload]
    issues = [
        issue
        for item in payloads
        for issue in audit_payload(model, item, discover_models())
    ]
    assert not [issue for issue in issues if issue.kind in ("int-parse", "long-overflow", "long-parse")]


def test_student_portal_display_fields_are_present(client, auth_headers):
    """The current student screen reads name and national_code; parent_mobile is Q-007."""
    response = client.get("/students/my_profile", headers=auth_headers["student"])
    assert response.status_code == 200
    profile = response.json()
    assert profile["info"]["name"] == "دانش‌آموز تست 1"
    assert profile["info"]["national_code"] == "0020000001"


def test_incomplete_class_dialog_minimum_wire_fields_are_present(client, auth_headers):
    """Current screen reads identity fields only; omitted shared-model fields are Q-006."""
    response = client.get("/teachers/1/incomplete_classes", headers=auth_headers["teacher"])
    assert response.status_code == 200
    items = response.json()
    assert items
    assert all({"id", "title", "code"} <= item.keys() for item in items)
