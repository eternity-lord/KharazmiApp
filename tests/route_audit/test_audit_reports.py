"""Inventory-level route audit scaffold for router reports.

Behavioral cases are marked blocked in docs/route-tests/routes/reports.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'GET' + ' ' + '/reports/chart-data',
    'GET' + ' ' + '/reports/debtors',
    'GET' + ' ' + '/reports/debtors/excel',
    'GET' + ' ' + '/reports/financial',
    'GET' + ' ' + '/reports/financial/excel',
    'GET' + ' ' + '/reports/financial_summary',
    'GET' + ' ' + '/reports/student_profile/print',
    'GET' + ' ' + '/reports/student_statement',
    'GET' + ' ' + '/reports/student_statement/print',
]

def test_reports_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'reports'}
    assert set(ROUTE_IDS) == expected
