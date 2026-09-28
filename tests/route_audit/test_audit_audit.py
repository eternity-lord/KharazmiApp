"""Inventory-level route audit scaffold for router audit.

Behavioral cases are marked blocked in docs/route-tests/routes/audit.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'GET' + ' ' + '/audit/suspicious_patterns',
]

def test_audit_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'audit'}
    assert set(ROUTE_IDS) == expected
