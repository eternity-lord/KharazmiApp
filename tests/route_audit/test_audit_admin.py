"""Inventory-level route audit scaffold for router admin.

Behavioral cases are marked blocked in docs/route-tests/routes/admin.md until
the router is processed. This module still makes every route an explicit
pytest test input, so a missing route cannot disappear silently.
"""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'POST' + ' ' + '/admin/approve_class/{course_id}',
    'POST' + ' ' + '/admin/classes/suspend_bulk',
    'GET' + ' ' + '/admin/deleted_classes',
    'GET' + ' ' + '/admin/deleted_classes/{course_id}',
    'POST' + ' ' + '/admin/deleted_classes/{course_id}/restore',
    'GET' + ' ' + '/admin/institute_settings',
    'PUT' + ' ' + '/admin/institute_settings',
    'POST' + ' ' + '/admin/institute_settings/upload_logo',
    'GET' + ' ' + '/admin/parent_contacts',
    'GET' + ' ' + '/admin/pending_classes',
    'GET' + ' ' + '/admin/pricing_table',
    'PUT' + ' ' + '/admin/pricing_table',
    'DELETE' + ' ' + '/admin/reject_class/{course_id}',
    'GET' + ' ' + '/admin/session_history',
    'POST' + ' ' + '/admin/session_history/{session_id}/reopen',
    'GET' + ' ' + '/admin/students/search',
    'DELETE' + ' ' + '/admin/students/{id}',
    'GET' + ' ' + '/admin/students/{id}/full_profile',
    'POST' + ' ' + '/admin/students/{id}/toggle_suspend',
    'GET' + ' ' + '/admin/teachers/search',
    'GET' + ' ' + '/admin/teachers/{id}/credentials',
    'PUT' + ' ' + '/admin/teachers/{id}/credentials',
    'POST' + ' ' + '/admin/teachers/{id}/credentials/reset_password',
    'DELETE' + ' ' + '/admin/teachers/{teacher_id}',
    'POST' + ' ' + '/admin/teachers/{teacher_id}/suspend',
    'GET' + ' ' + '/admin/today_summary',
    'GET' + ' ' + '/admin/transactions/list',
    'GET' + ' ' + '/admin/transactions/list/excel',
    'DELETE' + ' ' + '/admin/transactions/{id}',
    'PUT' + ' ' + '/admin/transactions/{id}',
    'GET' + ' ' + '/config/share',
    'POST' + ' ' + '/config/share/update',
    'GET' + ' ' + '/dashboard/stats',
    'GET' + ' ' + '/sms/history',
    'POST' + ' ' + '/sms/send',
    'POST' + ' ' + '/sms/send_bulk',
    'POST' + ' ' + '/teachers/approve/{teacher_id}',
    'GET' + ' ' + '/teachers/pending',
    'DELETE' + ' ' + '/teachers/reject/{teacher_id}',
    'GET' + ' ' + '/test/debt_calculation',
    'POST' + ' ' + '/test/transaction_logic',
]

def test_admin_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'admin'}
    assert set(ROUTE_IDS) == expected
