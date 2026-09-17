"""
ثبت جلسه / حضور و غیاب / هزینه‌ی جلسه / جریمه‌ی غیبت / حذف جلسه / برگشت اثر مالی — TEST-ONLY audit
(فقط تست؛ هیچ تغییری در کد اصلی پروژه انجام نشده است)

## Business rules تحت آزمون
- `wallet_teacher` مثبت = اعتبار نزد معلم | منفی = بدهی دانش‌آموز به معلم
- `wallet_institute` مثبت = اعتبار نزد آموزشگاه | منفی = بدهی دانش‌آموز به آموزشگاه
- صفر = تسویه
- **invariant همیشگی:** `wallet_balance == wallet_teacher + wallet_institute`

## نگاشت ۲۷ سناریوی درخواستی ← تست‌ها
| # | سناریو | تست‌ها |
|---|--------|--------|
| ۱ | ثبت جلسه برای عضو فعال کلاس | `test_s01_*` |
| ۲ | عضو نبودن ⇒ رد + بی‌اثری کامل | `test_s02_*` |
| ۳ | دانش‌آموز suspended ⇒ رد | `test_s03_*` |
| ۴ | duplicate همان course/date ⇒ 409 + بی‌اثری | `test_s04_*` |
| ۵ | همان کلاس، تاریخ دیگر ⇒ مجاز | `test_s05_*` |
| ۶ | دانش‌آموز تکراری در یک ثبت ⇒ سیاست = رد (نه update) | `test_s06_*` |
| ۷ | دانش‌آموز کلاس دیگر ⇒ رد | `test_s07_*` |
| ۸ | دانش‌آموز حذف‌شده / enrollment حذف‌شده | `test_s08a_*` (enrollment) + `test_s08b_finding_*` |
| ۹ | تاریخ جلالی معتبر/نامعتبر + duplicate پنهان | `test_s09a_*`, `test_s09b_*`, `test_s09c_*` |
| ۱۰ | Present ⇒ هزینه‌ی جلسه و سهم‌ها | `test_s10_*` |
| ۱۱ | Late ⇒ policy پروژه | `test_s11_*` |
| ۱۲ | غیبت موجه ⇒ بدون جریمه | `test_s12_*` |
| ۱۳ | غیبت غیرموجه ⇒ جریمه طبق rule کلاس | `test_s13_*` |
| ۱۴ | جلسه‌ی تماماً غایب | `test_s14_*` |
| ۱۵ | `rule_calc_absent=False` | `test_s15_*` |
| ۱۶ | `rule_prepay_teacher=True` | `test_s16_*` |
| ۱۷ | `rule_prepay_institute=True` | `test_s17_*` |
| ۱۸ | مبلغ فرد (۱۰۱) و باقیمانده | `test_s18_*` |
| ۱۹ | حذف نرم جلسه + برگشت اثر مالی | `test_s19a_*`, `test_s19b_finding_*`, `test_s19c_*` |
| ۲۰ | اجرای دوباره‌ی reverse | `test_s20_*` |
| ۲۱ | ویرایش جلسه (مبلغ جدید فقط یک‌بار) | `test_s21a_*`, `test_s21b_*` |
| ۲۲ | تغییر وضعیت در ویرایش (۳ حالت) | `test_s22a_*`, `test_s22b_*`, `test_s22c_*` |
| ۲۳ | جلسه‌ی حذف‌شده (settlement/گزارش/reverse) | `test_s23a_*`, `test_s23b_*`, `test_s23c_*` |
| ۲۴ | settlement معلم | `test_s24a_*` .. `test_s24e_*` |
| ۲۵ | rollback وسط ثبت/محاسبه | `test_s25a_*`, `test_s25b_*` |
| ۲۶ | invariant بعد از هر سناریوی مالی | `assert_invariant` در همه‌ی helperها + `test_s26_*` |
| ۲۷ | race condition (دو Session مستقل) | `test_s27a_*`, `test_s27b_*` (SQLite-only) |

## 🔎 تست‌های یافته‌محور (عمداً fail می‌شوند — طبق دستور تسک هیچ fix‌ای انجام نشده)
| یافته | تست | خلاصه |
|---|---|---|
| F-S1 | `test_s08b_finding_*` | دانش‌آموز soft-deleted در شمارش/سهم‌ها «حاضر» حساب می‌شود ولی نه رکورد حضور دارد نه شارژ |
| F-S2 | `test_s19b_finding_*` | حذف/برگشت جلسه ردیف‌های حضور را **فیزیکی** پاک می‌کند (بقیه‌ی حذف‌های پروژه نرم‌اند) |
| F-S3 | `test_s_ext_items_finding_*` | `items=[]` پذیرفته می‌شود و همان تاریخ را اشغال می‌کند (ثبت واقعی بعدی ۴۰۹ می‌گیرد) |
| F-S4 | `test_s_ext_status_finding_*` | وضعیت ناشناخته/کوچک‌نویس (مثل `banana`/`present`) بی‌صدا بدون شارژ ثبت می‌شود |

## اجرا (طبق قانون پروژه: فقط روی DB تست/کپی — هرگز gaj_db.db واقعی)
    cd /home/user/KharazmiApp && DATABASE_URL=sqlite:////tmp/attendance_audit.db \\
        PYTHONPATH=/home/user/KharazmiApp/Kharazmi_Server \\
        python3 -m pytest Kharazmi_Server/test_attendance_sessions_audit.py -q
تست‌ها DB درون‌حافظه‌ای خودشان (StaticPool) و برای سناریوی race یک فایل SQLite در tmp_path می‌سازند.
"""
import datetime
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, func, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from dependencies import reverse_session_financial_impacts
from financial_calculations import (
    calculate_institute_session_revenue,
    calculate_teacher_session_revenue,
    calculate_total_turnover,
)
from routers import attendance, finance, teachers
from schemas import AttendanceItem, AttendanceSubmitData, HistoryRequest, SettleRequest

TOKEN = "att-admin-token"
TODAY_JALALI = "1405/06/16"          # تاریخ معتبر و گذشته‌نسبت به امروز
OTHER_JALALI = "1405/06/17"
GREGORIAN_EQUIVALENT = "2026/09/07"  # همان ۱۴۰۵/۰۶/۱۶ در تقویم میلادی
RANGE_START, RANGE_END = "1400/01/01", "1410/01/01"


# ==========================================
# زیرساخت
# ==========================================
def make_engine(url="sqlite:///:memory:", **kwargs):
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30}, **kwargs)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    models.Base.metadata.create_all(engine)
    return engine


def seed_world(db, teacher_price=60, institute_share=40, prepay_teacher=False,
               prepay_institute=False, calc_absent=True):
    """شعبه + ادمین + معلم + ۳ دانش‌آموز + دو کلاس.

    پیش‌فرض: کلاس ۱ با نرخ معلم ۶۰ و سهم آموزشگاه ۴۰ ⇒ شارژ هر حاضر دقیقاً ۱۰۰.
    دانش‌آموزان ۱۰۱ و ۱۰۲ عضو کلاس ۱؛ دانش‌آموز ۱۰۳ فقط عضو کلاس ۲ (برای سناریوی ۷).
    """
    db.add_all([models.Branch(id=1, name="شعبه تست", active=True)])
    db.flush()
    user = models.User(id=1, username="att-admin", password="unused", role="admin",
                       sub_role="admin", branch_id=1)
    teacher = models.Teacher(id=1, teacher_code=101, first_name="معلم", last_name="تست",
                             mobile="09120000101", branch_id=1)
    db.add_all([user, teacher])
    for sid in (101, 102, 103):
        db.add(models.Student(
            id=sid, student_code=100000 + sid, first_name=f"دانش‌آموز{sid}", last_name="تست",
            national_code=f"AT-{sid}", student_mobile=f"091211101{sid}", parent_mobile=f"091222201{sid}",
            branch_id=1, wallet_teacher=0, wallet_institute=0, wallet_balance=0,
        ))
    db.flush()
    course = models.Course(
        id=1, title="کلاس یک", code="AT10001", teacher_id=teacher.id, branch_id=1,
        grade_level="دهم", teacher_session_price=teacher_price, is_admin_approved=True,
        rule_prepay_teacher=prepay_teacher, rule_prepay_institute=prepay_institute,
        rule_calc_absent=calc_absent,
    )
    course2 = models.Course(
        id=2, title="کلاس دو", code="AT10002", teacher_id=teacher.id, branch_id=1,
        grade_level="دهم", teacher_session_price=teacher_price, is_admin_approved=True,
    )
    db.add_all([course, course2])
    db.flush()
    e1 = models.Enrollment(student_id=101, course_id=1, branch_id=1, total_tuition=1000,
                           total_paid=0, register_date=TODAY_JALALI)
    e2 = models.Enrollment(student_id=102, course_id=1, branch_id=1, total_tuition=1000,
                           total_paid=0, register_date=TODAY_JALALI)
    e3 = models.Enrollment(student_id=103, course_id=2, branch_id=1, total_tuition=1000,
                           total_paid=0, register_date=TODAY_JALALI)
    db.add_all([
        e1, e2, e3,
        models.UserSession(token=TOKEN, user_id=user.id, sub_role="admin",
                           created_at=datetime.datetime.now()),
        models.InstituteShare(count_1=institute_share, count_2=institute_share * 2,
                              count_3=institute_share * 3),
    ])
    db.commit()
    return SimpleNamespace(db=db, user=user, teacher=teacher, course=course, course2=course2,
                           enroll1=e1, enroll2=e2, enroll3=e3)


@pytest.fixture
def world():
    """DB درون‌حافظه‌ای اختصاصی هر تست — هیچ فایلی از پروژه خوانده/نوشته نمی‌شود."""
    engine = make_engine(poolclass=StaticPool)
    with sessionmaker(bind=engine, expire_on_commit=False)() as db:
        yield seed_world(db)
    models.Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def file_world(tmp_path):
    """DB فایلی SQLite برای سناریوهای هم‌زمانی (سناریو ۲۷) — SQLite-only، حذف در پایان."""
    db_path = tmp_path / "attendance_race.db"
    engine = make_engine(f"sqlite:///{db_path}")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        seed_world(db)
    yield SimpleNamespace(factory=factory, db_path=str(db_path), engine=engine)
    engine.dispose()


# ---------- helpers ----------
def wallets(db, student_id=101):
    db.expire_all()
    student = db.get(models.Student, student_id)
    return (student.wallet_teacher or 0, student.wallet_institute or 0, student.wallet_balance or 0)


def assert_invariant(db, student_id=101, context="", expected=None):
    """سناریو ۲۶: wallet_balance == wallet_teacher + wallet_institute — بعد از هر عملیات مالی."""
    teacher, institute, balance = wallets(db, student_id)
    assert balance == teacher + institute, (
        f"نقض invariant {context}: balance={balance} != teacher({teacher}) + institute({institute})"
    )
    if expected is not None:
        assert (teacher, institute, balance) == expected, (
            f"{context}: کیف {student_id} = {(teacher, institute, balance)} ≠ {expected}"
        )
    return teacher, institute, balance


def items(*pairs):
    """items((101, "Present"), (102, "Absent", True)) — پشتیبانی از excused اختیاری."""
    built = []
    for pair in pairs:
        student_id, status = pair[0], pair[1]
        excused = pair[2] if len(pair) > 2 else False
        built.append(AttendanceItem(student_id=student_id, status=status, excused=excused))
    return built


def submit(world, session_items, date=TODAY_JALALI, course_id=1):
    request = AttendanceSubmitData(course_id=course_id, date=date, items=session_items)
    result = attendance.submit_session_and_calculate(
        request, db=world.db, authorization=f"Bearer {TOKEN}", sub_role="admin")
    for sid in {getattr(i, "student_id", None) for i in session_items} or {101}:
        if world.db.get(models.Student, sid) is not None:
            assert_invariant(world.db, sid, context="بعد از ثبت جلسه")
    return result


def edit(world, session_code, session_items, date=TODAY_JALALI):
    request = AttendanceSubmitData(course_id=world.course.id, date=date, items=session_items)
    result = attendance.edit_past_session(session_code, request, db=world.db,
                                          authorization=f"Bearer {TOKEN}", sub_role="admin")
    for sid in {getattr(i, "student_id", None) for i in session_items} or {101}:
        if world.db.get(models.Student, sid) is not None:
            assert_invariant(world.db, sid, context="بعد از ویرایش جلسه")
    return result


def delete(world, session_code, admin="admin"):
    return attendance.delete_session_endpoint(session_code, db=world.db, _=admin)


def settle(world, session_ids):
    # در API هر درخواست Session تازه‌ی خودش را دارد (get_db)؛ اینجا همان رفتار را با expire شبیه‌سازی
    # می‌کنیم تا گیت‌های «قبلاً تسویه شده» روی state واقعیِ DB سنجیده شوند نه identity-map قدیمی.
    world.db.expire_all()
    return teachers.settle_teacher_sessions(
        teacher_id=world.teacher.id, req=SettleRequest(session_ids=list(session_ids)),
        db=world.db, admin_sub_role="admin", authorization=f"Bearer {TOKEN}")


def session_row(db, session_id):
    db.expire_all()
    return db.get(models.SessionLog, session_id)


def attendance_rows(db, session_id=None):
    db.expire_all()
    query = db.query(models.Attendance)
    if session_id is not None:
        query = query.filter(models.Attendance.session_id == session_id)
    return query.order_by(models.Attendance.student_id).all()


def charge_rows(db, session_id):
    db.expire_all()
    return (db.query(models.Transaction)
            .filter(models.Transaction.session_id == session_id,
                    models.Transaction.type == "session_charge")
            .order_by(models.Transaction.id).all())


def active_charge_rows(db, session_id):
    return [t for t in charge_rows(db, session_id) if not t.is_deleted]


def counter_value(db, name="session"):
    db.expire_all()
    row = db.query(models.SequenceCounter).filter(models.SequenceCounter.name == name).first()
    return row.current_value if row is not None else None


def financial_snapshot(db):
    """عکس فوری ردیف‌های مالی برای اثبات «هیچ نوشتنی رخ نداده»."""
    return (
        db.query(func.count(models.SessionLog.id)).scalar(),
        db.query(func.count(models.Attendance.id)).scalar(),
        db.query(func.count(models.Transaction.id)).scalar(),
        db.query(func.count(models.Notification.id)).scalar(),
        counter_value(db),
    )


def assert_no_writes(db, before, context=""):
    assert financial_snapshot(db) == before, f"{context}: نوشتن ناخواسته در DB رخ داده است"


def foreign_keys_ok(db):
    return db.execute(text("PRAGMA foreign_key_check")).all() == []


# ==========================================
# سناریو ۱ — ثبت جلسه برای عضو فعال کلاس
# ==========================================
def test_s01_session_for_active_member_is_recorded_and_charged(world):
    result = submit(world, items((101, "Present")))

    session = session_row(world.db, result["session_id"])
    assert session.is_deleted is False and session.date == TODAY_JALALI
    assert session.attendee_count == 1
    assert (session.final_teacher_cost, session.final_institute_share) == (60, 40)
    assert (session.absent_penalty_teacher, session.absent_penalty_institute) == (0, 0)
    assert session.session_code is not None

    rows = attendance_rows(world.db, session.id)
    assert [(r.student_id, r.status, r.is_billed) for r in rows] == [(101, "Present", False)]

    txns = active_charge_rows(world.db, session.id)
    assert len(txns) == 1
    assert (txns[0].share_teacher, txns[0].share_institute) == (60, 40)
    assert txns[0].amount == -100 and txns[0].payment_method == "System"
    assert txns[0].branch_id == 1          # FIX H7: شعبه‌ی شاگرد
    assert txns[0].course_id == world.course.id and txns[0].session_id == session.id

    assert_invariant(world.db, 101, "سناریو ۱", expected=(-60, -40, -100))
    assert result["details"]["cost_per_student"] == 100
    assert result["details"]["teacher_share"] == 60
    assert result["details"]["institute_share"] == 40
    assert result["details"]["total_session_cost"] == 100
    assert foreign_keys_ok(world.db)


# ==========================================
# سناریو ۲ — عضو نبودن کلاس
# ==========================================
def test_s02_non_member_is_rejected_without_any_write(world):
    before = financial_snapshot(world.db)
    with pytest.raises(HTTPException) as error:
        submit(world, items((103, "Present")))     # ۱۰۳ عضو کلاس ۱ نیست
    assert error.value.status_code == 422
    assert "103" in str(error.value.detail)        # پیام دقیق مشابه H6(B)

    assert_no_writes(world.db, before, "سناریو ۲")
    assert wallets(world.db, 103) == (0, 0, 0)
    assert wallets(world.db, 101) == (0, 0, 0)
    assert counter_value(world.db) in (None, 0) or counter_value(world.db) == before[-1]
    assert foreign_keys_ok(world.db)


# ==========================================
# سناریو ۳ — دانش‌آموز معلق (suspended)
# ==========================================
def test_s03_suspended_student_is_rejected_without_financial_effect(world):
    student = world.db.get(models.Student, 101)
    student.is_suspended = True
    world.db.commit()

    before = financial_snapshot(world.db)
    with pytest.raises(HTTPException) as error:
        submit(world, items((101, "Present")))
    assert error.value.status_code == 422
    assert "معلق" in str(error.value.detail)

    assert_no_writes(world.db, before, "سناریو ۳")
    assert wallets(world.db, 101) == (0, 0, 0)


# ==========================================
# سناریو ۴ — duplicate همان course/date
# ==========================================
def test_s04_duplicate_course_date_is_rejected_and_inert(world):
    first = submit(world, items((101, "Present")))
    counter_after_first = counter_value(world.db)
    before = financial_snapshot(world.db)

    with pytest.raises(HTTPException) as error:
        submit(world, items((102, "Present")))
    assert error.value.status_code == 409, "سیاست پروژه: duplicate ⇒ 409"
    assert "قبلاً ثبت شده" in str(error.value.detail)

    assert_no_writes(world.db, before, "سناریو ۴")
    assert counter_value(world.db) == counter_after_first, "SequenceCounter بی‌دلیل بالا رفت"
    assert world.db.query(models.SessionLog).count() == 1
    assert len(attendance_rows(world.db)) == 1, "Attendance دوم ساخته نشد"
    assert len(charge_rows(world.db, first["session_id"])) == 1, "Transaction دوم ساخته نشد"
    assert_invariant(world.db, 101, "سناریو ۴", expected=(-60, -40, -100))
    assert wallets(world.db, 102) == (0, 0, 0), "کیف دانش‌آموز دوم دست‌نخورده"
    assert counter_value(world.db) == 100001, "شمارنده فقط یک‌بار مصرف شده"


def test_s04b_duplicate_is_also_rejected_for_an_archived_after_delete_date(world):
    """پس از حذف جلسه، همان تاریخ دوباره قابل ثبت است و اسمی از جلسه‌ی قبلی نمی‌ماند."""
    first = submit(world, items((101, "Present")))
    delete(world, first["session_code"])
    second = submit(world, items((101, "Present")))
    assert second["session_id"] != first["session_id"]
    assert session_row(world.db, first["session_id"]).is_deleted is True
    assert len(active_charge_rows(world.db, second["session_id"])) == 1


# ==========================================
# سناریو ۵ — همان کلاس در تاریخ دیگر
# ==========================================
def test_s05_same_course_on_another_date_is_allowed(world):
    first = submit(world, items((101, "Present")), date=TODAY_JALALI)
    second = submit(world, items((101, "Present")), date=OTHER_JALALI)
    assert first["session_id"] != second["session_id"]
    assert world.db.query(models.SessionLog).count() == 2
    assert len(attendance_rows(world.db)) == 2
    assert len(charge_rows(world.db, first["session_id"])) == 1
    assert len(charge_rows(world.db, second["session_id"])) == 1
    assert_invariant(world.db, 101, "سناریو ۵", expected=(-120, -80, -200))


# ==========================================
# سناریو ۶ — دانش‌آموز تکراری در یک ثبت
# ==========================================
def test_s06_duplicate_student_in_one_request_is_rejected_not_updated(world):
    """سیاست پروژه برای تکرار (session, student) در **یک** درخواست = **رد** (۴۲۲) نه update.

    شاهد: H6(C1) در `submit_session_and_calculate` + قید یکتای `uq_attendance_session_student`
    در `models.py` — یعنی نه رکورد تکراری ساخته می‌شود نه رکورد قبلی به‌روزرسانی.
    """
    before = financial_snapshot(world.db)
    with pytest.raises(HTTPException) as error:
        submit(world, items((101, "Present"), (101, "Absent")))
    assert error.value.status_code == 422
    assert "بیش از یک‌بار" in str(error.value.detail)
    assert_no_writes(world.db, before, "سناریو ۶")


def test_s06b_second_request_for_same_session_is_a_409_not_an_update(world):
    """درخواست دوم برای همان (کلاس، تاریخ) — حتی با وضعیت متفاوت — آپدیت نمی‌کند و ۴۰۹ است."""
    first = submit(world, items((101, "Present")))
    with pytest.raises(HTTPException) as error:
        submit(world, items((101, "Absent")))
    assert error.value.status_code == 409
    rows = attendance_rows(world.db, first["session_id"])
    assert [(r.student_id, r.status) for r in rows] == [(101, "Present")], "وضعیت قبلی دست‌نخورده"
    assert len(active_charge_rows(world.db, first["session_id"])) == 1


# ==========================================
# سناریو ۷ — دانش‌آموز کلاس دیگر
# ==========================================
def test_s07_student_of_another_course_is_rejected(world):
    before = financial_snapshot(world.db)
    with pytest.raises(HTTPException) as error:
        submit(world, items((101, "Present"), (103, "Present")))
    assert error.value.status_code == 422
    assert "103" in str(error.value.detail)
    assert_no_writes(world.db, before, "سناریو ۷")
    # و همان دانش‌آموز در کلاس خودش مشکلی ندارد
    ok = submit(world, items((103, "Present")), course_id=2)
    assert session_row(world.db, ok["session_id"]).attendee_count == 1


# ==========================================
# سناریو ۸ — دانش‌آموز حذف‌شده / enrollment حذف‌شده
# ==========================================
def test_s08a_deleted_enrollment_is_rejected_without_writes(world):
    world.enroll1.is_deleted = True
    world.db.commit()
    before = financial_snapshot(world.db)
    with pytest.raises(HTTPException) as error:
        submit(world, items((101, "Present")))
    assert error.value.status_code == 422
    assert_no_writes(world.db, before, "سناریو ۸ (enrollment حذف‌شده)")
    assert wallets(world.db, 101) == (0, 0, 0)


def test_s08b_finding_deleted_student_counts_as_present_but_charges_nobody(world):
    """🔎 F-S1 (عمداً fail): دانش‌آموز **soft-deleted** عضو فعال کلاس، در شمارش حاضرین و سهم‌ها
    «حاضر» حساب می‌شود و SessionLog با `attendee_count=1` و `final_teacher_cost=60` نهایی می‌شود،
    ولی حلقه‌ی شارژ او را رد می‌کند (`st is None: continue`) ⇒ **نه رکورد حضور، نه تراکنش، نه کسر از کیف**.

    پیامد: جلسه‌ای که کسی در آن شارژ نشده، سهم معلم را بدهکار می‌کند و شمارش حاضرینش دروغ است
    (گزارش/تسویه‌ی معلم از همین اعداد استفاده می‌کنند). مسیر «معلق» ۴۲۲ می‌دهد (سناریو ۳) اما
    مسیر «حذف‌شده» بی‌صدا ادامه می‌دهد.
    """
    student = world.db.get(models.Student, 101)
    student.is_deleted = True
    world.db.commit()

    before = financial_snapshot(world.db)
    submit(world, items((101, "Present")))          # پذیرفته می‌شود

    session = world.db.query(models.SessionLog).one()
    written = financial_snapshot(world.db) != before
    assert not written, (
        "F-S1: جلسه با دانش‌آموز حذف‌شده نباید هیچ نوشتنی داشته باشد؛ "
        f"attendee_count={session.attendee_count} final_teacher_cost={session.final_teacher_cost} "
        f"attendance_rows={len(attendance_rows(world.db))} charge_rows={len(charge_rows(world.db, session.id))}"
    )


# ==========================================
# سناریو ۹ — تاریخ جلسه
# ==========================================
@pytest.mark.parametrize("bad_date", [
    "bad-date", "1405/13/01", "1405/00/01", "1405/01/00", "1405/01/32",
    "1405/12/30",      # سال غیرکبیسه
    "1405/07/31",      # ماه ۳۰روزه
    "", "   ",
])
def test_s09a_invalid_dates_are_rejected_without_partial_writes(world, bad_date):
    before = financial_snapshot(world.db)
    with pytest.raises(HTTPException) as error:
        submit(world, items((101, "Present")), date=bad_date)
    assert error.value.status_code == 422, "سیاست پروژه برای تاریخ نامعتبر ⇒ ۴۲۲"
    assert_no_writes(world.db, before, f"تاریخ نامعتبر {bad_date!r}")
    assert wallets(world.db, 101) == (0, 0, 0)


@pytest.mark.parametrize("good_date", ["1405/06/16", "1405/01/31", "1405/06/31", "1405/07/30", "1405/12/29"])
def test_s09b_valid_jalali_dates_are_accepted_and_canonical(world, good_date):
    result = submit(world, items((101, "Present")), date=good_date)
    assert session_row(world.db, result["session_id"]).date == good_date


def test_s09c_no_hidden_duplicate_from_a_different_date_format(world):
    """همان روز با فرمت میلادی ≠ جلسه‌ی دوم: تاریخ کانونیکال می‌شود و duplicate واقعی ⇒ ۴۰۹."""
    first = submit(world, items((101, "Present")), date=TODAY_JALALI)
    with pytest.raises(HTTPException) as error:
        submit(world, items((101, "Present")), date=GREGORIAN_EQUIVALENT)
    assert error.value.status_code == 409
    assert world.db.query(models.SessionLog).count() == 1
    assert len(charge_rows(world.db, first["session_id"])) == 1
    assert_invariant(world.db, 101, "سناریو ۹")


def test_s09d_reverse_order_gregorian_then_jalali_is_also_a_409(world):
    first = submit(world, items((101, "Present")), date=GREGORIAN_EQUIVALENT)
    assert session_row(world.db, first["session_id"]).date == TODAY_JALALI, "تاریخ ذخیره‌شده کانونیکال است"
    with pytest.raises(HTTPException) as error:
        submit(world, items((101, "Present")), date=TODAY_JALALI)
    assert error.value.status_code == 409


# ==========================================
# سناریو ۱۰ — Present
# ==========================================
def test_s10_present_charges_exact_tariff_and_splits_shares(world):
    submit(world, items((101, "Present"), (102, "Present")))

    session = world.db.query(models.SessionLog).one()
    # T_total = 60 × 2 = 120 | I_total = count_2 = 80 | سرانه = 60 + 40 = 100
    assert (session.final_teacher_cost, session.final_institute_share) == (120, 80)
    assert session.cost_per_student == 100

    txns = active_charge_rows(world.db, session.id)
    assert len(txns) == 2
    assert all(t.share_teacher == 60 and t.share_institute == 40 for t in txns)
    assert sum(t.share_teacher for t in txns) == session.final_teacher_cost
    assert sum(t.share_institute for t in txns) == session.final_institute_share
    assert all(t.amount == -(t.share_teacher + t.share_institute) for t in txns)
    assert_invariant(world.db, 101, "سناریو ۱۰", expected=(-60, -40, -100))
    assert_invariant(world.db, 102, "سناریو ۱۰", expected=(-60, -40, -100))


# ==========================================
# سناریو ۱۱ — Late
# ==========================================
def test_s11_late_is_charged_exactly_like_present(world):
    """policy فعلی پروژه: `Late` هم‌ارز `Present` است (در شمارش حاضرین و در شارژ) و جریمه‌ی تأخیر وجود ندارد."""
    submit(world, items((101, "Late"), (102, "Present")))
    session = world.db.query(models.SessionLog).one()
    assert session.attendee_count == 2 and session.cost_per_student == 100
    assert (session.final_teacher_cost, session.final_institute_share) == (120, 80)
    assert (session.absent_penalty_teacher, session.absent_penalty_institute) == (0, 0)
    rows = {r.student_id: r.status for r in attendance_rows(world.db, session.id)}
    assert rows == {101: "Late", 102: "Present"}
    assert_invariant(world.db, 101, "سناریو ۱۱", expected=(-60, -40, -100))
    assert_invariant(world.db, 102, "سناریو ۱۱", expected=(-60, -40, -100))


# ==========================================
# سناریو ۱۲ — غیبت موجه
# ==========================================
def test_s12_excused_absence_has_no_penalty_and_no_mis_share(world):
    submit(world, items((101, "Present"), (102, "Absent", True)))

    session = world.db.query(models.SessionLog).one()
    assert session.attendee_count == 1
    assert (session.final_teacher_cost, session.final_institute_share) == (60, 40)
    assert (session.absent_penalty_teacher, session.absent_penalty_institute) == (0, 0), "جریمه‌ای نباید باشد"

    rows = {r.student_id: (r.status, r.excused) for r in attendance_rows(world.db, session.id)}
    assert rows == {101: ("Present", False), 102: ("Absent", True)}

    txns = active_charge_rows(world.db, session.id)
    assert [t.student_id for t in txns] == [101], "غایب موجه نباید شارژ شود"
    assert_invariant(world.db, 102, "سناریو ۱۲", expected=(0, 0, 0))
    assert_invariant(world.db, 101, "سناریو ۱۲", expected=(-60, -40, -100))

    # اطلاع‌رسانی غیبت ثبت شده ولی هیچ اثر مالی ندارد
    notifications = world.db.query(models.Notification).filter(models.Notification.type == "attendance").all()
    assert len(notifications) == 1 and "موجه" in notifications[0].body
    assert foreign_keys_ok(world.db)


# ==========================================
# سناریو ۱۳ — غیبت غیرموجه
# ==========================================
def test_s13_unexcused_absence_applies_course_rule_penalty(world):
    submit(world, items((101, "Present"), (102, "Absent")))

    session = world.db.query(models.SessionLog).one()
    assert (session.final_teacher_cost, session.final_institute_share) == (60, 40), "مبالغ قراردادی فقط برای حاضر"
    assert (session.absent_penalty_teacher, session.absent_penalty_institute) == (60, 40), "جریمه جدا از قرارداد"
    assert session.cost_per_student == 100

    by_student = {t.student_id: t for t in active_charge_rows(world.db, session.id)}
    assert set(by_student) == {101, 102}
    assert (by_student[102].share_teacher, by_student[102].share_institute) == (60, 40)
    assert by_student[102].amount == -100 and "غایب غیرموجه" in by_student[102].description
    assert (by_student[101].share_teacher, by_student[101].share_institute) == (60, 40)

    assert_invariant(world.db, 102, "سناریو ۱۳ (غایب غیرموجه)", expected=(-60, -40, -100))
    assert_invariant(world.db, 101, "سناریو ۱۳", expected=(-60, -40, -100))
    notification = world.db.query(models.Notification).filter(models.Notification.type == "attendance").one()
    assert "غیرموجه" in notification.body


# ==========================================
# سناریو ۱۴ — جلسه‌ی تماماً غایب
# ==========================================
def test_s14_all_absent_session_charges_penalty_only(world):
    result = submit(world, items((101, "Absent"), (102, "Absent")))

    session = session_row(world.db, result["session_id"])
    assert session.attendee_count == 0
    assert (session.final_teacher_cost, session.final_institute_share) == (0, 0), \
        "جلسه‌ی بدون حاضر نباید هزینه‌ی جلسه‌ی حاضرین را بگیرد"
    # جریمه = U × base ؛ base معلم = نرخ کلاس (۶۰)، base آموزشگاه = count_2/2 = ۴۰
    assert (session.absent_penalty_teacher, session.absent_penalty_institute) == (120, 80)
    assert session.cost_per_student == 100, "مبنای جریمه‌ی سرانه"

    txns = active_charge_rows(world.db, session.id)
    assert [(t.student_id, t.share_teacher, t.share_institute) for t in txns] == \
        [(101, 60, 40), (102, 60, 40)]
    assert sum(t.amount for t in txns) == -(session.absent_penalty_teacher + session.absent_penalty_institute)
    assert result["details"]["total_session_cost"] == 200
    assert_invariant(world.db, 101, "سناریو ۱۴", expected=(-60, -40, -100))
    assert_invariant(world.db, 102, "سناریو ۱۴", expected=(-60, -40, -100))


def test_s14b_all_absent_with_one_excused_only_penalizes_the_unexcused(world):
    submit(world, items((101, "Absent"), (102, "Absent", True)))
    session = world.db.query(models.SessionLog).one()
    assert (session.absent_penalty_teacher, session.absent_penalty_institute) == (60, 40)
    assert [t.student_id for t in active_charge_rows(world.db, session.id)] == [101]
    assert_invariant(world.db, 102, "سناریو ۱۴ (موجه)", expected=(0, 0, 0))


# ==========================================
# سناریو ۱۵ — rule_calc_absent=False
# ==========================================
def test_s15_course_with_absent_rule_off_charges_no_penalty(world):
    world.course.rule_calc_absent = False
    world.db.commit()
    submit(world, items((101, "Present"), (102, "Absent")))

    session = world.db.query(models.SessionLog).one()
    assert (session.absent_penalty_teacher, session.absent_penalty_institute) == (0, 0)
    assert (session.final_teacher_cost, session.final_institute_share) == (60, 40)
    assert [t.student_id for t in active_charge_rows(world.db, session.id)] == [101]
    assert_invariant(world.db, 102, "سناریو ۱۵", expected=(0, 0, 0))


# ==========================================
# سناریو ۱۶ و ۱۷ — پیش‌پرداخت معلم / آموزشگاه
# ==========================================
def test_s16_prepay_teacher_charges_no_teacher_share(world):
    world.course.rule_prepay_teacher = True
    world.db.commit()
    submit(world, items((101, "Present")))

    session = world.db.query(models.SessionLog).one()
    assert session.final_teacher_cost == 0, "policy پیش‌پرداخت معلم: سهم معلم از دانش‌آموز گرفته نمی‌شود"
    txn = active_charge_rows(world.db, session.id)[0]
    assert (txn.share_teacher, txn.share_institute) == (0, 40)
    assert txn.amount == -40
    assert_invariant(world.db, 101, "سناریو ۱۶", expected=(0, -40, -40))
    assert session.cost_per_student == 40


def test_s17_prepay_institute_charges_no_institute_share(world):
    world.course.rule_prepay_institute = True
    world.db.commit()
    submit(world, items((101, "Present")))

    session = world.db.query(models.SessionLog).one()
    assert session.final_institute_share == 0
    txn = active_charge_rows(world.db, session.id)[0]
    assert (txn.share_teacher, txn.share_institute) == (60, 0)
    assert txn.amount == -60
    assert_invariant(world.db, 101, "سناریو ۱۷", expected=(-60, 0, -60))
    assert session.cost_per_student == 60


# ==========================================
# سناریو ۱۸ — تقسیم مبلغ فرد (۱۰۱) و باقیمانده
# ==========================================
def test_s18_odd_amount_is_split_without_fractions_and_remainder_survives(world):
    """۳ حاضر، T_total = ۱۰۱ (تعرفه‌ی مقطع) و I_total = ۱۰۰ ⇒ پایه ۳۳ با باقیمانده‌ی توزیع‌شده."""
    world.course.teacher_session_price = 0        # اجبار به fallback تعرفه‌ی مقطعی
    institute = world.db.query(models.InstituteShare).first()
    institute.count_3 = 100
    world.db.add_all([
        models.PricingTable(category="high_school", count_1=60, count_2=80, count_3=101),
        models.Enrollment(student_id=103, course_id=1, branch_id=1, total_tuition=1000,
                          total_paid=0, register_date=TODAY_JALALI),
    ])
    world.db.commit()

    submit(world, items((101, "Present"), (102, "Present"), (103, "Present")))
    session = world.db.query(models.SessionLog).one()
    txns = active_charge_rows(world.db, session.id)
    assert len(txns) == 3

    teacher_shares = [t.share_teacher for t in txns]
    institute_shares = [t.share_institute for t in txns]
    assert all(isinstance(x, int) for x in teacher_shares + institute_shares), "سهم اعشاری ممنوع"
    assert sorted(teacher_shares) == [33, 34, 34] and sum(teacher_shares) == 101, "باقیمانده گم نشد"
    assert sorted(institute_shares) == [33, 33, 34] and sum(institute_shares) == 100
    assert session.final_teacher_cost == 101 and session.final_institute_share == 100
    assert all(t.amount == -(t.share_teacher + t.share_institute) for t in txns)
    assert sum(-t.amount for t in txns) == 201

    # نوع ذخیره‌شده در SQLite هم باید integer باشد (نه real)
    types = world.db.execute(text(
        "SELECT DISTINCT typeof(amount) || '/' || typeof(share_teacher) || '/' || typeof(share_institute) "
        "FROM transactions WHERE session_id = :s"), {"s": session.id}).all()
    assert types == [("integer/integer/integer",)], f"نوع اعشاری در DB: {types}"

    for sid in (101, 102, 103):
        teacher, institute_, balance = wallets(world.db, sid)
        assert balance == teacher + institute_, f"invariant شاگرد {sid}" 

    assert_invariant(world.db, 101, "سناریو ۱۸")
    assert_invariant(world.db, 102, "سناریو ۱۸")
    assert_invariant(world.db, 103, "سناریو ۱۸")


# ==========================================
# سناریو ۱۹ — حذف نرم جلسه
# ==========================================
def test_s19a_soft_delete_reverts_active_financial_effect_once(world):
    first = submit(world, items((101, "Present"), (102, "Present")))
    session_id = first["session_id"]
    assert wallets(world.db, 101) == (-60, -40, -100)

    delete(world, first["session_code"])

    session = session_row(world.db, session_id)
    assert session is not None and session.is_deleted is True, "حذف باید نرم باشد (سند تاریخی می‌ماند)"
    # تراکنش‌ها آرشیو می‌شوند ولی سطر و لینک‌ها می‌مانند
    rows = charge_rows(world.db, session_id)
    assert len(rows) == 2 and all(t.is_deleted for t in rows)
    assert all(t.session_id == session_id and t.course_id == world.course.id for t in rows)
    assert active_charge_rows(world.db, session_id) == []
    # کیف فقط یک بار restore می‌شود
    assert_invariant(world.db, 101, "سناریو ۱۹", expected=(0, 0, 0))
    assert_invariant(world.db, 102, "سناریو ۱۹", expected=(0, 0, 0))
    assert foreign_keys_ok(world.db)
    # گزارش‌های درآمد دیگر چیزی نشان نمی‌دهند
    assert calculate_teacher_session_revenue(world.db, 1, RANGE_START, RANGE_END) == 0
    assert calculate_institute_session_revenue(world.db, RANGE_START, RANGE_END) == 0
    assert calculate_total_turnover(world.db, RANGE_START, RANGE_END) == 0
    # حذف تکراری ⇒ ۴۰۴ و بی‌اثر
    with pytest.raises(HTTPException) as error:
        delete(world, first["session_code"])
    assert error.value.status_code == 404
    assert_invariant(world.db, 101, "سناریو ۱۹ (حذف تکراری)", expected=(0, 0, 0))


def test_s19b_finding_delete_destroys_attendance_history(world):
    """🔎 F-S2 (عمداً fail): `reverse_session_financial_impacts` ردیف‌های حضور را **فیزیکی** پاک می‌کند
    (`db.query(Attendance)...delete()` در dependencies.py)، پس با حذف جلسه سابقه‌ی حضور/غیاب
    برای همیشه از بین می‌رود — در حالی که همه‌ی حذف‌های دیگر پروژه (Enrollment/Installment/Transaction/
    SessionLog) نرم‌اند و برای همین دلیل نگه داشته شده‌اند.

    انتظار: پس از حذف جلسه، سابقه‌ی حضور هم مثل بقیه آرشیو بماند (یا حداقل نشانی از حذف داشته باشد).
    """
    first = submit(world, items((101, "Present"), (102, "Absent")))
    assert len(attendance_rows(world.db, first["session_id"])) == 2, "قبل از حذف دو ردیف حضور داریم"

    delete(world, first["session_code"])

    remaining = attendance_rows(world.db, first["session_id"])
    assert len(remaining) == 2, (
        "F-S2: با حذف جلسه، سابقه‌ی حضور فیزیکی پاک شد "
        f"(ردیف‌های باقی‌مانده: {len(remaining)}) و هیچ فلگ آرشیوی هم وجود ندارد"
    )


def test_s19c_delete_keeps_financial_documents_and_links_intact(world):
    first = submit(world, items((101, "Present")))
    session_id = first["session_id"]
    delete(world, first["session_code"])
    assert foreign_keys_ok(world.db), "FKهای Transaction/SessionLog نباید بشکنند"
    txn = charge_rows(world.db, session_id)[0]
    assert (txn.session_id, txn.course_id, txn.student_id, txn.branch_id) == \
        (session_id, world.course.id, 101, 1)
    assert txn.is_reversed is False, "برگشت مالی از مسیر reverse است، نه refund عمومی"


# ==========================================
# سناریو ۲۰ — اجرای دوباره‌ی reverse
# ==========================================
def test_s20_second_reverse_does_not_credit_or_create_duplicates(world):
    first = submit(world, items((101, "Present")))
    session_id = first["session_id"]

    reverse_session_financial_impacts(session_id, world.db)
    assert_invariant(world.db, 101, "سناریو ۲۰ (بار اول)", expected=(0, 0, 0))
    txn_count = len(charge_rows(world.db, session_id))

    reverse_session_financial_impacts(session_id, world.db)
    reverse_session_financial_impacts(session_id, world.db)

    assert_invariant(world.db, 101, "سناریو ۲۰ (اجرای دوباره)", expected=(0, 0, 0)), \
        "اجرای دوباره‌ی reverse نباید کیف را دوباره افزایش دهد"
    assert len(charge_rows(world.db, session_id)) == txn_count, "تراکنش تکراری ساخته نشد"
    assert all(t.is_deleted for t in charge_rows(world.db, session_id))
    assert foreign_keys_ok(world.db)


# ==========================================
# سناریو ۲۱ — ویرایش جلسه
# ==========================================
def test_s21a_edit_reverses_old_amount_and_applies_new_one_once(world):
    first = submit(world, items((101, "Present"), (102, "Absent")))
    session_code, session_id = first["session_code"], first["session_id"]
    old_ids = {t.id for t in charge_rows(world.db, session_id)}

    # جلسه‌ی جدید: هر دو حاضر ⇒ T_total = ۱۲۰، I_total = ۸۰
    edit(world, session_code, items((101, "Present"), (102, "Present")))

    session = session_row(world.db, session_id)
    assert session.date == TODAY_JALALI
    assert (session.final_teacher_cost, session.final_institute_share) == (120, 80)
    assert (session.absent_penalty_teacher, session.absent_penalty_institute) == (0, 0), \
        "جریمه‌ی قبلی باید خنثی شود"

    all_txns = charge_rows(world.db, session_id)
    assert old_ids.issubset({t.id for t in all_txns}), "تراکنش قدیمی آرشیو می‌شود، حذف نمی‌شود"
    assert all(world.db.get(models.Transaction, tid).is_deleted for tid in old_ids)

    active = active_charge_rows(world.db, session_id)
    assert len(active) == 2, "برای هر دانش‌آموز فقط یک تراکنش فعال"
    assert {t.student_id for t in active} == {101, 102}
    assert all(t.share_teacher == 60 and t.share_institute == 40 for t in active)

    # کیف فقط یک بار با مبلغ جدید کاهش می‌یابد (نه دو بار، نه صفر)
    assert_invariant(world.db, 101, "سناریو ۲۱", expected=(-60, -40, -100))
    assert_invariant(world.db, 102, "سناریو ۲۱", expected=(-60, -40, -100))

    rows = {r.student_id: r.status for r in attendance_rows(world.db, session_id)}
    assert rows == {101: "Present", 102: "Present"}, "حضور قبلی جایگزین شده، رکورد تکراری نیست"
    assert len(attendance_rows(world.db, session_id)) == 2


def test_s21b_reports_show_only_the_new_amount_after_edit(world):
    first = submit(world, items((101, "Present")))
    assert calculate_teacher_session_revenue(world.db, 1, RANGE_START, RANGE_END) == 60

    edit(world, first["session_code"], items((101, "Present"), (102, "Present")))

    assert calculate_teacher_session_revenue(world.db, 1, RANGE_START, RANGE_END) == 120
    assert calculate_institute_session_revenue(world.db, RANGE_START, RANGE_END) == 80
    # توجه: `calculate_total_turnover` طبق تعریفش فقط «واریزی فیزیکی» (type=deposit) را می‌شمارد،
    # پس شارژ جلسه در آن نمی‌آید و باید صفر بماند (تفکیک درآمد نظری از پول دریافت‌شده).
    assert calculate_total_turnover(world.db, RANGE_START, RANGE_END) == 0
    assert_invariant(world.db, 101, "سناریو ۲۱ (گزارش)", expected=(-60, -40, -100))


# ==========================================
# سناریو ۲۲ — تغییر وضعیت در ویرایش
# ==========================================
def test_s22a_present_to_absent_moves_money_from_contract_to_penalty(world):
    first = submit(world, items((101, "Present"), (102, "Present")))
    session_id = first["session_id"]
    assert session_row(world.db, session_id).final_teacher_cost == 120

    edit(world, first["session_code"], items((101, "Absent"), (102, "Present")))

    session = session_row(world.db, session_id)
    assert (session.final_teacher_cost, session.final_institute_share) == (60, 40)
    assert (session.absent_penalty_teacher, session.absent_penalty_institute) == (60, 40)
    active = {t.student_id: t for t in active_charge_rows(world.db, session_id)}
    assert set(active) == {101, 102}
    assert "غایب غیرموجه" in active[101].description and "حاضر" in active[102].description
    # اثر مالی نهایی فقط از وضعیت جدید می‌آید: ۱۰۰ برای هرکدام (نه ۲۰۰)
    assert_invariant(world.db, 101, "سناریو ۲۲ا", expected=(-60, -40, -100))
    assert_invariant(world.db, 102, "سناریو ۲۲ا", expected=(-60, -40, -100))


def test_s22b_absent_to_present_removes_the_penalty(world):
    first = submit(world, items((101, "Present"), (102, "Absent")))
    session_id = first["session_id"]
    assert session_row(world.db, session_id).absent_penalty_teacher == 60

    edit(world, first["session_code"], items((101, "Present"), (102, "Present")))

    session = session_row(world.db, session_id)
    assert (session.absent_penalty_teacher, session.absent_penalty_institute) == (0, 0)
    assert (session.final_teacher_cost, session.final_institute_share) == (120, 80)
    assert len(active_charge_rows(world.db, session_id)) == 2
    assert_invariant(world.db, 102, "سناریو ۲۲ب", expected=(-60, -40, -100))
    assert_invariant(world.db, 101, "سناریو ۲۲ب", expected=(-60, -40, -100))


def test_s22c_excused_to_unexcused_applies_penalty_exactly_once(world):
    first = submit(world, items((101, "Present"), (102, "Absent", True)))
    session_id = first["session_id"]
    assert_invariant(world.db, 102, "قبل از ویرایش", expected=(0, 0, 0))
    assert session_row(world.db, session_id).absent_penalty_teacher == 0

    edit(world, first["session_code"], items((101, "Present"), (102, "Absent")))

    session = session_row(world.db, session_id)
    assert (session.absent_penalty_teacher, session.absent_penalty_institute) == (60, 40)
    assert [r.excused for r in attendance_rows(world.db, session_id)] == [False, False]
    assert_invariant(world.db, 102, "سناریو ۲۲پ", expected=(-60, -40, -100)), \
        "جریمه فقط یک بار اعمال شود"
    # برگشت به موجه، اثر جریمه را کامل خنثی می‌کند
    edit(world, first["session_code"], items((101, "Present"), (102, "Absent", True)))
    assert session_row(world.db, session_id).absent_penalty_teacher == 0
    assert_invariant(world.db, 102, "سناریو ۲۲پ (برگشت)", expected=(0, 0, 0))


# ==========================================
# سناریو ۲۳ — جلسه‌ی حذف‌شده
# ==========================================
def test_s23a_deleted_session_is_not_settleable_nor_reversible(world):
    first = submit(world, items((101, "Present")))
    session_id = first["session_id"]
    delete(world, first["session_code"])

    with pytest.raises(HTTPException) as error:
        settle(world, [session_id])
    assert error.value.status_code == 400, "جلسه‌ی حذف‌شده نباید در لیست تسویه پیدا شود"
    assert world.db.query(models.Settlement).count() == 0
    assert world.db.query(models.Transaction).filter(
        models.Transaction.type == "settlement_payout").count() == 0

    # reverse دوباره بی‌اثر است (سناریو ۲۰) و کیف دوباره شارژ نمی‌شود
    reverse_session_financial_impacts(session_id, world.db)
    assert_invariant(world.db, 101, "سناریو ۲۳", expected=(0, 0, 0))


def test_s23b_deleted_session_disappears_from_active_reports(world):
    first = submit(world, items((101, "Present")))
    history_before = attendance.get_history(HistoryRequest(course_id=world.course.id),
                                            db=world.db, authorization=f"Bearer {TOKEN}", sub_role="admin")
    assert len(history_before) == 1

    delete(world, first["session_code"])

    history_after = attendance.get_history(HistoryRequest(course_id=world.course.id),
                                           db=world.db, authorization=f"Bearer {TOKEN}", sub_role="admin")
    assert history_after == [], "جلسه‌ی حذف‌شده در گزارش فعال جلسات نباید بیاید"
    with pytest.raises(HTTPException) as error:
        attendance.get_session_details(first["session_code"], db=world.db,
                                       authorization=f"Bearer {TOKEN}", sub_role="admin")
    assert error.value.status_code == 404
    assert calculate_teacher_session_revenue(world.db, 1, RANGE_START, RANGE_END) == 0
    assert calculate_institute_session_revenue(world.db, RANGE_START, RANGE_END) == 0


def test_s23c_deleted_session_charge_cannot_be_refunded_again(world):
    """برگشت دوباره: تراکنش session_charge از مسیر refund عمومی قابل برگشت نیست و بعد از حذف هم ۴۰۴ است."""
    first = submit(world, items((101, "Present")))
    txn_id = charge_rows(world.db, first["session_id"])[0].id

    with pytest.raises(HTTPException) as error:
        finance.refund_transaction(txn_id, db=world.db, authorization=f"Bearer {TOKEN}", _="admin")
    assert error.value.status_code == 400
    assert "حذف جلسه" in str(error.value.detail)

    delete(world, first["session_code"])
    with pytest.raises(HTTPException) as error:
        finance.refund_transaction(txn_id, db=world.db, authorization=f"Bearer {TOKEN}", _="admin")
    assert error.value.status_code == 404
    assert_invariant(world.db, 101, "سناریو ۲۳ (refund دوباره)", expected=(0, 0, 0))


# ==========================================
# سناریو ۲۴ — settlement معلم
# ==========================================
def test_s24a_active_session_settles_exactly_once_with_consistent_amount(world):
    first = submit(world, items((101, "Present"), (102, "Absent")))
    session_id = first["session_id"]
    session = session_row(world.db, session_id)
    expected_total = (session.final_teacher_cost or 0) + (session.absent_penalty_teacher or 0)
    assert expected_total == 120

    out = settle(world, [session_id])
    assert out["total_amount"] == expected_total
    assert out["session_count"] == 1

    settlement = world.db.query(models.Settlement).one()
    assert (settlement.total_amount, settlement.session_count) == (expected_total, 1)
    payout = world.db.query(models.Transaction).filter(
        models.Transaction.type == "settlement_payout").one()
    assert payout.amount == -expected_total and payout.target_wallet == "teacher"
    assert session_row(world.db, session_id).is_penalty_settled is True
    assert [r.is_billed for r in attendance_rows(world.db, session_id) if r.status == "Present"] == [True]

    # تسویه‌ی تکراری: رد و بی‌اثر
    with pytest.raises(HTTPException) as error:
        settle(world, [session_id])
    assert error.value.status_code == 400
    assert world.db.query(models.Settlement).count() == 1
    assert world.db.query(models.Transaction).filter(
        models.Transaction.type == "settlement_payout").count() == 1


def test_s24b_all_absent_session_is_settleable_once_for_its_penalty(world):
    first = submit(world, items((101, "Absent"), (102, "Absent")))
    session_id = first["session_id"]
    session = session_row(world.db, session_id)
    assert session.final_teacher_cost == 0 and session.absent_penalty_teacher == 120

    out = settle(world, [session_id])
    assert out["total_amount"] == 120, "جریمه‌ی غیبت هم باید قابل تسویه‌ی یک‌باره باشد"

    with pytest.raises(HTTPException) as error:
        settle(world, [session_id])
    assert error.value.status_code == 400
    assert world.db.query(models.Settlement).count() == 1


def test_s24c_reversed_and_deleted_sessions_are_not_settleable(world):
    first = submit(world, items((101, "Present")))
    reverse_session_financial_impacts(first["session_id"], world.db)
    with pytest.raises(HTTPException) as error:
        settle(world, [first["session_id"]])
    assert error.value.status_code == 400

    second = submit(world, items((101, "Present")), date=OTHER_JALALI)
    delete(world, second["session_code"])
    with pytest.raises(HTTPException) as error:
        settle(world, [second["session_id"]])
    assert error.value.status_code == 400
    assert world.db.query(models.Settlement).count() == 0


def test_s24d_settle_rejects_a_list_containing_an_already_settled_session(world):
    first = submit(world, items((101, "Present")))
    second = submit(world, items((101, "Present")), date=OTHER_JALALI)
    settle(world, [first["session_id"]])
    with pytest.raises(HTTPException) as error:
        settle(world, [first["session_id"], second["session_id"]])
    assert error.value.status_code == 400, "حتی یک جلسه‌ی تسویه‌شده کل درخواست را رد می‌کند"
    assert world.db.query(models.Settlement).count() == 1
    assert session_row(world.db, second["session_id"]).is_penalty_settled is False


def test_s24e_settled_session_is_locked_for_edit_and_delete(world):
    first = submit(world, items((101, "Present")))
    settle(world, [first["session_id"]])

    with pytest.raises(HTTPException) as error:
        edit(world, first["session_code"], items((101, "Absent")))
    assert error.value.status_code == 409
    with pytest.raises(HTTPException) as error:
        delete(world, first["session_code"])
    assert error.value.status_code == 409
    assert session_row(world.db, first["session_id"]).is_deleted is False
    assert_invariant(world.db, 101, "سناریو ۲۴ (قفل تسویه)", expected=(-60, -40, -100))


def test_s24f_empty_session_has_nothing_to_settle(world):
    """جلسه‌ی بدون هیچ حاضر/جریمه قابل تسویه نیست (رد می‌شود) — پیام خطا گمراه‌کننده است."""
    first = submit(world, [])
    with pytest.raises(HTTPException) as error:
        settle(world, [first["session_id"]])
    assert error.value.status_code == 400
    assert "قبلاً تسویه شده" in str(error.value.detail), "پیام فعلی «قبلاً تسویه شده» است نه «چیزی برای تسویه»"
    assert world.db.query(models.Settlement).count() == 0


# ==========================================
# سناریو ۲۵ — rollback
# ==========================================
def test_s25a_error_midway_leaves_no_partial_state(world, monkeypatch):
    before = financial_snapshot(world.db)

    def boom(self):
        raise RuntimeError("شبیه‌سازی خطای میانه‌ی ثبت جلسه (سینک کیف)")

    monkeypatch.setattr(models.Student, "sync_wallet_balance", boom)
    with pytest.raises(RuntimeError):
        submit(world, items((101, "Present"), (102, "Present")))
    world.db.rollback()
    monkeypatch.undo()

    assert_no_writes(world.db, before, "سناریو ۲۵ (کرش میانه)")
    assert wallets(world.db, 101) == (0, 0, 0)
    assert wallets(world.db, 102) == (0, 0, 0)


def test_s25b_error_at_the_end_of_the_loop_rolls_back_the_session_row(world):
    """خطای قطعی H7 (نبود شعبه) بعد از شارژ برخی دانش‌آموزان ⇒ کل ثبت باید برگردد."""
    for sid in (101, 102):
        world.db.get(models.Student, sid).branch_id = None
    world.course.branch_id = None
    world.db.commit()
    before = financial_snapshot(world.db)

    with pytest.raises(HTTPException) as error:
        submit(world, items((101, "Present")))
    assert error.value.status_code == 400
    assert "شعبه" in str(error.value.detail)

    assert_no_writes(world.db, before, "سناریو ۲۵ (خطای انتهای حلقه)")
    assert wallets(world.db, 101) == (0, 0, 0)
    assert counter_value(world.db) in (None, 0) or counter_value(world.db) == before[-1]


def test_s25c_failed_edit_keeps_the_old_financial_effect_intact(world):
    first = submit(world, items((101, "Present")))
    session_id = first["session_id"]
    before_txn_ids = {t.id for t in active_charge_rows(world.db, session_id)}
    before_amount = session_row(world.db, session_id).final_teacher_cost

    # ویرایش با دانش‌آموز عضو کلاس دیگر ⇒ ۴۲۲ و هیچ تغییری (حتی reverse هم اجرا نمی‌شود)
    with pytest.raises(HTTPException) as error:
        edit(world, first["session_code"], items((103, "Present")))
    assert error.value.status_code == 422

    assert {t.id for t in active_charge_rows(world.db, session_id)} == before_txn_ids
    assert session_row(world.db, session_id).final_teacher_cost == before_amount
    assert_invariant(world.db, 101, "سناریو ۲۵ (ویرایش ناموفق)", expected=(-60, -40, -100))


# ==========================================
# سناریو ۲۶ — invariant در مسیر کامل
# ==========================================
def test_s26_invariant_holds_through_a_full_financial_walk(world):
    submit(world, items((101, "Present"), (102, "Absent")))
    assert_invariant(world.db, 101, "گام ۱ (ثبت)")
    assert_invariant(world.db, 102, "گام ۱ (غایب)")

    finance.submit_payment(
        __import__("schemas").FinanceSubmitData(
            student_id=101, amount=50, target_wallet="teacher", description="پرداخت تستی",
            payment_method="نقدی", date=TODAY_JALALI),
        db=world.db, _="admin", authorization=f"Bearer {TOKEN}")
    assert_invariant(world.db, 101, "گام ۲ (پرداخت)")

    first = world.db.query(models.SessionLog).one()
    edit(world, first.session_code, items((101, "Present"), (102, "Present")))
    assert_invariant(world.db, 101, "گام ۳ (ویرایش)")
    assert_invariant(world.db, 102, "گام ۳ (ویرایش)")

    delete(world, first.session_code)
    assert_invariant(world.db, 101, "گام ۴ (حذف)")
    assert_invariant(world.db, 102, "گام ۴ (حذف)")
    assert foreign_keys_ok(world.db)


# ==========================================
# سناریو ۲۷ — هم‌زمانی (SQLite-only)
# ==========================================
def _race_result(fn):
    try:
        return ("ok", fn())
    except HTTPException as error:
        return ("http", error.status_code)
    except Exception as error:            # noqa: BLE001 — نوع خطای رقیب برای گزارش لازم است
        return ("error", type(error).__name__)


def test_s27a_concurrent_submit_for_same_course_date_charges_once(file_world):
    """SQLite-only: فایل DB مشترک + دو Session مستقل (PostgreSQL اثبات نمی‌شود — در گزارش توضیح داده شده).

    گارد اصلی ایندکس یکتای partial `uq_session_course_date_active` است؛ فقط یک درخواست باید موفق شود.
    """
    barrier = Barrier(2)

    def racer(_):
        with file_world.factory() as db:
            barrier.wait(timeout=10)
            return _race_result(lambda: attendance.submit_session_and_calculate(
                AttendanceSubmitData(course_id=1, date=TODAY_JALALI,
                                     items=[AttendanceItem(student_id=101, status="Present")]),
                db=db, authorization=f"Bearer {TOKEN}", sub_role="admin"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(racer, (1, 2)))

    outcomes = [r[0] for r in results]
    assert outcomes.count("ok") == 1, f"باید دقیقاً یک ثبت موفق باشد: {results}"
    loser = [r for r in results if r[0] != "ok"][0]
    assert loser == ("http", 409), f"بازنده باید ۴۰۹ باشد نه {loser}"

    with file_world.factory() as db:
        assert db.query(func.count(models.SessionLog.id)).scalar() == 1
        assert db.query(func.count(models.Attendance.id)).scalar() == 1
        assert db.query(func.count(models.Transaction.id)).scalar() == 1
        student = db.get(models.Student, 101)
        assert (student.wallet_teacher, student.wallet_institute, student.wallet_balance) == (-60, -40, -100)
        assert foreign_keys_ok(db)


def test_s27b_concurrent_reverse_credits_the_wallet_only_once(file_world):
    with file_world.factory() as db:
        session_id = attendance.submit_session_and_calculate(
            AttendanceSubmitData(course_id=1, date=TODAY_JALALI,
                                 items=[AttendanceItem(student_id=101, status="Present")]),
            db=db, authorization=f"Bearer {TOKEN}", sub_role="admin")["session_id"]

    barrier = Barrier(2)

    def reverter(_):
        with file_world.factory() as db:
            barrier.wait(timeout=10)
            return _race_result(lambda: reverse_session_financial_impacts(session_id, db))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reverter, (1, 2)))

    assert all(r[0] == "ok" for r in results), f"هر دو reverse باید بی‌خطا تمام شوند: {results}"
    with file_world.factory() as db:
        student = db.get(models.Student, 101)
        assert (student.wallet_teacher, student.wallet_institute, student.wallet_balance) == (0, 0, 0), \
            "کیف باید فقط یک بار restore شود (نه دو بار)"
        assert db.query(models.Transaction).filter(models.Transaction.is_deleted == False).count() == 0
        assert db.query(models.Transaction).count() == 1, "تراکنش تکراری ساخته نشد"
        assert foreign_keys_ok(db)


# ==========================================
# یافته‌های تکمیلی (خارج از شماره‌گذاری ۲۷ سناریو)
# ==========================================
def test_s_ext_items_finding_empty_attendee_list_occupies_the_date(world):
    """🔎 F-S3 (عمداً fail): `items=[]` پذیرفته می‌شود و یک SessionLog می‌سازد که همان (کلاس، تاریخ)
    را اشغال می‌کند؛ ثبت واقعی بعدی همان روز **۴۰۹** می‌گیرد — یعنی یک درخواست بی‌محتوا می‌تواند
    جلسه‌ی واقعی کلاس را قفل کند."""
    submit(world, [])
    assert world.db.query(func.count(models.SessionLog.id)).scalar() == 0, \
        "F-S3: درخواست بدون هیچ ردیف حضور/غیاب نباید جلسه بسازد"

    # و اگر ساخته نشد، ثبت واقعی باید موفق باشد
    submit(world, items((101, "Present")))


@pytest.mark.parametrize("bogus_status", ["banana", "present", "PRESENT", "حاضر", ""])
def test_s_ext_status_finding_unknown_status_is_silently_free(world, bogus_status):
    """🔎 F-S4 (عمداً fail): وضعیت ناشناخته/کوچک‌نویس پذیرفته می‌شود، ردیف حضور با همان متن ثبت
    می‌شود و **هیچ شارژی** رخ نمی‌دهد (`should_charge=False`) — نه خطا، نه هشدار.
    یعنی یک تایپ ساده در کلاینت بی‌صدا درآمد جلسه را صفر می‌کند.

    انتظار: فقط وضعیت‌های معتبر پروژه (`Present`/`Late`/`Absent` طبق `models.Attendance.status`
    و فیلترهای is_billed/جریمه) پذیرفته شوند و بقیه مثل خطای تاریخ/عضویت ⇒ ۴۲۲.
    """
    before = financial_snapshot(world.db)
    with pytest.raises(HTTPException) as error:
        submit(world, items((101, bogus_status)))
    assert error.value.status_code == 422, f"وضعیت {bogus_status!r} باید رد شود"
    assert_no_writes(world.db, before, f"وضعیت نامعتبر {bogus_status!r}")
