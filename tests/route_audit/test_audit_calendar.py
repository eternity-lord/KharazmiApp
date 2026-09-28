"""Inventory-level route audit scaffold for router calendar.

Behavioral cases are marked blocked in docs/route-tests/routes/calendar.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'POST' + ' ' + '/calendar/check_conflicts',
    'GET' + ' ' + '/calendar/events',
    'POST' + ' ' + '/rooms/create',
    'GET' + ' ' + '/rooms/list',
]

def test_calendar_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'calendar'}
    assert set(ROUTE_IDS) == expected
