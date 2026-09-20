# test_teacher_null_data.py
# Regression tests for the «لیست مربیان / انتخاب معلم» crash:
# legacy rows with NULL mobile / national_code / total_paid / Course.title must not
# 500 the teacher search, teacher full profile, or pending settlement endpoints,
# and one bad row must not break the rest of the list.
import datetime
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Branch, Course, Enrollment, Student, Teacher, User, UserSession,
    SessionLog, Attendance,
)
from routers.admin import search_admin_teachers, search_admin_students
from routers.teachers import get_teacher_full_profile, get_pending_settlement


class TestTeacherNullData(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.db.add(Branch(id=1, name="مرکزی", active=True))

        self.admin = User(username="admin", password="x", full_name="مدیر", role="admin", sub_role="admin", branch_id=1)
        self.db.add(self.admin)
        self.db.flush()
        self.db.add(UserSession(token="admin-token", user_id=self.admin.id, sub_role="admin", created_at=datetime.datetime.now()))

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    # ------------------------------------------------------------------
    # 1. Teacher search (PersonListActivity / انتخاب معلم)
    # ------------------------------------------------------------------
    def test_search_teachers_null_mobile(self):
        good = Teacher(first_name="مریم", last_name="تست", mobile="09120000001", national_code="0012345678", is_approved=True)
        bad = Teacher(first_name="رضا", last_name="بدون‌موبایل", mobile=None, national_code="0012345679", is_approved=True)
        self.db.add_all([good, bad])
        self.db.commit()

        rows = search_admin_teachers(query=None, db=self.db, sub_role="admin")
        # یک رکورد ناقص نباید کل لیست را خراب کند — هر دو معلم باید موجود باشند.
        self.assertEqual(len(rows), 2)
        by_id = {r.id: r for r in rows}
        self.assertEqual(by_id[bad.id].mobile, "")
        self.assertEqual(by_id[bad.id].national_code, "0012345679")
        self.assertEqual(by_id[good.id].mobile, "09120000001")

    def test_search_teachers_null_national_code(self):
        bad = Teacher(first_name="رضا", last_name="بدون‌کدملی", mobile="09120000002", national_code=None, is_approved=True)
        self.db.add(bad)
        self.db.commit()

        rows = search_admin_teachers(query=None, db=self.db, sub_role="admin")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].national_code, "")
        self.assertEqual(rows[0].mobile, "09120000002")

    def test_search_teachers_all_null_pii(self):
        # بدترین حالت: همه‌ی فیلدهای legacy NULL — حتی «None» نباید در نام بیاید.
        bad = Teacher(first_name=None, last_name=None, mobile=None, national_code=None, is_approved=True)
        self.db.add(bad)
        self.db.commit()

        rows = search_admin_teachers(query=None, db=self.db, sub_role="admin")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].name, "نامشخص")
        self.assertEqual(rows[0].mobile, "")
        self.assertEqual(rows[0].national_code, "")
        self.assertNotIn("None", rows[0].name)

    def test_search_students_null_mobile(self):
        # همان مدل/صفحه — یک شاگرد ناقص هم نباید کل لیست را 500 کند.
        bad = Student(first_name="علی", last_name="تست", national_code="0012345680", student_mobile=None,
                      wallet_teacher=0, wallet_institute=0, wallet_balance=0)
        self.db.add(bad)
        self.db.commit()

        rows = search_admin_students(query=None, db=self.db, sub_role="admin")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].mobile, "")
        self.assertEqual(rows[0].national_code, "0012345680")

    # ------------------------------------------------------------------
    # 2. Teacher full profile
    # ------------------------------------------------------------------
    def test_full_profile_null_mobile_and_national_code(self):
        teacher = Teacher(first_name="مریم", last_name="تست", mobile=None, national_code=None, is_approved=True)
        self.db.add(teacher)
        self.db.commit()

        profile = get_teacher_full_profile(id=teacher.id, db=self.db, authorization="Bearer admin-token", sub_role="admin")
        self.assertEqual(profile.info.mobile, "")
        self.assertEqual(profile.info.national_code, "")
        self.assertEqual(profile.info.name, "مریم تست")

    def test_full_profile_null_total_paid(self):
        teacher = Teacher(first_name="مریم", last_name="تست", mobile="09120000001", national_code="0012345678", is_approved=True)
        student = Student(first_name="علی", last_name="تست", national_code="0012345681", student_mobile="09121111111",
                          wallet_teacher=0, wallet_institute=0, wallet_balance=0)
        self.db.add_all([teacher, student])
        self.db.flush()
        course = Course(title="ریاضی", code="200001", teacher_id=teacher.id, is_admin_approved=True,
                        is_deleted=False, grade_level="دهم", class_time="16:00-17:30",
                        days_of_week="شنبه", teacher_session_price=100000)
        self.db.add(course)
        self.db.flush()
        # total_paid=NULL legacy (explicit None forces NULL over the column default).
        enrollment = Enrollment(student_id=student.id, course_id=course.id, register_date="1405/06/01",
                                shift="عصر", total_tuition=1000000, total_paid=None)
        self.db.add(enrollment)
        self.db.commit()

        profile = get_teacher_full_profile(id=teacher.id, db=self.db, authorization="Bearer admin-token", sub_role="admin")
        # NULL باید مثل صفر حساب شود — نه TypeError/500.
        self.assertEqual(profile.total_revenue, 0)
        self.assertEqual(profile.total_students, 1)

    def test_full_profile_null_course_title(self):
        teacher = Teacher(first_name="مریم", last_name="تست", mobile="09120000001", national_code="0012345678", is_approved=True)
        self.db.add(teacher)
        self.db.flush()
        # کلاس legacy با title=NULL.
        course = Course(title=None, code=None, teacher_id=teacher.id, is_admin_approved=True,
                        is_deleted=False, grade_level=None, class_time="16:00-17:30",
                        days_of_week="شنبه", teacher_session_price=100000)
        self.db.add(course)
        self.db.commit()

        profile = get_teacher_full_profile(id=teacher.id, db=self.db, authorization="Bearer admin-token", sub_role="admin")
        self.assertEqual(len(profile.classes), 1)
        self.assertNotIn("None", profile.classes[0])
        self.assertTrue(profile.classes[0].startswith("کلاس بدون عنوان"))

    def test_full_profile_mixed_good_and_bad_rows(self):
        teacher = Teacher(first_name="مریم", last_name="تست", mobile="09120000001", national_code="0012345678", is_approved=True)
        self.db.add(teacher)
        self.db.flush()
        course_good = Course(title="ریاضی", code="200001", teacher_id=teacher.id, is_admin_approved=True,
                             is_deleted=False, grade_level="دهم", class_time="16:00-17:30",
                             days_of_week="شنبه", teacher_session_price=100000)
        course_bad = Course(title=None, code="200002", teacher_id=teacher.id, is_admin_approved=True,
                            is_deleted=False, grade_level=None, class_time="16:00-17:30",
                            days_of_week="یکشنبه", teacher_session_price=100000)
        self.db.add_all([course_good, course_bad])
        self.db.flush()
        s1 = Student(first_name="علی", last_name="اول", national_code="0012345681", student_mobile="09121111111",
                     wallet_teacher=0, wallet_institute=0, wallet_balance=0)
        s2 = Student(first_name="باقر", last_name="دوم", national_code="0012345682", student_mobile="09121111112",
                     wallet_teacher=0, wallet_institute=0, wallet_balance=0)
        self.db.add_all([s1, s2])
        self.db.flush()
        e_good = Enrollment(student_id=s1.id, course_id=course_good.id, register_date="1405/06/01", shift="عصر",
                            total_tuition=1000000, total_paid=500000)
        e_bad = Enrollment(student_id=s2.id, course_id=course_bad.id, register_date="1405/06/01", shift="عصر",
                           total_tuition=1000000, total_paid=None)
        self.db.add_all([e_good, e_bad])
        self.db.commit()

        profile = get_teacher_full_profile(id=teacher.id, db=self.db, authorization="Bearer admin-token", sub_role="admin")
        # رکورد خوب سالم می‌ماند و رکورد بد هم خرابش نمی‌کند.
        self.assertEqual(profile.total_revenue, 500000)
        self.assertEqual(profile.total_students, 2)
        self.assertEqual(profile.active_classes_count, 2)
        self.assertTrue(any("ریاضی (200001)" in c for c in profile.classes))
        self.assertTrue(any(c.startswith("کلاس بدون عنوان") for c in profile.classes))
        for c in profile.classes:
            self.assertNotIn("None", c)

    # ------------------------------------------------------------------
    # 3. Pending settlement
    # ------------------------------------------------------------------
    def _make_session_with_attendance(self, teacher, course, student, date="1405/06/02"):
        session_log = SessionLog(course_id=course.id, date=date, time="16:00", final_teacher_cost=100000,
                                 final_institute_share=50000, cost_per_student=150000, attendee_count=1,
                                 status="Finished")
        self.db.add(session_log)
        self.db.flush()
        attendance = Attendance(session_id=session_log.id, student_id=student.id, status="Present",
                                is_billed=False, excused=False)
        self.db.add(attendance)
        self.db.flush()
        return session_log

    def test_pending_settlement_null_class_title(self):
        teacher = Teacher(first_name="مریم", last_name="تست", mobile="09120000001", national_code="0012345678", is_approved=True)
        student = Student(first_name="علی", last_name="تست", national_code="0012345683", student_mobile="09121111111",
                          wallet_teacher=0, wallet_institute=0, wallet_balance=0)
        self.db.add_all([teacher, student])
        self.db.flush()
        # کلاس legacy با title=NULL.
        course = Course(title=None, code="200001", teacher_id=teacher.id, is_admin_approved=True,
                        is_deleted=False, grade_level="دهم", class_time="16:00-17:30",
                        days_of_week="شنبه", teacher_session_price=100000)
        self.db.add(course)
        self.db.flush()
        self._make_session_with_attendance(teacher, course, student)
        self.db.commit()

        pending = get_pending_settlement(teacher_id=teacher.id, db=self.db, authorization="Bearer admin-token", sub_role="admin")
        self.assertEqual(pending["session_count"], 1)
        row = pending["pending_sessions"][0]
        # null نباید در پاسخ باشد — فال‌بک مناسب به‌جای آن.
        self.assertEqual(row["class_title"], "کلاس بدون عنوان")
        self.assertNotIn(None, row.values())
        self.assertEqual(pending["total_amount"], 100000)

    def test_pending_settlement_mixed_good_and_bad_rows(self):
        teacher = Teacher(first_name="مریم", last_name="تست", mobile="09120000001", national_code="0012345678", is_approved=True)
        self.db.add(teacher)
        self.db.flush()
        course_good = Course(title="ریاضی", code="200001", teacher_id=teacher.id, is_admin_approved=True,
                             is_deleted=False, grade_level="دهم", class_time="16:00-17:30",
                             days_of_week="شنبه", teacher_session_price=100000)
        course_bad = Course(title=None, code="200002", teacher_id=teacher.id, is_admin_approved=True,
                            is_deleted=False, grade_level=None, class_time="16:00-17:30",
                            days_of_week="یکشنبه", teacher_session_price=100000)
        self.db.add_all([course_good, course_bad])
        self.db.flush()
        s1 = Student(first_name="علی", last_name="اول", national_code="0012345684", student_mobile="09121111111",
                     wallet_teacher=0, wallet_institute=0, wallet_balance=0)
        s2 = Student(first_name="باقر", last_name="دوم", national_code="0012345685", student_mobile="09121111112",
                     wallet_teacher=0, wallet_institute=0, wallet_balance=0)
        self.db.add_all([s1, s2])
        self.db.flush()
        self._make_session_with_attendance(teacher, course_good, s1, date="1405/06/02")
        self._make_session_with_attendance(teacher, course_bad, s2, date="1405/06/03")
        self.db.commit()

        pending = get_pending_settlement(teacher_id=teacher.id, db=self.db, authorization="Bearer admin-token", sub_role="admin")
        # هر دو جلسه موجودند — رکورد ناقص جلسه‌ی سالم را نمی‌بیند.
        self.assertEqual(pending["session_count"], 2)
        titles = [r["class_title"] for r in pending["pending_sessions"]]
        self.assertIn("ریاضی", titles)
        self.assertIn("کلاس بدون عنوان", titles)
        self.assertNotIn(None, titles)
        self.assertEqual(pending["total_amount"], 200000)

    def test_pending_settlement_null_teacher_name(self):
        # نام‌های NULL نباید «None None» در teacher_name بیاورند.
        teacher = Teacher(first_name=None, last_name=None, mobile="09120000003", national_code="0012345686", is_approved=True)
        self.db.add(teacher)
        self.db.commit()

        pending = get_pending_settlement(teacher_id=teacher.id, db=self.db, authorization="Bearer admin-token", sub_role="admin")
        self.assertEqual(pending["teacher_name"], "نامشخص")
        self.assertEqual(pending["session_count"], 0)


if __name__ == "__main__":
    unittest.main()
