"""Inventory-level route audit scaffold for router crm.

Behavioral cases are marked blocked in docs/route-tests/routes/crm.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'POST' + ' ' + '/crm/leads/create',
    'GET' + ' ' + '/crm/leads/list',
    'POST' + ' ' + '/crm/leads/{id}/convert',
    'POST' + ' ' + '/crm/leads/{id}/notes',
    'POST' + ' ' + '/crm/register_online',
]

def test_crm_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'crm'}
    assert set(ROUTE_IDS) == expected
