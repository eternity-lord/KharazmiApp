"""Value and state-transition audit for routers.attendance."""
from __future__ import annotations

from .oracle import build_oracle


ATTENDANCE_ROUTES = [
    ("GET", "/admin/live_sessions"),
    ("GET", "/admin/live_sessions/{session_id}/roster"),
    ("POST", "/attendance/get"),
    ("POST", "/attendance/get_history"),
    ("GET", "/attendance/live/current"),
    ("POST", "/attendance/qr_check-in"),
    ("DELETE", "/attendance/session/{session_code}"),
    ("GET", "/attendance/session/{session_code}"),
    ("PUT", "/attendance/session/{session_code}"),
    ("POST", "/attendance/student_history"),
    ("POST", "/attendance/submit_session"),
    ("POST", "/attendance/{course_id}/start_live"),
    ("POST", "/attendance/{session_id}/cancel_live"),
    ("POST", "/attendance/{session_id}/end_live"),
    ("POST", "/attendance/{session_id}/live_status"),
]
ROUTE_IDS = [f"{method} {path}" for method, path in ATTENDANCE_ROUTES]


def test_attendance_route_inventory_is_explicit(client):
    paths = {(path, method.upper()) for path, operations in client.app.openapi()["paths"].items() for method in operations}
    assert [(m, p) for m, p in ATTENDANCE_ROUTES if (p, m.upper()) not in paths] == []


def test_session_details_and_class_attendance_have_values(client, auth_headers):
    headers = auth_headers["admin"]
    details = client.get("/attendance/session/5001", headers=headers)
    by_date = client.post("/attendance/get", json={"course_id": 1, "date": "1405/06/10"}, headers=headers)
    history = client.post("/attendance/get_history", json={"course_id": 1}, headers=headers)
    student = client.post("/attendance/student_history", json={"student_id": 1, "course_id": 1}, headers=headers)
    assert details.status_code == by_date.status_code == history.status_code == student.status_code == 200
    body = details.json()
    assert body["session_code"] == 5001
    assert body["class_title"] == "ریاضی پایه فعال"
    assert body["attendee_count"] == 3
    assert {item["status"] for item in body["items"]} == {"Present", "Late", "Absent"}
    assert by_date.json()[0]["name"] == "دانش‌آموز تست 1"
    assert history.json()[0]["date"] == "1405/06/10"
    assert history.json()[0]["total_cost"] == 600_000
    assert student.json()["present_count"] == 1
    assert student.json()["attendance_history"][0]["status"] == "حاضر"


def test_live_start_status_cancel_is_idempotent_without_financial_effect(client, auth_headers, db):
    import models
    headers = auth_headers["admin"]
    sessions_before = db.query(models.SessionLog).count()
    tx_before = db.query(models.Transaction).count()
    started = client.post("/attendance/1/start_live", headers=headers)
    assert started.status_code == 200, started.text
    live_id = started.json()["live_session_id"]
    assert started.json()["status"] == "LIVE"
    duplicate = client.post("/attendance/1/start_live", headers=headers)
    assert duplicate.status_code == 409
    saved = client.post(f"/attendance/{live_id}/live_status", json={"items": {"1": {"status": "Present", "excused": False}, "2": {"status": "Late", "excused": False}}}, headers=headers)
    assert saved.status_code == 200
    assert saved.json()["count"] == 2
    cancelled = client.post(f"/attendance/{live_id}/cancel_live", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    replay = client.post(f"/attendance/{live_id}/cancel_live", headers=headers)
    assert replay.status_code == 200
    db.expire_all()
    live = db.get(models.LiveSession, live_id)
    assert live.status == "CANCELLED"
    assert db.query(models.SessionLog).count() == sessions_before
    assert db.query(models.Transaction).count() == tx_before


def test_live_state_and_role_specific_reads(client, auth_headers):
    teacher_live = client.get("/attendance/live/current", headers=auth_headers["teacher"])
    admin_live = client.get("/attendance/live/current", headers=auth_headers["admin"])
    all_live = client.get("/admin/live_sessions", headers=auth_headers["admin"])
    roster = client.get("/admin/live_sessions/1/roster", headers=auth_headers["admin"])
    assert teacher_live.status_code == admin_live.status_code == all_live.status_code == roster.status_code == 200
    assert teacher_live.json()["live_session_id"] == 1
    assert admin_live.json() is None
    assert any(row["live_session_id"] == 1 and row["present"] == 1 for row in all_live.json())
    assert roster.json()["live_session_id"] == 1
    assert roster.json()["students"][0]["status"] == "Present"


def test_suspended_course_cannot_start_live_without_writing(client, auth_headers, db):
    import models
    before = db.query(models.LiveSession).count()
    response = client.post("/attendance/3/start_live", headers=auth_headers["admin"])
    assert response.status_code == 403
    db.expire_all()
    assert db.query(models.LiveSession).count() == before
