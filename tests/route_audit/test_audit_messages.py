"""Inventory-level route audit scaffold for router messages.

Behavioral cases are marked blocked in docs/route-tests/routes/messages.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'POST' + ' ' + '/messages/broadcast',
    'GET' + ' ' + '/messages/conversations',
    'POST' + ' ' + '/messages/conversations/create',
    'GET' + ' ' + '/messages/conversations/{id}/history',
    'POST' + ' ' + '/messages/conversations/{id}/pin',
    'POST' + ' ' + '/messages/conversations/{id}/send',
    'DELETE' + ' ' + '/messages/{id}',
]

def test_messages_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'messages'}
    assert set(ROUTE_IDS) == expected
