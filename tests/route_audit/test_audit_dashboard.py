"""Dashboard KPI and push contract audit."""
from .route_registry import route_id, routes

ROUTE_IDS = [
    'GET' + ' ' + '/dashboard/kpis',
    'GET' + ' ' + '/dashboard/push_status',
]


def test_dashboard_route_inventory_is_explicit():
    expected = {route_id(row) for row in routes() if row["handler"].split(".")[1] == 'dashboard'}
    assert set(ROUTE_IDS) == expected


def test_dashboard_kpis_have_independent_seed_values_and_push_is_local(client, auth_headers):
    import routers.dashboard as dashboard

    dashboard._clear_dashboard_cache()
    response = client.get("/dashboard/kpis", headers=auth_headers["admin"])
    assert response.status_code == 200, response.text
    assert response.json() == {
        "today_revenue": 0,
        "total_overdue_amount": 700_000,
        "overdue_installments_count": 2,
        "active_students_count": 29,
        "suspicious_alerts_count": 0,
        "dunning_pending_count": 0,
    }
    push = client.get("/dashboard/push_status", headers=auth_headers["admin"])
    assert push.status_code == 200
    assert push.json() == {"fcm_configured": False, "device_token_count": 0}
    assert "private_key" not in push.text and "api_key" not in push.text
