"""Inventory-level route audit scaffold for router serve_upload.

Behavioral cases are marked blocked in docs/route-tests/routes/serve_upload.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'GET' + ' ' + '/uploads/{filename}',
]

def test_serve_upload_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'serve_upload'}
    assert set(ROUTE_IDS) == expected
