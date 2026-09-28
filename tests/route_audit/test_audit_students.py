"""Inventory-level route audit scaffold for router students.

Behavioral cases are marked blocked in docs/route-tests/routes/students.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'POST' + ' ' + '/admin/students/{id}/send_portal_link',
    'POST' + ' ' + '/grades/submit',
    'GET' + ' ' + '/students/my_profile',
    'POST' + ' ' + '/students/register',
    'POST' + ' ' + '/students/register_and_enroll',
    'GET' + ' ' + '/students/search',
    'GET' + ' ' + '/students/search_simple',
    'PUT' + ' ' + '/students/update/{student_id}',
    'POST' + ' ' + '/students/{id}/upload_photo',
    'GET' + ' ' + '/students/{student_id}',
    'GET' + ' ' + '/students/{student_id}/communication_history',
    'GET' + ' ' + '/students/{student_id}/grades',
    'GET' + ' ' + '/students/{student_id}/installments',
]

def test_students_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'students'}
    assert set(ROUTE_IDS) == expected
