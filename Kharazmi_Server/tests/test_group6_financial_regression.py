"""Regression tests for the group 6 settlement ledger contract.

These tests use an in-memory database and never touch the live gaj_db.db file.
"""
import json
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from routers.teachers import _write_settlement_reversal


class TestGroup6SettlementReversal(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()

    def tearDown(self):
        self.db.rollback()
        self.db.close()
        self.engine.dispose()

    def test_reversal_is_scoped_and_does_not_touch_student_teacher_wallet(self):
        teacher = models.Teacher(first_name="T", last_name="G6", mobile="g6-t", national_code="g6-t")
        student = models.Student(first_name="S", last_name="G6", national_code="g6-s", wallet_teacher=-700)
        self.db.add_all([teacher, student])
        self.db.flush()
        course = models.Course(
            title="G6", code="g6-c", teacher_id=teacher.id, days_of_week="شنبه",
            class_time="10:00", is_deleted=False, is_suspended=False, is_paused=False,
        )
        self.db.add(course)
        self.db.flush()
        session = models.SessionLog(
            course_id=course.id, date="2099/01/01", time="10:00",
            final_teacher_cost=700, is_penalty_settled=False, is_deleted=False,
        )
        self.db.add(session)
        self.db.flush()
        attendance = models.Attendance(
            session_id=session.id, student_id=student.id, status="Present",
            is_billed=True, is_deleted=False,
        )
        payout = models.Transaction(amount=-700, type="settlement_payout", target_wallet="teacher")
        settlement = models.Settlement(
            teacher_id=teacher.id, total_amount=700, session_count=1,
            session_ids_json=json.dumps([session.id]),
        )
        self.db.add_all([attendance, payout, settlement])
        self.db.flush()
        payout.settlement_id = settlement.id
        settlement.payout_transaction_id = payout.id
        before_wallet = student.wallet_teacher

        session_ids, reversal = _write_settlement_reversal(self.db, settlement, "اشتباه در ثبت", 101)
        self.db.flush()
        self.db.refresh(attendance)
        self.db.refresh(student)

        self.assertEqual(session_ids, [session.id])
        self.assertTrue(settlement.is_reversed)
        self.assertFalse(attendance.is_billed)
        self.assertEqual(student.wallet_teacher, before_wallet)
        self.assertEqual(reversal.type, "reversal")
        self.assertEqual(reversal.amount, 700)
        self.assertEqual(reversal.settlement_id, settlement.id)

    def test_http_reverse_and_edit_routes_match_teacher_and_settlement_ids(self):
        """قرارداد واقعی HTTP: ردیف نمایش‌داده‌شده در history باید همان ID قابل‌عملیات باشد."""
        from dependencies import check_admin_access, get_db
        from main import app

        teacher = models.Teacher(first_name="T", last_name="HTTP", mobile="g6-http-t", national_code="g6-http-t")
        student = models.Student(first_name="S", last_name="HTTP", national_code="g6-http-s", wallet_teacher=-500)
        self.db.add_all([teacher, student]); self.db.flush()
        course = models.Course(title="HTTP", code="g6-http-c", teacher_id=teacher.id,
                               days_of_week="شنبه", class_time="10:00", is_deleted=False,
                               is_suspended=False, is_paused=False)
        self.db.add(course); self.db.flush()
        session = models.SessionLog(course_id=course.id, date="1405/01/01", time="10:00",
                                    final_teacher_cost=500, is_penalty_settled=True, is_deleted=False)
        self.db.add(session); self.db.flush()
        self.db.add(models.Attendance(session_id=session.id, student_id=student.id,
                                      status="Present", is_billed=True, is_deleted=False))
        payout = models.Transaction(amount=-500, type="settlement_payout", target_wallet="teacher")
        settlement = models.Settlement(teacher_id=teacher.id, total_amount=500, session_count=1,
                                       session_ids_json=json.dumps([session.id]))
        self.db.add_all([payout, settlement]); self.db.flush()
        payout.settlement_id = settlement.id
        settlement.payout_transaction_id = payout.id
        self.db.commit()

        def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[check_admin_access] = lambda: "admin"
        try:
            client = TestClient(app)
            response = client.post(
                f"/teachers/{teacher.id}/settlements/{settlement.id}/reverse",
                params={"reason": "رگرسیون HTTP"},
            )
            self.assertEqual(response.status_code, 200, response.text)

            replacement = models.Settlement(teacher_id=teacher.id, total_amount=500,
                                            session_count=1, session_ids_json=json.dumps([session.id]))
            replacement_payout = models.Transaction(amount=-500, type="settlement_payout", target_wallet="teacher")
            self.db.add_all([replacement, replacement_payout]); self.db.flush()
            replacement.payout_transaction_id = replacement_payout.id
            replacement_payout.settlement_id = replacement.id
            self.db.commit()
            response = client.put(
                f"/teachers/{teacher.id}/settlements/{replacement.id}/edit",
                json={"total_amount": 450, "reason": "رگرسیون تعدیل HTTP"},
            )
            self.assertEqual(response.status_code, 200, response.text)
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
