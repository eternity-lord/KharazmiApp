"""Inventory-level route audit scaffold for router branches.

Behavioral cases are marked blocked in docs/route-tests/routes/branches.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'GET' + ' ' + '/branches',
    'POST' + ' ' + '/branches',
    'PUT' + ' ' + '/branches/{branch_id}',
    'POST' + ' ' + '/branches/{branch_id}/suspend',
    'GET' + ' ' + '/dashboard/branch_stats',
    'GET' + ' ' + '/resources',
    'POST' + ' ' + '/resources',
    'POST' + ' ' + '/resources/bookings',
    'PUT' + ' ' + '/resources/{id}',
]

def test_branches_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'branches'}
    assert set(ROUTE_IDS) == expected
