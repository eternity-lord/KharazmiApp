"""Inventory-level route audit scaffold for router attendance.

Behavioral cases are marked blocked in docs/route-tests/routes/attendance.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'GET' + ' ' + '/admin/live_sessions',
    'GET' + ' ' + '/admin/live_sessions/{session_id}/roster',
    'POST' + ' ' + '/attendance/get',
    'POST' + ' ' + '/attendance/get_history',
    'GET' + ' ' + '/attendance/live/current',
    'POST' + ' ' + '/attendance/qr_check-in',
    'DELETE' + ' ' + '/attendance/session/{session_code}',
    'GET' + ' ' + '/attendance/session/{session_code}',
    'PUT' + ' ' + '/attendance/session/{session_code}',
    'POST' + ' ' + '/attendance/student_history',
    'POST' + ' ' + '/attendance/submit_session',
    'POST' + ' ' + '/attendance/{course_id}/start_live',
    'POST' + ' ' + '/attendance/{session_id}/cancel_live',
    'POST' + ' ' + '/attendance/{session_id}/end_live',
    'POST' + ' ' + '/attendance/{session_id}/live_status',
]

def test_attendance_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'attendance'}
    assert set(ROUTE_IDS) == expected
