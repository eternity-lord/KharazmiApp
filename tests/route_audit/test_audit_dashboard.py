"""Inventory-level route audit scaffold for router dashboard.

Behavioral cases are marked blocked in docs/route-tests/routes/dashboard.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'GET' + ' ' + '/dashboard/kpis',
    'GET' + ' ' + '/dashboard/push_status',
]

def test_dashboard_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'dashboard'}
    assert set(ROUTE_IDS) == expected
