"""Reproductions for the four known findings carried from the prior audit.

These tests assert the desired behavior, not the currently observed behavior;
strict xfail keeps CI green while preserving a visible reproduction.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from .kotlin_contract import audit_payload


def test_O02_android_push_client_registers_FCM_token():
    root = Path(__file__).parents[2] / "KharazmiAdmin/app/src/main"
    source = "\n".join(path.read_text(encoding="utf-8") for path in (root / "java").rglob("*.kt"))
    model_source = (root / "java/com/example/kharazmiadmin/AppModels.kt").read_text(encoding="utf-8")
    manifest = (root / "AndroidManifest.xml").read_text(encoding="utf-8")
    gradle = (root.parents[1] / "build.gradle.kts").read_text(encoding="utf-8")
    assert "FirebaseMessaging.getInstance" in source
    assert '@POST("auth/device_token")' in source
    assert '@SerializedName("token") val token: String' in model_source
    assert "override fun onNewToken(token: String)" in source
    assert "PushTokenRegistration.refreshAndRegister(applicationContext)" in source
    assert 'android:name=".PushMessagingService"' in manifest
    assert "firebase-messaging" in gradle
    assert "FCM_SERVER_KEY" not in source, "FCM server credentials must stay on the backend"


def test_O12_unpublished_exam_is_hidden_from_student(client, auth_headers):
    response = client.get("/exams/student/list", headers=auth_headers["student"])
    assert response.status_code == 200, response.text
    assert all(row["id"] != 2 for row in response.json())


def test_O14_parent_exam_decimal_max_score_is_not_parsed_as_Int():
    issues = audit_payload("ParentExamItem", {"course_title": "ریاضی", "title": "آزمون", "date": "1405/06/25", "max_score": 12.5})
    assert not any(issue.kind == "int-parse" and issue.field == "max_score" for issue in issues)


@pytest.mark.xfail(strict=True, reason="RA-admin-19")
def test_O19_restore_class_restores_financial_history_atomically(client, auth_headers, db):
    import models
    response = client.post("/admin/deleted_classes/4/restore", json={"mode": "metadata_only", "reason": "audit reproduction"}, headers=auth_headers["admin"])
    try:
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["mode"] == "full"
        assert body["finances_untouched"] is False
        assert db.query(models.Enrollment).filter(models.Enrollment.course_id == 4, models.Enrollment.is_deleted == False).count() > 0
    finally:
        course = db.get(models.Course, 4)
        if course:
            course.is_deleted = True
        db.query(models.ClassRestoreLog).filter(models.ClassRestoreLog.course_id == 4).delete(synchronize_session=False)
        db.query(models.ActivityLog).filter(models.ActivityLog.target_id == 4, models.ActivityLog.action == "restore_class_metadata").delete(synchronize_session=False)
        db.commit()
