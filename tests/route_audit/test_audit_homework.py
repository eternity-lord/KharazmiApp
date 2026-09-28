"""Inventory-level route audit scaffold for router homework.

Behavioral cases are marked blocked in docs/route-tests/routes/homework.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'POST' + ' ' + '/homework/create',
    'GET' + ' ' + '/homework/parent/child/{student_id}',
    'GET' + ' ' + '/homework/student/list',
    'POST' + ' ' + '/homework/submissions/{homework_id}/submit',
    'POST' + ' ' + '/homework/submissions/{sub_id}/grade',
    'DELETE' + ' ' + '/homework/{id}',
]

def test_homework_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'homework'}
    assert set(ROUTE_IDS) == expected
