"""Inventory-level route audit scaffold for router parent.

Behavioral cases are marked blocked in docs/route-tests/routes/parent.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'GET' + ' ' + '/parent/child_profile',
    'POST' + ' ' + '/parent/login',
    'GET' + ' ' + '/parent/portal',
    'POST' + ' ' + '/parent/request_otp',
    'POST' + ' ' + '/parent/select_child',
]

def test_parent_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'parent'}
    assert set(ROUTE_IDS) == expected
