"""Inventory-level route audit scaffold for router exams.

Behavioral cases are marked blocked in docs/route-tests/routes/exams.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'POST' + ' ' + '/exams/attempts/{attempt_id}/submit',
    'POST' + ' ' + '/exams/attempts/{exam_id}/start',
    'POST' + ' ' + '/exams/create',
    'GET' + ' ' + '/exams/student/list',
    'POST' + ' ' + '/exams/{id}/questions',
    'GET' + ' ' + '/students/{student_id}/report_card',
    'GET' + ' ' + '/students/{student_id}/report_card/pdf',
]

def test_exams_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'exams'}
    assert set(ROUTE_IDS) == expected
