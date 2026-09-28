"""Inventory-level route audit scaffold for router classes.

Behavioral cases are marked blocked in docs/route-tests/routes/classes.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'POST' + ' ' + '/admin/classes/{course_id}/suspend_s',
    'POST' + ' ' + '/classes/create',
    'GET' + ' ' + '/classes/deletion_requests',
    'POST' + ' ' + '/classes/deletion_requests/{request_id}/approve',
    'POST' + ' ' + '/classes/deletion_requests/{request_id}/reject',
    'GET' + ' ' + '/classes/list',
    'GET' + ' ' + '/classes/pending_approval',
    'POST' + ' ' + '/classes/pending_approval/bulk_approve',
    'POST' + ' ' + '/classes/pending_approval/bulk_reject',
    'PUT' + ' ' + '/classes/update',
    'PUT' + ' ' + '/classes/update_info/{course_id}',
    'GET' + ' ' + '/classes/{class_id}/students_full/excel',
    'DELETE' + ' ' + '/classes/{course_id}',
    'GET' + ' ' + '/classes/{course_id}/details',
    'POST' + ' ' + '/classes/{course_id}/request_delete',
    'POST' + ' ' + '/classes/{course_id}/suspend',
    'GET' + ' ' + '/classes/{id}/full_report',
    'GET' + ' ' + '/classes/{id}/students_full',
    'POST' + ' ' + '/enrollments/add',
    'POST' + ' ' + '/enrollments/add_bulk',
    'DELETE' + ' ' + '/enrollments/{enrollment_id}',
]

def test_classes_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'classes'}
    assert set(ROUTE_IDS) == expected
