"""
Audit Radar - Fraud Detection System tests
Isolated read-only tests - does not modify finance/classes/students/auth routers
Covers: 403 for non-admin, 200 for admin, 3 suspicious patterns mock
"""
import datetime
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from models import Base, User, UserSession, Student, Teacher, Course, SessionLog, Attendance, Transaction, Enrollment, Branch
from main import app
from dependencies import get_db, hash_password


class TestAuditRadar(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # Seed branch
        self.db.add(Branch(id=1, name="مرکزی", active=True))
        self.db.commit()

        # Users: admin, secretary, teacher
        self.admin_user = User(id=1, username="09120000000", password=hash_password("123"), full_name="Admin", role="admin", sub_role="admin", branch_id=1)
        self.secretary_user = User(id=2, username="09121111111", password=hash_password("123"), full_name="Secretary", role="admin", sub_role="secretary", branch_id=1)
        self.teacher_user = User(id=3, username="09123333333", password=hash_password("101"), full_name="Teacher", role="teacher", sub_role="teacher", branch_id=1)
        self.db.add_all([self.admin_user, self.secretary_user, self.teacher_user])
        self.db.commit()

        # Teacher record matching teacher user
        self.teacher = Teacher(id=1, first_name="امیر", last_name="احمدی", national_code="0001000128", mobile="09123333333", teacher_code=101, is_approved=True, password=hash_password("101"))
        self.db.add(self.teacher)
        self.db.commit()

        # Students needed for FK
        self.student1 = Student(id=1, first_name="الارا", last_name="صیامی", national_code="0000000001", student_mobile="09120000001", parent_mobile="09120000001")
        self.student2 = Student(id=2, first_name="سارا", last_name="احمدی", national_code="0000000002", student_mobile="09120000002", parent_mobile="09120000002")
        self.db.add_all([self.student1, self.student2])
        self.db.commit()

        # Sessions tokens (use same tokens as teacher e2e for consistency)
        self.admin_session = UserSession(token="tok_admin", user_id=1, sub_role="admin", created_at=datetime.datetime.now())
        self.secretary_session = UserSession(token="tok_secretary", user_id=2, sub_role="secretary", created_at=datetime.datetime.now())
        self.teacher_session = UserSession(token="tok_teacher", user_id=3, sub_role="teacher", created_at=datetime.datetime.now())
        self.db.add_all([self.admin_session, self.secretary_session, self.teacher_session])
        self.db.commit()

        # Course for patterns
        self.course = Course(id=1, title="ریاضی ۱۰", code="MATH10", teacher_id=1, class_time="16:00")
        self.db.add(self.course)
        self.db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_403_non_admin_cannot_access_audit(self):
        # Secretary -> 403
        r = self.client.get("/audit/suspicious_patterns", headers={"Authorization": "Bearer tok_secretary"})
        self.assertEqual(r.status_code, 403, f"secretary should be 403 but got {r.status_code}: {r.text}")
        # Teacher -> 403
        r2 = self.client.get("/audit/suspicious_patterns", headers={"Authorization": "Bearer tok_teacher"})
        self.assertEqual(r2.status_code, 403, f"teacher should be 403 but got {r2.status_code}: {r2.text}")
        # No token -> 401
        r3 = self.client.get("/audit/suspicious_patterns")
        self.assertEqual(r3.status_code, 401)

    def test_200_admin_can_access_empty(self):
        r = self.client.get("/audit/suspicious_patterns", headers={"Authorization": "Bearer tok_admin"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, list)

    def test_pattern_A_suspicious_attendance_night(self):
        # Create suspicious session at 02:30 (00-05)
        sl = SessionLog(course_id=1, date="2026/01/01", time="02:30", start_time="02:30", final_teacher_cost=0, final_institute_share=0, cost_per_student=0, attendee_count=1, status="Finished")
        self.db.add(sl)
        self.db.commit()
        self.db.refresh(sl)
        r = self.client.get("/audit/suspicious_patterns", headers={"Authorization": "Bearer tok_admin"})
        self.assertEqual(r.status_code, 200)
        alerts = r.json()
        # Should contain at least one suspicious_attendance
        types = [a["type"] for a in alerts]
        self.assertIn("suspicious_attendance", types, f"expected suspicious_attendance in {alerts}")
        # Verify severity high
        for a in alerts:
            if a["type"] == "suspicious_attendance":
                self.assertEqual(a["severity"], "high")
                self.assertIn("02:30", a["description"])
                break

    def test_pattern_A_delayed_after_class_time(self):
        # Course class_time 16:00, session at 23:00 => diff 7h >5 => suspicious
        # Ensure previous test data isolated? This test creates fresh DB per test, so add delayed session
        sl = SessionLog(course_id=1, date="2026/01/02", time="23:00", start_time="23:00", final_teacher_cost=0, final_institute_share=0, cost_per_student=0, attendee_count=1, status="Finished")
        self.db.add(sl)
        self.db.commit()
        r = self.client.get("/audit/suspicious_patterns", headers={"Authorization": "Bearer tok_admin"})
        self.assertEqual(r.status_code, 200)
        alerts = [a for a in r.json() if a["type"] == "suspicious_attendance"]
        self.assertTrue(len(alerts) >= 1)
        found = any("تأخیر" in a["description"] or "23:00" in a["description"] for a in alerts)
        # Night check already catches 23 not in 0-5, but delayed check should catch diff 7
        # If night not trigger (23 not 0-5), delayed diff should trigger description containing اختلاف
        self.assertTrue(found, f"expected delayed description in {alerts}")

    def test_pattern_B_rapid_deletion(self):
        # Create a transaction that is soft-deleted
        txn = Transaction(student_id=1, course_id=1, amount=50000, payment_method="cash", date="2026/01/01", description="test", type="tuition", is_deleted=True, is_reversed=False, share_teacher=0, share_institute=0)
        self.db.add(txn)
        self.db.commit()
        self.db.refresh(txn)
        # Snapshot counts before call to ensure read-only
        count_before = self.db.query(Transaction).filter(Transaction.is_deleted == True).count()
        r = self.client.get("/audit/suspicious_patterns", headers={"Authorization": "Bearer tok_admin"})
        self.assertEqual(r.status_code, 200)
        alerts = [a for a in r.json() if a["type"] == "rapid_deletion"]
        self.assertTrue(len(alerts) >= 1, f"expected rapid_deletion but got {r.json()}")
        self.assertEqual(alerts[0]["severity"], "high")
        self.assertIn(str(txn.id), alerts[0]["description"])
        # Read-only verification: count unchanged
        count_after = self.db.query(Transaction).filter(Transaction.is_deleted == True).count()
        self.assertEqual(count_before, count_after)

    def test_pattern_C_perfect_attendance(self):
        # Create course2 to isolate from other patterns? Use course id 1 with 10 sessions all present
        # First ensure student enrolled? Not required for Attendance check alone
        # Create 10 session logs for course 1
        session_ids = []
        for i in range(10):
            sl = SessionLog(course_id=1, date=f"2026/01/{10+i:02d}", time="16:00", start_time="16:00", final_teacher_cost=10000, final_institute_share=5000, cost_per_student=15000, attendee_count=1, status="Finished")
            self.db.add(sl)
            self.db.flush()
            session_ids.append(sl.id)
        self.db.commit()
        # For each session, add attendance Present for student 1 (no Absent)
        for sid in session_ids:
            att = Attendance(session_id=sid, student_id=1, status="Present", is_billed=False, excused=False)
            self.db.add(att)
        self.db.commit()
        r = self.client.get("/audit/suspicious_patterns", headers={"Authorization": "Bearer tok_admin"})
        self.assertEqual(r.status_code, 200)
        alerts = [a for a in r.json() if a["type"] == "perfect_attendance"]
        self.assertTrue(len(alerts) >= 1, f"expected perfect_attendance but got {r.json()}")
        self.assertEqual(alerts[0]["severity"], "medium")
        # Description should mention 10 جلسه and 0 غیبت (allow Persian digit ۰)
        self.assertIn("10", alerts[0]["description"])
        self.assertTrue("غیبت" in alerts[0]["description"], f"missing غیبت in {alerts[0]['description']}")
        # Check for either ASCII 0 or Persian ۰ before غیبت
        self.assertTrue("0 غیبت" in alerts[0]["description"] or "۰ غیبت" in alerts[0]["description"], f"expected 0/۰ غیبت in {alerts[0]['description']}")

    def test_read_only_wallet_not_modified(self):
        # Capture wallets before
        s_before = self.db.query(Student).filter(Student.id == 1).first()
        wt_before = s_before.wallet_teacher
        wi_before = s_before.wallet_institute
        wb_before = s_before.wallet_balance
        # Trigger all patterns (add data)
        sl = SessionLog(course_id=1, date="2026/01/05", time="03:00", final_teacher_cost=0, final_institute_share=0, cost_per_student=0, attendee_count=1, status="Finished")
        self.db.add(sl)
        txn = Transaction(student_id=1, course_id=1, amount=10000, payment_method="cash", date="2026/01/05", description="test2", type="tuition", is_deleted=True, is_reversed=False)
        self.db.add(txn)
        self.db.commit()
        r = self.client.get("/audit/suspicious_patterns", headers={"Authorization": "Bearer tok_admin"})
        self.assertEqual(r.status_code, 200)
        self.db.refresh(s_before)
        # Verify wallets unchanged
        s_after = self.db.query(Student).filter(Student.id == 1).first()
        self.assertEqual(wt_before, s_after.wallet_teacher)
        self.assertEqual(wi_before, s_after.wallet_institute)
        self.assertEqual(wb_before, s_after.wallet_balance)


if __name__ == "__main__":
    unittest.main()
