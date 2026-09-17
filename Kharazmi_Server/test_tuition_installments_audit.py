"""
Tuition / Discount / Contractual Debt / Enrollment / Installment — TEST-ONLY audit
(فقط تست و گزارش؛ هیچ تغییر در کد اصلی پروژه انجام نشده است)

## دامنه
`financial_calculations.calculate_enrollment_debt` / `calculate_student_debt`،
`dependencies.get_enrollment_tuition_and_discount`، مسیر ثبت‌نام (`classes.add_enrollment`)،
مسیر اقساط (`finance.create_installment` / `pay_installment_manually` / مانده‌ی FIFO در
`submit_payment`) و بازتاب آن‌ها در debtors/dashboard/reminders/پروفایل مالی.
منطق کیف پول فقط در حد ساخت fixture و بررسی عدم‌تداخل استفاده می‌شود.

## نگاشت سناریوها
| # | سناریو | تست |
|---|---|---|
| ۱ | شهریه ۱۰۰۰ / پرداخت ۲۰۰ ⇒ بدهی ۸۰۰ | `test_s01_*` |
| ۲ | تخفیف درصدی ۱۰٪ | `test_s02_*` |
| ۳ | تخفیف ثابت ۳۰۰ | `test_s03_*` |
| ۴ | تخفیف > ۱۰۰٪ (رد شدن / عدم بدهی منفی) | `test_s04_*` |
| ۵ | discount_value منفی | `test_s05*` |
| ۶ | total_paid منفی | `test_s06*` |
| ۷ | پرداخت بیشتر از شهریه ⇒ بدهی منفی نشود | `test_s07_*` |
| ۸ | جدایی بدهی قراردادی از بدهی کیف | `test_s08_*` |
| ۹ | چند enrollment و overpayment یکی از آن‌ها | `test_s09_*` |
| ۱۰ | enrollment فعال با شهریه معتبر | `test_s10_*` |
| ۱۱ | enrollment حذف‌شده در بدهی فعال نیاید | `test_s11_*` |
| ۱۲ | enrollment legacy با tuition صفر (fallback کیف) | `test_s12_*` |
| ۱۳ | ساخت قسط برای enrollment فعال | `test_s13_*` |
| ۱۴ | ساخت قسط برای enrollment حذف‌شده | `test_s14_*` |
| ۱۵ | پرداخت کامل قسط | `test_s15_*` |
| ۱۶ | پرداخت جزئی تجمعی | `test_s16_*` |
| ۱۷ | چند پرداخت جزئی | `test_s17_*` |
| ۱۸ | پرداخت دوباره‌ی قسط تسویه‌شده | `test_s18_*` |
| ۱۹ | پرداخت بیشتر از مانده‌ی قسط | `test_s19_*` |
| ۲۰ | قسط enrollment حذف‌شده در ۴ نما | `test_s20_*` |
| ۲۱ | تاریخ‌های جلالی | `test_s21*` |
| ۲۲ | بعد از پرداخت قسط | `test_s22_*` |
| ۲۳ | rollback وسط پرداخت | `test_s23_*` |
| ۲۴ | دو پرداخت هم‌زمان روی یک قسط | `test_s24_*` |

## ⚠️ تست‌های یافته‌محور (عمداً fail می‌شوند)
`test_finding_t1_*` و `test_finding_t2_*` نقص‌های واقعی را مستند می‌کنند (طبق دستور تسک هیچ fix‌ای
انجام نشده). اگر روزی اصلاح شوند سبز/XPASS می‌شوند.

## اجرا (طبق قانون پروژه: فقط روی DB تست/کپی — هرگز gaj_db.db واقعی)
    cd /home/user/KharazmiApp && DATABASE_URL=sqlite:////tmp/tuition_audit.db \
        PYTHONPATH=/home/user/KharazmiApp/Kharazmi_Server \
        python3 -m pytest Kharazmi_Server/test_tuition_installments_audit.py -q
"""
import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, event, func, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from dependencies import get_enrollment_tuition_and_discount
from financial_calculations import (
    calculate_enrollment_debt,
    calculate_institute_collected_revenue,
    calculate_student_debt,
    calculate_total_turnover,
)
from routers import classes, dashboard, finance
from routers.finance import InstallmentCreateRequest
from schemas import EnrollmentCreate, FinanceSubmitData, InstallmentCreate
from today_summary import parse_project_date

TOKEN = "tuition-admin-token"
TODAY_JALALI = "1405/06/16"          # تاریخ معتبر گذشته‌نسبت به امروز
PAST_JALALI = "1399/01/01"
FUTURE_JALALI = "1406/01/01"
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


def seed_world(db, total_tuition=1000, total_paid=200, discount_type="none", discount_value=0):
    """دانش‌آموز + دو کلاس + یک ثبت‌نام فعال (پیش‌فرض: ۱۰۰۰ شهریه، ۲۰۰ پرداخت‌شده ⇒ بدهی ۸۰۰)."""
    db.add_all([models.Branch(id=1, name="شعبه تست", active=True)])
    db.flush()
    user = models.User(id=1, username="tuition-admin", password="unused", role="admin",
                       sub_role="admin", branch_id=1)
    teacher = models.Teacher(id=1, teacher_code=101, first_name="معلم", last_name="تست",
                             mobile="09120000101", branch_id=1)
    student = models.Student(
        id=101, student_code=100101, first_name="دانش‌آموز", last_name="تست",
        national_code="TU-101", student_mobile="09121110101", parent_mobile="09122220101",
        branch_id=1, wallet_teacher=0, wallet_institute=0, wallet_balance=0,
    )
    db.add_all([user, teacher, student])
    db.flush()
    db.add_all([
        models.Course(id=1, title="کلاس یک", code="TU10001", teacher_id=teacher.id, branch_id=1,
                      grade_level="دهم", teacher_session_price=60, is_admin_approved=True),
        models.Course(id=2, title="کلاس دو", code="TU10002", teacher_id=teacher.id, branch_id=1,
                      grade_level="دهم", teacher_session_price=50, is_admin_approved=True),
    ])
    db.flush()
    enrollment = models.Enrollment(
        student_id=student.id, course_id=1, branch_id=1, register_date=TODAY_JALALI, shift="صبح",
        total_tuition=total_tuition, total_paid=total_paid,
        discount_type=discount_type, discount_value=discount_value,
    )
    db.add_all([
        enrollment,
        models.UserSession(token=TOKEN, user_id=user.id, sub_role="admin",
                           created_at=datetime.datetime.now()),
    ])
    db.commit()
    return SimpleNamespace(db=db, user=user, teacher=teacher, student=student,
                           course1=db.get(models.Course, 1), course2=db.get(models.Course, 2),
                           enrollment=enrollment)


@pytest.fixture
def world():
    """DB درون‌حافظه‌ای اختصاصی هر تست — هیچ فایلی از پروژه خوانده/نوشته نمی‌شود."""
    engine = make_engine(poolclass=StaticPool)
    with sessionmaker(bind=engine, expire_on_commit=False)() as db:
        yield seed_world(db)
    models.Base.metadata.drop_all(engine)
    engine.dispose()


# ---------- helpers ----------
def wallets(db, student_id=101):
    db.expire_all()
    student = db.get(models.Student, student_id)
    return (student.wallet_teacher or 0), (student.wallet_institute or 0), (student.wallet_balance or 0)


def assert_wallet_invariant(db, student_id=101, context=""):
    """منطق کیف فقط در حد «عدم تداخل» بررسی می‌شود (خارج از دامنه‌ی این تسک)."""
    teacher, institute, balance = wallets(db, student_id)
    assert balance == teacher + institute, (
        f"نقض invariant کیف {context}: {balance} != {teacher} + {institute}"
    )
    return teacher, institute, balance


def fresh(db, obj):
    db.expire_all()
    return db.get(type(obj), obj.id)


def tuition_parts(enrollment):
    """(شهریه نهایی، مبلغ تخفیف) طبق لایه‌ی محاسبات مرکزی."""
    return get_enrollment_tuition_and_discount(enrollment)


def enrollment_debt(db, enrollment_id=1):
    db.expire_all()
    return calculate_enrollment_debt(db.get(models.Enrollment, enrollment_id))


def student_debt(db, student_id=101):
    db.expire_all()
    return calculate_student_debt(db, db.get(models.Student, student_id))


def add_enrollment(world, course_id=2, total_tuition=1000, paid_amount=0,
                   discount_type="none", discount_value=0, installments=None):
    data = EnrollmentCreate(
        student_id=world.student.id, course_id=course_id, register_date=TODAY_JALALI, shift="صبح",
        total_tuition=total_tuition, paid_amount=paid_amount, payment_method="نقدی",
        receiver="صندوق", discount_type=discount_type, discount_value=discount_value,
        installments=installments,
    )
    return classes.add_enrollment(data, db=world.db, _="admin")


def pay(world, amount, enrollment_id=1, wallet="institute", method="نقدی"):
    values = dict(student_id=world.student.id, amount=amount, target_wallet=wallet,
                  description="پرداخت تستی", payment_method=method, date=TODAY_JALALI,
                  enrollment_id=enrollment_id)
    result = finance.submit_payment(FinanceSubmitData(**values), db=world.db, _="admin",
                                   authorization=f"Bearer {TOKEN}")
    assert_wallet_invariant(world.db, context="بعد از پرداخت")
    return result


def create_installment(world, enrollment_id=1, amount=100, due_date=TODAY_JALALI):
    return finance.create_installment(
        InstallmentCreateRequest(enrollment_id=enrollment_id, amount=amount, due_date=due_date),
        db=world.db, authorization=f"Bearer {TOKEN}", _="admin",
    )


def installment_row(db, installment_id):
    db.expire_all()
    return db.get(models.Installment, installment_id)


def pay_installment_manually(world, installment_id, method="نقدی"):
    return finance.pay_installment_manually(
        installment_id, db=world.db, _="admin", payment_method=method,
        authorization=f"Bearer {TOKEN}",
    )


def deposit_transactions(db):
    db.expire_all()
    return db.query(models.Transaction).filter(models.Transaction.type == "deposit").all()


# ==========================================
# سناریو ۱ — شهریه ۱۰۰۰ و پرداخت ۲۰۰ ⇒ بدهی ۸۰۰
# ==========================================
def test_s01_tuition_1000_paid_200_gives_debt_800(world):
    assert (world.enrollment.total_tuition, world.enrollment.total_paid) == (1000, 200)
    assert enrollment_debt(world.db) == 800
    assert student_debt(world.db) == 800


# ==========================================
# سناریو ۲ — تخفیف درصدی ۱۰٪
# ==========================================
def test_s02_percentage_discount_10_percent(world):
    enrollment = world.enrollment
    enrollment.discount_type, enrollment.discount_value = "percentage", 10
    world.db.commit()

    final, discount = tuition_parts(enrollment)
    assert (final, discount) == (900, 100), f"۱۰٪ از ۱۰۰۰ ⇒ نهایی ۹۰۰ و تخفیف ۱۰۰؛ شد {(final, discount)}"
    assert enrollment_debt(world.db) == 700, "بدهی = ۹۰۰ − ۲۰۰"
    assert student_debt(world.db) == 700


# ==========================================
# سناریو ۳ — تخفیف ثابت ۳۰۰
# ==========================================
def test_s03_fixed_discount_300(world):
    enrollment = world.enrollment
    enrollment.discount_type, enrollment.discount_value = "fixed", 300
    world.db.commit()

    final, discount = tuition_parts(enrollment)
    assert (final, discount) == (700, 300), f"شد {(final, discount)}"
    assert enrollment_debt(world.db) == 500, "بدهی = ۷۰۰ − ۲۰۰"


# ==========================================
# سناریو ۴ — تخفیف بیشتر از ۱۰۰٪
# ==========================================
@pytest.mark.parametrize("bad_percentage", [101, 150, 1000])
def test_s04a_api_rejects_percentage_over_100(world, bad_percentage):
    with pytest.raises(HTTPException) as error:
        add_enrollment(world, course_id=2, discount_type="percentage", discount_value=bad_percentage)
    assert error.value.status_code == 400, "policy پروژه: درصد تخفیف خارج از ۰..۱۰۰ ⇒ ۴۰۰"
    assert world.db.query(models.Enrollment).filter(models.Enrollment.course_id == 2).count() == 0


def test_s04b_calc_layer_never_produces_negative_tuition_or_debt(world):
    """حتی اگر داده‌ی تخفیف >۱۰۰٪ از مسیر غیر-API وارد شود، بدهی هرگز منفی نمی‌شود (clamp صریح)."""
    enrollment = world.enrollment
    enrollment.discount_type, enrollment.discount_value = "percentage", 150
    world.db.commit()

    final, discount = tuition_parts(enrollment)
    assert final == 0, f"شهریه نهایی باید صفر شود (clamp) نه منفی؛ شد {final}"
    assert discount == 1500
    assert enrollment_debt(world.db) == 0
    assert student_debt(world.db) == 0


# ==========================================
# سناریو ۵ — discount_value منفی
# ==========================================
@pytest.mark.parametrize("d_type", ["percentage", "fixed"])
def test_s05a_api_rejects_negative_discount_value(world, d_type):
    with pytest.raises(HTTPException) as error:
        add_enrollment(world, course_id=2, discount_type=d_type, discount_value=-5)
    assert error.value.status_code == 400
    assert world.db.query(models.Enrollment).filter(models.Enrollment.course_id == 2).count() == 0


def test_s05b_calc_layer_behaviour_for_negative_discount_is_documented(world):
    """رفتار مستند برای داده‌ی غیر-API: تخفیف منفی مثل «افزایش شهریه» عمل می‌کند
    (`final = base − (−x) = base + x`) و هیچ خطا/clamp‌ای رخ نمی‌دهد. لایه‌ی API جلوی ورودش را می‌گیرد."""
    enrollment = world.enrollment
    enrollment.discount_type, enrollment.discount_value = "percentage", -10
    world.db.commit()
    final, discount = tuition_parts(enrollment)
    assert (final, discount) == (1100, -100), f"شد {(final, discount)}"
    assert enrollment_debt(world.db) == 900, "بدهی = ۱۱۰۰ − ۲۰۰ (نه کمتر)"


# ==========================================
# سناریو ۶ — total_paid منفی
# ==========================================
def test_s06a_schema_rejects_negative_paid_amount(world):
    with pytest.raises(ValidationError):
        EnrollmentCreate(student_id=101, course_id=2, register_date=TODAY_JALALI, shift="صبح",
                         total_tuition=1000, paid_amount=-1, payment_method="نقدی", receiver="صندوق")


def test_s06b_negative_total_paid_in_db_is_documented(world):
    """رفتار مستند برای داده‌ی غیر-API: total_paid منفی بدهی را بیشتر می‌کند (بدون clamp منفی)."""
    world.enrollment.total_paid = -50
    world.db.commit()
    assert enrollment_debt(world.db) == 1050, "۱۰۰۰ − (−۵۰) = ۱۰۵۰"


# ==========================================
# سناریو ۷ — پرداخت بیشتر از شهریه
# ==========================================
def test_s07_overpayment_never_makes_debt_negative(world):
    world.enrollment.total_paid = 1500
    world.db.commit()
    assert enrollment_debt(world.db) == 0
    assert student_debt(world.db) == 0

    profile = finance.get_student_financial_dashboard(101, db=world.db,
                                                      authorization=f"Bearer {TOKEN}", _role="admin")
    assert profile["enrollments"][0]["outstanding"] == 0, "بدهی نمایشی هم نباید منفی شود"


# ==========================================
# سناریو ۸ — جدایی بدهی قراردادی از بدهی کیف پول
# ==========================================
def test_s08_contractual_and_wallet_debt_stay_separate(world):
    world.db.query(models.Student).filter(models.Student.id == 101).update(
        {models.Student.wallet_teacher: -30, models.Student.wallet_institute: -20},
        synchronize_session=False)
    world.db.commit()
    student = fresh(world.db, world.student)
    student.sync_wallet_balance()
    world.db.commit()
    assert wallets(world.db)[:2] == (-30, -20)

    # بدهی قراردادی فقط از شهریه/پرداخت می‌آید و کیف‌ها به آن اضافه نمی‌شوند
    assert enrollment_debt(world.db) == 800
    assert student_debt(world.db) == 800, "بدهی کل نباید ۸۰۰+۳۰+۲۰ شود"

    rows = finance.get_debtors_list(db=world.db, authorization=f"Bearer {TOKEN}", _="admin")
    row = next(r for r in rows if r["student_id"] == 101)
    assert row["total_debt"] == 800
    assert (row["debt_teacher"], row["debt_institute"]) == (30, 20), "بدهی کیف جداگانه گزارش می‌شود"


# ==========================================
# سناریو ۹ — چند enrollment و overpayment
# ==========================================
def test_s09_overpayment_in_one_enrollment_does_not_cancel_another(world):
    add_enrollment(world, course_id=2, total_tuition=500, paid_amount=600)   # پیش‌پرداخت بیشتر از شهریه
    assert enrollment_debt(world.db, 1) == 800
    assert enrollment_debt(world.db, 2) == 0, "overpayment یک ثبت‌نام نباید بدهی دیگری را حذف کند"
    assert student_debt(world.db) == 800

    # و برعکس: پرداختِ ثبت‌نام دوم به بدهی ثبت‌نام اول سرایت نمی‌کند
    pay(world, 100, enrollment_id=2)
    assert enrollment_debt(world.db, 1) == 800
    assert enrollment_debt(world.db, 2) == 0


# ==========================================
# سناریو ۱۰ — enrollment فعال با شهریه معتبر
# ==========================================
def test_s10_active_enrollment_debt_comes_from_tuition_and_paid(world):
    assert enrollment_debt(world.db) == 1000 - 200
    pay(world, 300, enrollment_id=1)
    assert enrollment_debt(world.db) == 1000 - 500
    assert fresh(world.db, world.enrollment).total_paid == 500


# ==========================================
# سناریو ۱۱ — enrollment حذف‌شده
# ==========================================
def test_s11_deleted_enrollment_is_excluded_from_active_debt(world):
    classes.delete_enrollment(1, db=world.db, _="admin")
    assert fresh(world.db, world.enrollment).is_deleted is True

    assert enrollment_debt(world.db, 1) == 0, "ثبت‌نام آرشیوشده بدهی فعال ندارد"
    assert student_debt(world.db) == 0
    rows = finance.get_debtors_list(db=world.db, authorization=f"Bearer {TOKEN}", _="admin")
    assert all(r["student_id"] != 101 for r in rows), "شاگرد بدون بدهی فعال نباید در بدهکاران بیاید"


# ==========================================
# سناریو ۱۲ — enrollment legacy با total_tuition صفر
# ==========================================
def test_s12_legacy_zero_tuition_falls_back_to_wallet_debt(world):
    world.enrollment.total_tuition = 0
    world.db.commit()
    world.db.query(models.Student).filter(models.Student.id == 101).update(
        {models.Student.wallet_teacher: -30, models.Student.wallet_institute: -20},
        synchronize_session=False)
    world.db.commit()
    student = fresh(world.db, world.student)
    student.sync_wallet_balance()
    world.db.commit()

    assert enrollment_debt(world.db) == 0
    assert student_debt(world.db) == 50, "fallback legacy = ۳۰ + ۲۰ (بدهی کیف‌ها)"


def test_s12b_priced_enrollment_takes_precedence_over_legacy_wallet_debt(world):
    """اگر ثبت‌نام فعالِ قیمت‌دار وجود دارد، بدهی کیف نادیده گرفته می‌شود (Bug16)."""
    world.db.query(models.Student).filter(models.Student.id == 101).update(
        {models.Student.wallet_teacher: -500, models.Student.wallet_institute: -400},
        synchronize_session=False)
    world.db.commit()
    student = fresh(world.db, world.student)
    student.sync_wallet_balance()
    world.db.commit()

    assert student_debt(world.db) == 800, "بدهی قراردادی (۸۰۰)، نه ۹۰۰ بدهی کیف"


# ==========================================
# سناریو ۱۳ — ساخت قسط برای ثبت‌نام فعال
# ==========================================
def test_s13_create_installment_for_active_enrollment(world):
    result = create_installment(world, enrollment_id=1, amount=250, due_date="1405/07/01")
    row = installment_row(world.db, result["installment_id"])
    assert (row.enrollment_id, row.amount, row.due_date) == (1, 250, "1405/07/01")
    assert row.is_paid is False and not row.is_deleted
    assert (row.paid_amount or 0) == 0


# ==========================================
# سناریو ۱۴ — ساخت قسط برای ثبت‌نام حذف‌شده
# ==========================================
def test_s14_create_installment_for_deleted_enrollment_is_rejected(world):
    classes.delete_enrollment(1, db=world.db, _="admin")
    with pytest.raises(HTTPException) as error:
        create_installment(world, enrollment_id=1, amount=100)
    assert error.value.status_code == 404
    world.db.rollback()
    assert world.db.query(models.Installment).count() == 0


# ==========================================
# سناریو ۱۵ — پرداخت کامل قسط
# ==========================================
def test_s15_full_manual_payment_settles_installment(world):
    installment_id = create_installment(world, amount=300, due_date="1405/07/01")["installment_id"]
    result = pay_installment_manually(world, installment_id)

    row = installment_row(world.db, installment_id)
    assert row.is_paid is True
    assert row.paid_amount == row.amount == 300
    assert row.paid_at, "زمان پرداخت باید ثبت شود"

    assert fresh(world.db, world.enrollment).total_paid == 500, "۲۰۰ + ۳۰۰"
    assert enrollment_debt(world.db) == 500
    assert wallets(world.db)[1] == 300, "فقط کیف آموزشگاه شارژ می‌شود"
    assert_wallet_invariant(world.db, context="پس از تسویه‌ی قسط")

    receipts = deposit_transactions(world.db)
    assert len(receipts) == 1 and receipts[0].amount == 300 and receipts[0].id == result["receipt_id"]
    allocations = world.db.query(models.TransactionInstallmentAllocation).all()
    assert len(allocations) == 1 and allocations[0].amount == 300


# ==========================================
# سناریو ۱۶ — پرداخت جزئی تجمعی
# ==========================================
def test_s16_partial_payments_accumulate_without_overwrite(world):
    installment_id = create_installment(world, amount=100, due_date="1405/07/01")["installment_id"]

    pay(world, 30, enrollment_id=1)
    row = installment_row(world.db, installment_id)
    assert (row.paid_amount, row.is_paid) == (30, False), "پوشش جزئی باید ثبت شود ولی تسویه نه"

    pay(world, 40, enrollment_id=1)
    row = installment_row(world.db, installment_id)
    assert (row.paid_amount, row.is_paid) == (70, False), (
        f"پوشش باید تجمعی باشد (۳۰+۴۰=۷۰)، نه بازنویسی‌شده؛ شد {(row.paid_amount, row.is_paid)}"
    )
    assert fresh(world.db, world.enrollment).total_paid == 200 + 70


# ==========================================
# سناریو ۱۷ — چند پرداخت جزئی و سقف مبلغ قسط
# ==========================================
def test_s17_multiple_partials_never_exceed_amount_and_settle_at_full_cover(world):
    installment_id = create_installment(world, amount=100, due_date="1405/07/01")["installment_id"]

    pay(world, 30, enrollment_id=1)
    pay(world, 40, enrollment_id=1)
    pay(world, 30, enrollment_id=1)
    row = installment_row(world.db, installment_id)
    assert (row.paid_amount, row.is_paid) == (100, True), f"شد {(row.paid_amount, row.is_paid)}"

    # پرداخت بیشتر: قسط نباید فراتر از مبلغش پر شود
    pay(world, 500, enrollment_id=1)
    row = installment_row(world.db, installment_id)
    assert row.paid_amount == 100, f"مجموع پوشش نباید از مبلغ قسط بیشتر شود؛ شد {row.paid_amount}"
    assert row.is_paid is True


# ==========================================
# سناریو ۱۸ — پرداخت دوباره‌ی قسط تسویه‌شده
# ==========================================
def test_s18_paying_settled_installment_is_rejected_and_inert(world):
    installment_id = create_installment(world, amount=100, due_date="1405/07/01")["installment_id"]
    pay_installment_manually(world, installment_id)
    before = (fresh(world.db, world.enrollment).total_paid, wallets(world.db), len(deposit_transactions(world.db)))

    with pytest.raises(HTTPException) as error:
        pay_installment_manually(world, installment_id)
    assert error.value.status_code == 400, "قسط تسویه‌شده ⇒ ۴۰۰"
    world.db.rollback()

    after = (fresh(world.db, world.enrollment).total_paid, wallets(world.db), len(deposit_transactions(world.db)))
    assert after == before, f"هیچ اثر مالی نباید دوباره اعمال شود: {after} != {before}"

    # مسیر پرداخت عمومی (FIFO) هم نباید قسط تسویه‌شده را دوباره پر کند
    pay(world, 50, enrollment_id=1)
    row = installment_row(world.db, installment_id)
    assert row.paid_amount == 100 and row.is_paid is True


# ==========================================
# سناریو ۱۹ — پرداخت بیشتر از مانده‌ی قسط
# ==========================================
def test_s19_overpayment_beyond_remaining_is_not_recorded_twice(world):
    installment_id = create_installment(world, amount=100, due_date="1405/07/01")["installment_id"]
    pay(world, 90, enrollment_id=1)
    assert installment_row(world.db, installment_id).paid_amount == 90

    pay(world, 400, enrollment_id=1)          # ۱۰ پوشش قسط + ۳۹۰ اعتبار کیف
    row = installment_row(world.db, installment_id)
    assert (row.paid_amount, row.is_paid) == (100, True), (
        f"فقط مانده (۱۰) باید ثبت شود؛ شد {(row.paid_amount, row.is_paid)}"
    )
    allocations = world.db.query(models.TransactionInstallmentAllocation).filter(
        models.TransactionInstallmentAllocation.installment_id == installment_id).all()
    assert sum(a.amount for a in allocations) == 100, "مجموع ledger پوشش هم نباید از مبلغ قسط بگذرد"

    # مسیر دستی روی قسطی که پوشش کامل دارد ⇒ ۴۰۰ (مبلغی برای وصول نیست)
    other_id = create_installment(world, amount=100, due_date="1405/07/02")["installment_id"]
    world.db.query(models.Installment).filter(models.Installment.id == other_id).update(
        {models.Installment.paid_amount: 100}, synchronize_session=False)
    world.db.commit()
    with pytest.raises(HTTPException) as error:
        pay_installment_manually(world, other_id)
    assert error.value.status_code == 400
    world.db.rollback()


# ==========================================
# سناریو ۲۰ — قسطِ ثبت‌نام حذف‌شده در چهار نما
# ==========================================
def test_s20_deleted_enrollment_installments_are_hidden_everywhere(world):
    installment_id = create_installment(world, amount=100, due_date=PAST_JALALI)["installment_id"]
    dashboard._clear_dashboard_cache()
    before = dashboard.get_dashboard_kpis(db=world.db, _="admin")
    assert before.overdue_installments_count == 1, "پیش‌نیاز تست: قسط معوقه دیده می‌شود"

    classes.delete_enrollment(1, db=world.db, _="admin")
    row = installment_row(world.db, installment_id)
    assert row.is_deleted is True, "حذف ثبت‌نام باید اقساطش را آرشیو کند"

    dashboard._clear_dashboard_cache()
    after = dashboard.get_dashboard_kpis(db=world.db, _="admin")
    assert after.overdue_installments_count == 0, "داشبورد نباید قسط ثبت‌نام حذف‌شده را بشمارد"

    rows = finance.get_debtors_list(db=world.db, authorization=f"Bearer {TOKEN}", _="admin")
    assert all(r["student_id"] != 101 for r in rows), "debtors نباید شاگردِ بدون بدهی فعال را بیاورد"

    with pytest.raises(HTTPException) as error:
        finance.send_installment_payment_reminder(installment_id, db=world.db, _="admin")
    assert error.value.status_code == 404, "یادآوری قسط آرشیوشده ⇒ ۴۰۴"
    world.db.rollback()

    profile = finance.get_student_financial_dashboard(101, db=world.db,
                                                      authorization=f"Bearer {TOKEN}", _role="admin")
    assert profile["installments"] == [], "پروفایل مالی نباید قسط ثبت‌نام حذف‌شده را نشان دهد"
    assert profile["enrollments"] == [], "و نه خود ثبت‌نام حذف‌شده را"
    assert finance.get_all_installments(student_id=101, db=world.db,
                                        authorization=f"Bearer {TOKEN}", sub_role="admin") == []


# ==========================================
# سناریو ۲۱ — تاریخ‌های جلالی
# ==========================================
@pytest.mark.parametrize("due_date", [TODAY_JALALI, PAST_JALALI, FUTURE_JALALI, "1405/12/29"])
def test_s21a_valid_jalali_due_dates_are_accepted(world, due_date):
    result = create_installment(world, amount=10, due_date=due_date)
    assert installment_row(world.db, result["installment_id"]).due_date == due_date
    assert parse_project_date(due_date) is not None, "تاریخ معتبر باید parse شود"


@pytest.mark.parametrize("bad_date", ["not-a-date", "1405/13/45", "1405/7/15", "", "2026-09-17T00"])
def test_s21b_invalid_jalali_due_dates_are_rejected_with_422(world, bad_date):
    with pytest.raises(ValidationError):
        InstallmentCreateRequest(enrollment_id=1, amount=10, due_date=bad_date)


def test_s21c_overdue_status_uses_parsed_jalali_date(world):
    past = create_installment(world, amount=100, due_date=PAST_JALALI)["installment_id"]
    future = create_installment(world, amount=100, due_date=FUTURE_JALALI)["installment_id"]
    pay_installment_manually(world, future)              # قسط آینده را تسویه می‌کنیم
    profile = finance.get_student_financial_dashboard(101, db=world.db,
                                                      authorization=f"Bearer {TOKEN}", _role="admin")
    by_id = {row["id"]: row for row in profile["installments"]}
    assert by_id[past]["status"] == "معوقه"
    assert by_id[future]["status"] == "پرداخت شده"


# ==========================================
# سناریو ۲۲ — بعد از پرداخت قسط
# ==========================================
def test_s22_after_installment_payment_everything_is_consistent(world):
    installment_id = create_installment(world, amount=400, due_date="1405/07/01")["installment_id"]
    pay_installment_manually(world, installment_id)

    row = installment_row(world.db, installment_id)
    assert (row.is_paid, row.paid_amount) == (True, 400)
    assert fresh(world.db, world.enrollment).total_paid == 600
    assert enrollment_debt(world.db) == 400
    assert student_debt(world.db) == 400

    assert calculate_institute_collected_revenue(world.db, RANGE_START, RANGE_END) == 400
    assert calculate_total_turnover(world.db, RANGE_START, RANGE_END) == 400

    profile = finance.get_student_financial_dashboard(101, db=world.db,
                                                      authorization=f"Bearer {TOKEN}", _role="admin")
    assert profile["wallet"]["total_debt"] == 400
    assert profile["wallet"]["total_paid"] == 600
    assert profile["enrollments"][0]["total_paid"] == 600
    assert profile["installments"][0]["is_paid"] is True


# ==========================================
# سناریو ۲۳ — rollback وسط پرداخت قسط
# ==========================================
def test_s23a_failure_midway_leaves_no_partial_state(world, monkeypatch):
    """خطا بعد از UPDATEهای کیف/قسط و قبل از کامیت ⇒ هیچ نیمه‌تغییری نباید باقی بماند."""
    installment_id = create_installment(world, amount=100, due_date="1405/07/01")["installment_id"]

    def boom(self):
        raise RuntimeError("شبیه‌سازی خطای میانه‌ی پرداخت (سینک کیف)")

    monkeypatch.setattr(models.Student, "sync_wallet_balance", boom)
    with pytest.raises(RuntimeError):
        pay_installment_manually(world, installment_id)
    world.db.rollback()
    monkeypatch.undo()

    row = installment_row(world.db, installment_id)
    assert (row.is_paid, row.paid_amount or 0) == (False, 0), "فلیپ is_paid/paid_amount نباید بماند"
    assert fresh(world.db, world.enrollment).total_paid == 200, "total_paid نباید نیمه‌تغییر کند"
    assert wallets(world.db) == (0, 0, 0), "کیف نباید شارژ نیمه‌کاره داشته باشد"
    assert deposit_transactions(world.db) == [], "رسید ناقص نباید باقی بماند"
    assert world.db.query(models.TransactionInstallmentAllocation).count() == 0
    assert enrollment_debt(world.db) == 800, "بدهی نباید تغییر ناقص داشته باشد"


def test_s23b_failure_after_ledger_rows_still_rolls_back(world, monkeypatch):
    """خطا در آخرین قدم (بعد از ساخت رسید و ردیف ledger، قبل از کامیت) هم باید کاملاً برگردد."""
    installment_id = create_installment(world, amount=100, due_date="1405/07/01")["installment_id"]

    class BoomActivityLog:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("شبیه‌سازی خطای لاگ حسابرسی در آخرین قدم")

    monkeypatch.setattr(finance, "ActivityLog", BoomActivityLog)
    with pytest.raises(RuntimeError):
        pay_installment_manually(world, installment_id)
    world.db.rollback()
    monkeypatch.undo()

    row = installment_row(world.db, installment_id)
    assert (row.is_paid, row.paid_amount or 0) == (False, 0)
    assert deposit_transactions(world.db) == [], "رسید ساخته‌شده نباید کامیت شده باشد"
    assert world.db.query(models.TransactionInstallmentAllocation).count() == 0
    assert wallets(world.db) == (0, 0, 0)
    assert fresh(world.db, world.enrollment).total_paid == 200


# ==========================================
# سناریو ۲۴ — دو پرداخت هم‌زمان روی یک قسط (SQLite فایلی)
# ==========================================
def test_s24_concurrent_manual_payments_settle_exactly_once(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'installment-race.sqlite'}")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        seed_world(db)
        installment_id = finance.create_installment(
            InstallmentCreateRequest(enrollment_id=1, amount=100, due_date=TODAY_JALALI),
            db=db, authorization=f"Bearer {TOKEN}", _="admin",
        )["installment_id"]

    barrier = Barrier(2)

    def attempt(_):
        with factory() as db:
            barrier.wait(timeout=20)
            try:
                finance.pay_installment_manually(installment_id, db=db, _="admin",
                                                payment_method="نقدی", authorization=f"Bearer {TOKEN}")
                return 200
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(attempt, range(2)))

    with factory() as db:
        assert sorted(statuses)[0] == 200, f"یکی باید موفق شود؛ وضعیت‌ها: {statuses}"
        assert sorted(statuses)[1] in (400, 409), f"دومی باید رد شود (۴۰۰/۴۰۹)؛ شد {statuses}"
        row = installment_row(db, installment_id)
        assert (row.is_paid, row.paid_amount) == (True, 100), "پوشش نباید دوباره/دوتایی ثبت شود"
        assert db.get(models.Student, 101).wallet_institute == 100, "کیف فقط یک‌بار شارژ شود"
        deposit_rows = db.query(models.Transaction).filter(models.Transaction.type == "deposit").all()
        assert len(deposit_rows) == 1 and deposit_rows[0].amount == 100
        assert db.get(models.Enrollment, 1).total_paid == 300, "total_paid فقط یک‌بار افزایش یابد"
    engine.dispose()


# ==========================================
# یافته‌های ممیزی (عمداً fail — طبق دستور تسک هیچ fix‌ای انجام نشده)
# ==========================================
def test_finding_t1_enrollment_installments_skip_validation(world):
    """🔎 F-T1: مسیر «ثبت‌نام همراه با اقساط» (`classes.add_enrollment` → schemas.InstallmentCreate)
    هیچ اعتبارسنجی‌ای روی مبلغ/تاریخ قسط ندارد، در حالی که اندپوینت اختصاصی
    `POST /finance/installments` همان ورودی‌ها را با ۴۲۲ رد می‌کند ⇒ سیاست ناهمگون و امکان ساخت
    قسط با مبلغ ≤ ۰ یا تاریخ نامعتبر (که بعداً از مسیر وصول با ۴۰۰ رد می‌شود و در گزارش‌ها
    به‌شکل «در انتظار» گیر می‌کند)."""
    result = add_enrollment(world, course_id=2, total_tuition=1000, installments=[
        InstallmentCreate(amount=-5, due_date="bad-date"),
        InstallmentCreate(amount=0, due_date="1405/13/45"),
    ])
    rows = world.db.query(models.Installment).filter(
        models.Installment.enrollment_id == result["enrollment_id"]).all()
    created = sorted((r.amount, r.due_date) for r in rows)
    assert created == [], (
        f"F-T1: انتظار می‌رفت اقساط نامعتبر (مبلغ ≤۰ یا تاریخ نامعتبر) ساخته نشوند؛ "
        f"ساخته‌شده‌ها: {created}"
    )


def test_finding_t2_regex_accepts_calendar_invalid_jalali_dates(world):
    """🔎 F-T2: الگوی اعتبارسنجی `due_date` در `InstallmentCreateRequest` فقط «شکل» تاریخ را چک می‌کند
    (`\\d{4}/MM/DD` با DD تا ۳۱)، پس تاریخ‌های ناموجود جلالی مثل ۳۱ ماه‌های ۷ تا ۱۲ (که ۳۰ روزه‌اند)
    یا ۳۰ اسفند سال غیرکبیسه پذیرفته می‌شوند؛ `parse_project_date` بعداً آن‌ها را None می‌کند،
    پس وضعیت قسط همیشه «در انتظار» می‌ماند و هیچ یادآوری معوقه‌ای فعال نمی‌شود."""
    for bogus in ("1405/07/31", "1405/12/30"):
        try:
            request = InstallmentCreateRequest(enrollment_id=1, amount=10, due_date=bogus)
        except ValidationError:
            continue   # رفتار مطلوب
        result = create_installment(world, amount=10, due_date=request.due_date)
        row = installment_row(world.db, result["installment_id"])
        assert row is None, (
            f"F-T2: تاریخ ناموجود {bogus!r} پذیرفته و قسط ساخته شد "
            f"(parse_project_date آن None است ⇒ وضعیت «در انتظار»/بدون یادآوری)"
        )
