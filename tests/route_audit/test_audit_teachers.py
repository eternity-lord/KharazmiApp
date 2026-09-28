"""Inventory-level route audit scaffold for router teachers.

Behavioral cases are marked blocked in docs/route-tests/routes/teachers.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'GET' + ' ' + '/teachers/list',
    'GET' + ' ' + '/teachers/list/excel',
    'POST' + ' ' + '/teachers/register',
    'PUT' + ' ' + '/teachers/update/{teacher_id}',
    'GET' + ' ' + '/teachers/{id}/full_profile',
    'GET' + ' ' + '/teachers/{id}/today_summary',
    'POST' + ' ' + '/teachers/{id}/upload_photo',
    'GET' + ' ' + '/teachers/{teacher_id}',
    'GET' + ' ' + '/teachers/{teacher_id}/classes',
    'GET' + ' ' + '/teachers/{teacher_id}/collaboration_summary',
    'GET' + ' ' + '/teachers/{teacher_id}/communication_history',
    'GET' + ' ' + '/teachers/{teacher_id}/incomplete_classes',
    'GET' + ' ' + '/teachers/{teacher_id}/pending_classes',
    'GET' + ' ' + '/teachers/{teacher_id}/pending_settlement',
    'POST' + ' ' + '/teachers/{teacher_id}/settle',
    'GET' + ' ' + '/teachers/{teacher_id}/settlement_history',
    'PUT' + ' ' + '/teachers/{teacher_id}/settlements/{settlement_id}/edit',
    'POST' + ' ' + '/teachers/{teacher_id}/settlements/{settlement_id}/reverse',
]

def test_teachers_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'teachers'}
    assert set(ROUTE_IDS) == expected
