"""Inventory-level route audit scaffold for router analytics.

Behavioral cases are marked blocked in docs/route-tests/routes/analytics.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'GET' + ' ' + '/analytics/classes',
    'GET' + ' ' + '/analytics/dashboard',
    'GET' + ' ' + '/analytics/enrollment_funnel',
    'GET' + ' ' + '/analytics/export/excel',
    'GET' + ' ' + '/analytics/export/pdf',
    'GET' + ' ' + '/analytics/teachers',
]

def test_analytics_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'analytics'}
    assert set(ROUTE_IDS) == expected
