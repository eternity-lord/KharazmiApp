"""Inventory-level route audit scaffold for router auth.

Behavioral cases are marked blocked in docs/route-tests/routes/auth.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'POST' + ' ' + '/auth/change-mobile',
    'POST' + ' ' + '/auth/change-password',
    'POST' + ' ' + '/auth/device_token',
    'POST' + ' ' + '/auth/login',
    'POST' + ' ' + '/auth/logout',
    'GET' + ' ' + '/auth/me',
    'POST' + ' ' + '/auth/student/login',
    'POST' + ' ' + '/auth/student/request_otp',
    'GET' + ' ' + '/notifications',
    'POST' + ' ' + '/notifications/read_all',
    'GET' + ' ' + '/notifications/unread_count',
    'POST' + ' ' + '/notifications/{id}/read',
]

def test_auth_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'auth'}
    assert set(ROUTE_IDS) == expected
