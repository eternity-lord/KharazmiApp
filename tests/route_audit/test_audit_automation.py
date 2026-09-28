"""Inventory-level route audit scaffold for router automation.

Behavioral cases are marked blocked in docs/route-tests/routes/automation.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'GET' + ' ' + '/automation/logs',
    'GET' + ' ' + '/automation/rules',
    'POST' + ' ' + '/automation/rules',
    'PUT' + ' ' + '/automation/rules/{rule_id}',
    'POST' + ' ' + '/automation/run_rules',
]

def test_automation_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'automation'}
    assert set(ROUTE_IDS) == expected
