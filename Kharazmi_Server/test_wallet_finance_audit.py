"""
Wallet / Internal Payment / Refund / Balance-Consistency — TEST-ONLY audit
(فقط تست؛ هیچ تغییری در کد اصلی پروژه انجام نشده است)

## Business rules تحت آزمون
- `wallet_teacher` مثبت = اعتبار نزد معلم | منفی = بدهی به معلم
- `wallet_institute` مثبت = اعتبار نزد آموزشگاه | منفی = بدهی به آموزشگاه
- صفر = تسویه
- **invariant همیشگی:** `wallet_balance == wallet_teacher + wallet_institute`

## نگاشت سناریوهای درخواستی ← تست‌ها
| # | سناریو | تست |
|---|--------|-----|
| ۱ | موجودی اولیه صفر | `test_s01_initial_wallets_are_zero` |
| ۲ | ثبت جلسه ۱۰۰ ⇒ ‎-۱۰۰ | `test_s02_session_charge_100_makes_minus_100` |
| ۳ | پرداخت ۴۰ ⇒ ‎-۶۰ | `test_s03_payment_40_moves_debt_from_100_to_60` |
| ۴ | پرداخت ۶۰ ⇒ ۰ | `test_s04_payment_60_settles_to_zero` |
| ۵ | پرداخت ۱۰۰ بعد از تسویه ⇒ ‎+۱۰۰ | `test_s05_payment_after_settlement_goes_positive` |
| ۶ | refund همان ۱۰۰ ⇒ ۰ | `test_s06_refund_returns_balance_to_zero` |
| ۷ | پرداخت فقط teacher | `test_s07_teacher_only_payment_touches_only_teacher_wallet` |
| ۸ | پرداخت فقط institute | `test_s08_institute_only_payment_touches_only_institute_wallet` |
| ۹ | پرداخت both ⇒ جمع سهم‌ها = مبلغ | `test_s09_split_payment_shares_sum_exactly_to_amount` |
| ۱۰ | مبلغ ۰/منفی/نامعتبر قبل از هر نوشتن رد شود | `test_s10_invalid_amounts_rejected_before_any_write` |
| ۱۱ | refund تکراری بی‌اثر | `test_s11_duplicate_refund_is_rejected_and_changes_nothing` |
| ۱۲ | deleted/reversed در گزارش درآمد و نمای فعال | `test_s12_*` |
| ۱۳ | invariant بعد از هر سناریو | `assert_wallet_invariant` (در همه‌ی تست‌ها) + `test_s13_full_walk_invariant_every_step` |
| ۱۴ | lost update در پرداخت هم‌زمان / bulk update | `test_s14a_*`, `test_s14b_*`, `test_s14c_*` |

## ⚠️ تست‌های یافته‌محور (عمداً fail می‌شوند)
سه تست با نام `test_finding_fw1a_*` / `test_finding_fw1b_*` / `test_finding_fw2_*` برای **مستندسازی
نقص‌های واقعی** نوشته شده‌اند و انتظار می‌رود fail شوند (اگر روزی فیکس شوند، XPASS/سبز می‌شوند و
باید نامشان از `finding` به تست رگرسیون عادی تغییر کند). جزئیات در گزارش/چک‌پوینت همین تسک.

## اجرا (طبق قانون پروژه: فقط روی DB تست/کپی — هرگز gaj_db.db واقعی)
    cd /home/user/KharazmiApp && DATABASE_URL=sqlite:////tmp/wallet_audit.db \
        PYTHONPATH=/home/user/KharazmiApp/Kharazmi_Server \
        python3 -m pytest Kharazmi_Server/test_wallet_finance_audit.py -q
تست‌ها DB درون‌حافظه‌ای/فایل موقت خودشان را می‌سازند (StaticPool / tmp_path).
"""
import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from financial_calculations import (
    calculate_institute_collected_revenue,
    calculate_student_debt,
    calculate_total_turnover,
)
from routers import attendance, finance
from schemas import AttendanceItem, AttendanceSubmitData, FinanceSubmitData

# سقف ایمنی: هر تست باید کوچک و قابل‌اتکا بمانَد
TODAY_JALALI = "1405/06/16"      # گذشته‌ی معتبر نسبت به امروز (۱۴۰۵/۰۶/۲۶)
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


def seed_world(db):
    """دانش‌آموز با کیف صفر + کلاس با نرخ جلسه ۶۰ و سهم آموزشگاه ۴۰ ⇒ شارژ هر جلسه دقیقاً ۱۰۰."""
    db.add_all([models.Branch(id=1, name="شعبه تست", active=True)])
    db.flush()
    user = models.User(id=1, username="wallet-admin", password="unused", role="admin", sub_role="admin", branch_id=1)
    teacher = models.Teacher(id=1, teacher_code=101, first_name="معلم", last_name="تست",
                             mobile="09120000101", branch_id=1)
    student = models.Student(
        id=101, student_code=100101, first_name="دانش‌آموز", last_name="تست",
        national_code="W-101", student_mobile="09121110101", parent_mobile="09122220101",
        branch_id=1, wallet_teacher=0, wallet_institute=0, wallet_balance=0,
    )
    db.add_all([user, teacher, student])
    db.flush()
    course = models.Course(
        id=1, title="کلاس تست", code="W10001", teacher_id=teacher.id, branch_id=1,
        grade_level="دهم", teacher_session_price=60, is_admin_approved=True,
    )
    db.add(course)
    db.flush()
    enrollment = models.Enrollment(
        student_id=student.id, course_id=course.id, branch_id=1,
        total_tuition=1000, total_paid=0, register_date=TODAY_JALALI,
    )
    db.add_all([
        enrollment,
        models.UserSession(token="wallet-admin-token", user_id=user.id, sub_role="admin",
                           created_at=datetime.datetime.now()),
        models.InstituteSettings(name="آموزشگاه تست", address="ت", phone="021", card_number="1234"),
        # سهم آموزشگاه برای ۱ نفر = ۴۰ (جمع با ۶۰ معلم = ۱۰۰)
        models.InstituteShare(count_1=40, count_2=80, count_3=120),
    ])
    db.commit()
    return SimpleNamespace(db=db, user=user, teacher=teacher, student=student, course=course,
                           enrollment=enrollment)


@pytest.fixture
def world():
    """DB درون‌حافظه‌ای اختصاصی هر تست — هیچ فایلی از پروژه خوانده/نوشته نمی‌شود."""
    engine = make_engine(poolclass=StaticPool)
    with sessionmaker(bind=engine, expire_on_commit=False)() as db:
        yield seed_world(db)
    models.Base.metadata.drop_all(engine)
    engine.dispose()


# ---------- helpers با assert خودکار invariant (سناریو ۱۳) ----------
def wallets(db, student_id=101):
    """خواندن تازه از DB (نه از حافظه‌ی ORM) تا مقدار واقعیِ ذخیره‌شده سنجیده شود."""
    db.expire_all()
    student = db.get(models.Student, student_id)
    return student.wallet_teacher or 0, student.wallet_institute or 0, student.wallet_balance or 0


def assert_wallet_invariant(db, student_id=101, expected_teacher=None, expected_institute=None,
                            expected_balance=None, context=""):
    """invariant مرکزی: wallet_balance == wallet_teacher + wallet_institute (سناریو ۱۳)."""
    teacher, institute, balance = wallets(db, student_id)
    assert balance == teacher + institute, (
        f"نقض invariant {context}: balance={balance} != teacher({teacher}) + institute({institute})"
    )
    if expected_teacher is not None:
        assert teacher == expected_teacher, f"{context}: wallet_teacher={teacher} ≠ {expected_teacher}"
    if expected_institute is not None:
        assert institute == expected_institute, f"{context}: wallet_institute={institute} ≠ {expected_institute}"
    if expected_balance is not None:
        assert balance == expected_balance, f"{context}: wallet_balance={balance} ≠ {expected_balance}"
    return teacher, institute, balance


def pay(world, amount, wallet="institute", **overrides):
    values = dict(student_id=world.student.id, amount=amount, target_wallet=wallet,
                  description="پرداخت تستی", payment_method="نقدی", date=TODAY_JALALI)
    values.update(overrides)
    result = finance.submit_payment(FinanceSubmitData(**values), db=world.db, _="admin",
                                    authorization="Bearer wallet-admin-token")
    assert_wallet_invariant(world.db, context="بعد از پرداخت")
    return result


def submit_session(world, date=TODAY_JALALI):
    request = AttendanceSubmitData(course_id=world.course.id, date=date,
                                   items=[AttendanceItem(student_id=world.student.id, status="Present")])
    result = attendance.submit_session_and_calculate(request, db=world.db,
                                                     authorization="Bearer wallet-admin-token",
                                                     sub_role="admin")
    assert_wallet_invariant(world.db, context="بعد از ثبت جلسه")
    return result


def refund(world, transaction_id):
    result = finance.refund_transaction(transaction_id, db=world.db,
                                        authorization="Bearer wallet-admin-token", _="admin")
    assert_wallet_invariant(world.db, context="بعد از استرداد")
    return result


def deposit_count(db):
    return db.query(models.Transaction).filter(models.Transaction.type == "deposit").count()


def receipt(db, amount=100, **overrides):
    """رسید مستقیم، فقط برای ساختن حالت‌های پرچمی (deleted/reversed) در سناریو ۱۲."""
    values = dict(student_id=101, enrollment_id=1, course_id=1, branch_id=1, amount=amount,
                  payment_method="نقدی", type="deposit", target_wallet="institute",
                  date=TODAY_JALALI, description="رسید تستی", share_teacher=0, share_institute=amount)
    values.update(overrides)
    transaction = models.Transaction(**values)
    db.add(transaction)
    db.flush()
    return transaction


# ==========================================
# سناریو ۱ — موجودی اولیه
# ==========================================
def test_s01_initial_wallets_are_zero(world):
    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=0, expected_balance=0,
                            context="موجودی اولیه")
    # صفر = تسویه: بدهی قراردادی صفر است (شهریه ۱۰۰۰ - پرداخت ۰ → بدهی ۱۰۰۰ طبق ثبت‌نام)
    assert calculate_student_debt(world.db, world.student) == 1000
    assert world.db.query(models.Transaction).count() == 0


# ==========================================
# سناریو ۲ — ثبت جلسه با مبلغ ۱۰۰
# ==========================================
def test_s02_session_charge_100_makes_minus_100(world):
    submit_session(world)
    teacher, institute, balance = assert_wallet_invariant(
        world.db, expected_teacher=-60, expected_institute=-40, expected_balance=-100,
        context="شارژ جلسه",
    )
    assert teacher + institute == -100, "مجموع دو کیف باید دقیقاً -100 باشد"
    charge = world.db.query(models.Transaction).filter(models.Transaction.type == "session_charge").one()
    assert charge.amount == -100
    assert charge.share_teacher == 60 and charge.share_institute == 40
    # علامت منفی = بدهی دانش‌آموز
    assert balance < 0


# ==========================================
# سناریو ۳ و ۴ — پرداخت ۴۰ سپس ۶۰
# ==========================================
def test_s03_payment_40_moves_debt_from_100_to_60(world):
    submit_session(world)
    pay(world, 40, wallet="institute")
    assert_wallet_invariant(world.db, expected_teacher=-60, expected_institute=0, expected_balance=-60,
                            context="پرداخت ۴۰")


def test_s04_payment_60_settles_total_balance_to_zero(world):
    """سناریوی ۳+۴ درخواست: بدهی کل -۱۰۰ → پرداخت ۴۰ → -۶۰ → پرداخت ۶۰ → صفر.
    نکته‌ی دقیق سیستم: پرداخت‌ها به کیف انتخاب‌شده می‌روند؛ «تسویه» در سطح
    جمعِ دو کیف معنا دارد (wallet_balance=0) و ممکن است یک کیف بستانکار بماند."""
    submit_session(world)
    pay(world, 40, wallet="institute")
    assert_wallet_invariant(world.db, expected_teacher=-60, expected_institute=0, expected_balance=-60,
                            context="بعد از پرداخت ۴۰")

    pay(world, 60, wallet="institute")
    teacher, institute, balance = assert_wallet_invariant(
        world.db, expected_teacher=-60, expected_institute=60, expected_balance=0,
        context="بعد از پرداخت ۶۰ (تسویه در سطح جمع)",
    )
    assert balance == 0, "جمع دو کیف باید صفر (تسویه) شود"
    assert teacher + institute == balance


def test_s04b_settling_both_wallets_to_exactly_zero(world):
    """تسویه‌ی دقیق هر دو کیف: ۴۰ به آموزشگاه (بدهی آموزشگاه ۴۰-) و ۶۰ به معلم (بدهی معلم ۶۰-)."""
    submit_session(world)
    pay(world, 40, wallet="institute")
    pay(world, 60, wallet="teacher")
    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=0, expected_balance=0,
                            context="تسویه‌ی دقیق دو کیف")


# ==========================================
# سناریو ۵ و ۶ — پرداخت بعد از تسویه و استرداد
# ==========================================
def test_s05_payment_after_settlement_goes_positive(world):
    pay(world, 100, wallet="institute")            # موجودی صفر بود؛ پرداخت ۱۰۰ ⇒ اعتبار
    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=100, expected_balance=100,
                            context="پرداخت بعد از تسویه")
    assert wallets(world.db)[2] > 0, "مقدار مثبت = اعتبار نزد آموزشگاه"


def test_s06_refund_returns_balance_to_zero(world):
    deposit_tx = pay(world, 100, wallet="institute")["receipt_id"]
    assert_wallet_invariant(world.db, expected_balance=100, context="قبل از استرداد")

    refund(world, deposit_tx)
    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=0, expected_balance=0,
                            context="بعد از استرداد")

    original = world.db.get(models.Transaction, deposit_tx)
    reversal = world.db.query(models.Transaction).filter(models.Transaction.type == "reversal").one()
    assert original.is_reversed is True
    assert reversal.amount == -100 and reversal.target_wallet == "institute"
    assert reversal.remittance_number != original.remittance_number, "شماره‌ی حواله‌ی استرداد نباید تکرار شود"


# ==========================================
# سناریو ۷ و ۸ — تک‌کیفی
# ==========================================
def test_s07_teacher_only_payment_touches_only_teacher_wallet(world):
    pay(world, 70, wallet="teacher")
    assert_wallet_invariant(world.db, expected_teacher=70, expected_institute=0, expected_balance=70,
                            context="پرداخت فقط معلم")
    transactions = world.db.query(models.Transaction).all()
    assert len(transactions) == 1 and transactions[0].target_wallet == "teacher"


def test_s08_institute_only_payment_touches_only_institute_wallet(world):
    pay(world, 30, wallet="institute")
    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=30, expected_balance=30,
                            context="پرداخت فقط آموزشگاه")
    transactions = world.db.query(models.Transaction).all()
    assert len(transactions) == 1 and transactions[0].target_wallet == "institute"


# ==========================================
# سناریو ۹ — پرداخت both
# ==========================================
@pytest.mark.parametrize("amount", [100, 101, 999, 1001])
def test_s09_split_payment_shares_sum_exactly_to_amount(world, amount):
    pay(world, amount, wallet="both")
    receipts_ = world.db.query(models.Transaction).filter(models.Transaction.type == "deposit").all()
    assert len(receipts_) == 2, "پرداخت both باید دو رسید (هر کیف یکی) ثبت کند"
    teacher_share = sum(t.amount for t in receipts_ if t.target_wallet == "teacher")
    institute_share = sum(t.amount for t in receipts_ if t.target_wallet == "institute")
    assert teacher_share + institute_share == amount, "جمع دو سهم باید دقیقاً برابر مبلغ پرداخت باشد"
    assert_wallet_invariant(world.db, expected_teacher=teacher_share, expected_institute=institute_share,
                            expected_balance=amount, context=f"تقسیم both برای {amount}")


def test_s09b_explicit_split_is_not_reinterpreted(world):
    pay(world, 500, wallet="both", amount_teacher=200, amount_institute=300)
    assert_wallet_invariant(world.db, expected_teacher=200, expected_institute=300, expected_balance=500,
                            context="تقسیم صریح")


# ==========================================
# سناریو ۱۰ — مبالغ نامعتبر: رد قبل از هر نوشتن
# ==========================================
@pytest.mark.parametrize("case", [
    dict(amount=0, wallet="institute"),                       # صفر
    dict(amount=-50, wallet="institute"),                     # منفی
    dict(amount=0, wallet="teacher"),                         # صفر (کیف معلم)
    dict(amount=0, wallet="both"),                            # صفر در حالت both
    dict(amount=100, wallet="legacy"),                        # کیف نامعتبر (M12)
    dict(amount=100, wallet="both", amount_teacher=-10, amount_institute=110),   # سهم منفی
    dict(amount=100, wallet="both", amount_teacher=None, amount_institute=100),  # تقسیم ناقص
])
def test_s10_invalid_amounts_rejected_before_any_write(world, case):
    before_tx = world.db.query(models.Transaction).count()
    before_wallets = wallets(world.db)
    before_sequence = world.db.query(models.SequenceCounter).count()

    with pytest.raises(HTTPException) as error:
        pay(world, case["amount"], wallet=case["wallet"],
            **{k: v for k, v in case.items() if k.startswith("amount_")})

    assert error.value.status_code == 400, f"انتظار 400 برای {case}، دریافت {error.value.status_code}"
    world.db.rollback()
    assert world.db.query(models.Transaction).count() == before_tx, "هیچ تراکنشی نباید ثبت شود"
    assert wallets(world.db) == before_wallets, "هیچ کیف پولی نباید تغییر کند"
    assert world.db.query(models.SequenceCounter).count() == before_sequence, "شمارنده‌ها نباید مصرف شوند"
    assert_wallet_invariant(world.db, context="بعد از رد شدن پرداخت نامعتبر")


def test_s10c_null_wallet_is_rejected_at_schema_level(world):
    """کیف None به‌جای رسیدن به منطق پول، همان‌جا در اعتبارسنجی schema رد می‌شود (زودتر از هر نوشتن)."""
    from pydantic import ValidationError

    before_tx = world.db.query(models.Transaction).count()
    before_wallets = wallets(world.db)
    with pytest.raises(ValidationError):
        finance.submit_payment(
            FinanceSubmitData(student_id=101, amount=100, target_wallet=None,
                              description="کیف نامعتبر", payment_method="نقدی", date=TODAY_JALALI),
            db=world.db, _="admin", authorization="Bearer wallet-admin-token",
        )
    world.db.rollback()
    assert world.db.query(models.Transaction).count() == before_tx
    assert wallets(world.db) == before_wallets
    assert_wallet_invariant(world.db, context="بعد از رد شدن کیف None")


def test_s10b_invalid_amount_leaves_previous_debt_untouched(world):
    """پرداخت نامعتبر روی بدهی موجود: بدهی دقیقاً همان -۱۰۰ قبلی می‌ماند."""
    submit_session(world)
    with pytest.raises(HTTPException) as error:
        pay(world, 0, wallet="institute")
    assert error.value.status_code == 400
    world.db.rollback()
    assert_wallet_invariant(world.db, expected_teacher=-60, expected_institute=-40, expected_balance=-100,
                            context="بعد از تلاش پرداخت صفر")


# ==========================================
# سناریو ۱۱ — استرداد تکراری
# ==========================================
def test_s11_duplicate_refund_is_rejected_and_changes_nothing(world):
    deposit_tx = pay(world, 100, wallet="institute")["receipt_id"]
    refund(world, deposit_tx)
    snapshot = wallets(world.db)
    tx_count = world.db.query(models.Transaction).count()

    with pytest.raises(HTTPException) as error:
        refund(world, deposit_tx)

    assert error.value.status_code == 400, "استرداد دوم باید 400 بدهد"
    world.db.rollback()
    assert wallets(world.db) == snapshot, "استرداد تکراری نباید هیچ تغییر مالی بسازد"
    assert world.db.query(models.Transaction).count() == tx_count, "ردیف معکوس دوم نباید ثبت شود"
    assert world.db.query(models.Transaction).filter(models.Transaction.type == "reversal").count() == 1
    assert_wallet_invariant(world.db, expected_balance=0, context="بعد از استرداد تکراری")


def test_s11b_refund_of_session_charge_is_rejected(world):
    """شارژ جلسه مسیر استرداد عمومی ندارد (M16) — کیف نباید دست بخورد."""
    submit_session(world)
    charge = world.db.query(models.Transaction).filter(models.Transaction.type == "session_charge").one()
    with pytest.raises(HTTPException) as error:
        refund(world, charge.id)
    assert error.value.status_code == 400
    world.db.rollback()
    assert_wallet_invariant(world.db, expected_balance=-100, context="بعد از رد استرداد شارژ جلسه")
    assert world.db.get(models.Transaction, charge.id).is_reversed is False


# ==========================================
# سناریو ۱۲ — تراکنش‌های deleted/reversed
# ==========================================
def test_s12a_inactive_receipts_are_excluded_from_revenue_reports(world):
    receipt(world.db, amount=100)                                        # فعال ⇒ باید شمرده شود
    receipt(world.db, amount=100, is_deleted=True)                       # حذف‌شده
    receipt(world.db, amount=100, is_reversed=True)                      # برگشت‌خورده
    receipt(world.db, amount=-100, type="reversal")                      # ردیف معکوس (منفی)
    world.db.commit()

    institute_revenue = calculate_institute_collected_revenue(world.db, RANGE_START, RANGE_END)
    turnover = calculate_total_turnover(world.db, RANGE_START, RANGE_END)
    assert institute_revenue == 100, f"درآمد وصول‌شده باید فقط رسید فعال را بشمارد (شد {institute_revenue})"
    assert turnover == 100, f"گردش مالی باید فقط رسید فعال را بشمارد (شد {turnover})"


def test_s12b_refunded_payment_has_no_net_effect_on_active_revenue(world):
    deposit_tx = pay(world, 150, wallet="institute")["receipt_id"]
    assert calculate_institute_collected_revenue(world.db, RANGE_START, RANGE_END) == 150

    refund(world, deposit_tx)
    assert calculate_institute_collected_revenue(world.db, RANGE_START, RANGE_END) == 0, (
        "پس از استرداد، نه اصل رسید (is_reversed) و نه ردیف معکوس نباید در درآمد فعال بمانند"
    )
    assert calculate_total_turnover(world.db, RANGE_START, RANGE_END) == 0


def test_s12c_active_transactions_view_hides_reversed_rows(world):
    """نمای فعال تراکنش‌های دانش‌آموز: ردیف برگشت‌خورده/حذف‌شده نباید دیده شود."""
    active = pay(world, 100, wallet="institute")["receipt_id"]
    refund(world, active)

    rows = finance.get_student_physical_transactions(
        world.student.id, db=world.db, authorization="Bearer wallet-admin-token", _role="admin",
    )
    ids = {row["id"] for row in rows}
    assert active not in ids, "رسید برگشت‌خورده در نمای فعال نباید باشد"
    for row in rows:
        assert row["is_reversed"] is False
    assert_wallet_invariant(world.db, expected_balance=0, context="نمای فعال بعد از استرداد")


def test_s12d_reversed_session_charge_returns_wallet_to_baseline(world):
    """حذف/برگشت جلسه: کیف به حالت اول برمی‌گردد و گزارش درآمد صفر می‌ماند."""
    from dependencies import reverse_session_financial_impacts

    result = submit_session(world)
    assert_wallet_invariant(world.db, expected_balance=-100, context="بعد از شارژ جلسه")

    reverse_session_financial_impacts(result["session_id"], world.db)
    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=0, expected_balance=0,
                            context="بعد از برگشت جلسه")
    charge = world.db.query(models.Transaction).filter(models.Transaction.type == "session_charge").one()
    assert charge.is_deleted is True
    assert calculate_total_turnover(world.db, RANGE_START, RANGE_END) == 0


# ==========================================
# سناریو ۱۳ — invariant در کل مسیر
# ==========================================
def test_s13_full_walk_invariant_every_step(world):
    """مسیر کامل؛ **بلافاصله بعد از هر گام** مقدار مورد انتظار و invariant بررسی می‌شود."""
    def check(label, expected_teacher, expected_institute, expected_balance):
        teacher, institute, balance = wallets(world.db)
        assert (teacher, institute, balance) == (expected_teacher, expected_institute, expected_balance), (
            f"گام «{label}»: انتظار {(expected_teacher, expected_institute, expected_balance)} "
            f"واقعی {(teacher, institute, balance)}"
        )
        assert balance == teacher + institute, f"نقض invariant در گام «{label}»"
        assert_wallet_invariant(world.db, context=label)

    submit_session(world)                                              # شارژ جلسه ۱۰۰
    check("شارژ جلسه ۱۰۰", -60, -40, -100)

    pay(world, 40, wallet="institute")                                 # پرداخت جزئی
    check("پرداخت ۴۰ به آموزشگاه", -60, 0, -60)

    pay(world, 60, wallet="both", amount_teacher=30, amount_institute=30)
    check("پرداخت تقسیمی ۶۰", -30, 30, 0)

    split_ids = pay(world, 500, wallet="both")["receipt_ids"]           # پرداخت ۵۰۰ (۲۵۰/۲۵۰)
    check("پرداخت ۵۰۰ (both)", 220, 280, 500)

    for receipt_id in split_ids:                                        # استرداد کامل هر دو رسید
        refund(world, receipt_id)
    check("استرداد کامل پرداخت ۵۰۰", -30, 30, 0)


# ==========================================
# سناریو ۱۴ — هم‌زمانی و lost update
# ==========================================
def test_s14a_concurrent_payments_do_not_lose_updates(tmp_path):
    """سه پرداخت هم‌زمان از سه اتصال مستقل: هیچ پرداختی نباید گم شود (UPDATE اتمیک، بدون RMW)."""
    engine = make_engine(f"sqlite:///{tmp_path / 'wallet-concurrency.sqlite'}")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        seed_world(db)

    barrier = Barrier(3)

    def do_payment(_):
        with factory() as db:
            barrier.wait(timeout=20)
            try:
                finance.submit_payment(
                    FinanceSubmitData(student_id=101, amount=100, target_wallet="institute",
                                      description="پرداخت هم‌زمان", payment_method="نقدی", date=TODAY_JALALI),
                    db=db, _="admin", authorization="Bearer wallet-admin-token",
                )
                return 200
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=3) as pool:
        statuses = list(pool.map(do_payment, range(3)))

    with factory() as db:
        teacher, institute, balance = wallets(db)
        assert statuses == [200, 200, 200], f"هر سه پرداخت باید موفق شوند؛ وضعیت‌ها: {statuses}"
        assert institute == 300, f"lost update: انتظار 300، دریافت {institute}"
        assert balance == teacher + institute == 300
        assert db.query(models.Transaction).filter(models.Transaction.type == "deposit").count() == 3
    engine.dispose()


def test_s14b_concurrent_split_payments_keep_sum_consistent(tmp_path):
    """پرداخت‌های هم‌زمان both: هم جمع سهم‌ها و هم invariant باید حفظ شود."""
    engine = make_engine(f"sqlite:///{tmp_path / 'wallet-concurrency-split.sqlite'}")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        seed_world(db)

    barrier = Barrier(2)

    def do_split(_):
        with factory() as db:
            barrier.wait(timeout=20)
            finance.submit_payment(
                FinanceSubmitData(student_id=101, amount=101, target_wallet="both",
                                  description="تقسیمی هم‌زمان", payment_method="نقدی", date=TODAY_JALALI),
                db=db, _="admin", authorization="Bearer wallet-admin-token",
            )
            return 200

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(do_split, range(2)))

    with factory() as db:
        teacher, institute, balance = wallets(db)
        assert statuses == [200, 200]
        # هر پرداخت ۱۰۱ ⇒ ۵۰+۵۱؛ دو پرداخت ⇒ ۱۰۰+۱۰۲ (ترتیب سهم‌ها ثابت است)
        assert teacher + institute == 202, f"جمع سهم‌ها باید 202 باشد، شد {teacher + institute}"
        assert balance == teacher + institute
        receipts_ = db.query(models.Transaction).filter(models.Transaction.type == "deposit").all()
        assert sum(t.amount for t in receipts_) == 202
    engine.dispose()


def test_s14c_production_bulk_update_keeps_invariant_and_survives_stale_writer(tmp_path):
    """bulk update کیف (الگوی پروداکشن: UPDATE خام + refresh + sync) نباید هیچ اثری گم کند،
    و یک سشن دیگر با آبجکت کهنه که فقط فیلد نامرتبط را می‌نویسد نباید کیف‌ها را برگرداند."""
    engine = make_engine(f"sqlite:///{tmp_path / 'wallet-bulk.sqlite'}")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        seed_world(db)

    stale_db = factory()
    stale_db.get(models.Student, 101)          # خواندن کهنه (۰/۰/۰) پیش از پرداخت

    other_db = factory()
    other_db.query(models.Student).filter(models.Student.id == 101).update(
        {models.Student.wallet_institute: func.coalesce(models.Student.wallet_institute, 0) + 100},
        synchronize_session=False,
    )
    # دقیقاً همان کاری که اندپوینت‌های پول انجام می‌دهند: refresh + سینک کل
    writer_student = other_db.get(models.Student, 101)
    other_db.refresh(writer_student)
    writer_student.sync_wallet_balance()
    other_db.commit()
    other_db.close()

    with factory() as db:                      # invariant باید بعد از bulk update برقرار باشد
        teacher, institute, balance = wallets(db)
        assert (institute, balance) == (100, 100), (
            f"bulk update + sync باید جمع را 100 کند (شد institute={institute}, balance={balance})"
        )
        assert balance == teacher + institute

    stale_student = stale_db.get(models.Student, 101)
    stale_student.first_name = "نام جدید"       # نوشتن فیلد نامرتبط با آبجکت کهنه
    stale_db.commit()
    stale_db.close()

    with factory() as db:
        teacher, institute, balance = wallets(db)
        assert institute == 100, f"کیف آموزشگاه باید 100 بماند (نشد {institute}) — ریسک lost update"
        assert balance == teacher + institute == 100, (
            f"نقض invariant پس از کامیت سشن کهنه: balance={balance} != {teacher}+{institute}"
        )
    engine.dispose()


def test_s14d_counterfactual_read_modify_write_would_lose_update(tmp_path):
    """شاهدِ ریسک (فقط برای سنجش شدت — کد اصلی این الگو را استفاده نمی‌کند):
    اگر به‌جای UPDATE اتمیک، الگوی «بخوان-جمع-بنویس» در پایتون استفاده شود،
    پرداخت دوم مقدار پرداخت اول را پاک می‌کند."""
    engine = make_engine(f"sqlite:///{tmp_path / 'wallet-rmw.sqlite'}")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        seed_world(db)

    with factory() as db:
        student = db.get(models.Student, 101)
        read_teacher, read_institute = student.wallet_teacher, student.wallet_institute  # خواندن ۱

        with factory() as db2:  # «پرداخت موازی» که بین خواندن و نوشتن کامیت می‌شود
            db2.query(models.Student).filter(models.Student.id == 101).update(
                {models.Student.wallet_institute: func.coalesce(models.Student.wallet_institute, 0) + 100},
                synchronize_session=False,
            )
            db2.commit()

        # نوشتن کور با مقدار قدیمی ← همان چیزی که طراحی اتمیک فعلی از آن جلوگیری می‌کند
        student.wallet_institute = read_institute + 100
        student.sync_wallet_balance()
        db.commit()

    with factory() as db:
        institute = wallets(db)[1]
        assert institute == 100, (
            f"الگوی RMW به‌صورت مورد انتظار یک پرداخت را از دست داد (شد {institute}) — "
            "این تست ارزش UPDATE اتمیک فعلی را مستند می‌کند"
        )
    engine.dispose()


# ==========================================
# قواعد کسب‌وکار: معنای علامت کیف
# ==========================================
def test_business_rule_signs_and_settlement_semantics(world):
    # منفی = بدهی دانش‌آموز
    submit_session(world)
    assert_wallet_invariant(world.db, expected_teacher=-60, expected_institute=-40, expected_balance=-100,
                            context="بدهی")
    assert wallets(world.db)[2] < 0, "منفی = بدهی دانش‌آموز"

    # صفر = تسویه (هر دو کیف دقیقاً صفر)
    pay(world, 60, wallet="teacher")
    pay(world, 40, wallet="institute")
    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=0, expected_balance=0,
                            context="تسویه")
    assert wallets(world.db)[2] == 0, "صفر = تسویه"

    # مثبت = اعتبار، و فقط همان کیفی که پول گرفته تغییر می‌کند
    pay(world, 250, wallet="teacher")
    teacher, institute, balance = wallets(world.db)
    assert balance == 250 > 0, "مثبت = اعتبار"
    assert (teacher, institute) == (250, 0), "اعتبار فقط نزد همان کیفی که پرداخت شده"
    assert_wallet_invariant(world.db, expected_balance=250, context="اعتبار")


def test_business_rule_invariant_holds_for_legacy_null_wallets():
    """ستون‌های nullable: مقدار None باید مثل صفر رفتار کند و invariant نشکند."""
    engine = make_engine(poolclass=StaticPool)
    try:
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            world = seed_world(db)
            student = db.get(models.Student, 101)
            student.wallet_teacher = None
            student.wallet_institute = None
            db.commit()
            teacher, institute, balance = wallets(db)
            assert (teacher, institute, balance) == (0, 0, 0), f"None باید صفر شود: {(teacher, institute, balance)}"
            assert balance == teacher + institute
    finally:
        models.Base.metadata.drop_all(engine)
        engine.dispose()


# ==========================================
# پوشش مسیرهای پول (Path coverage) — اثبات تجربی invariant روی همه‌ی مسیرهای نوشتن کیف
# ==========================================
def test_path_installment_manual_payment_keeps_invariant(world):
    """مسیر «پرداخت دستی قسط» (finance.pay_installment_manually): فقط آموزشگاه شارژ می‌شود."""
    installment = models.Installment(enrollment_id=world.enrollment.id, amount=300, due_date="1405/07/01", is_paid=False)
    world.db.add(installment)
    world.db.commit()

    finance.pay_installment_manually(installment.id, db=world.db, _="admin",
                                     payment_method="نقدی", authorization="Bearer wallet-admin-token")
    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=300, expected_balance=300,
                            context="پرداخت دستی قسط")

    # پرداخت دوم روی همان قسط باید رد شود و کیف دست‌نخورده بماند
    with pytest.raises(HTTPException) as error:
        finance.pay_installment_manually(installment.id, db=world.db, _="admin",
                                        payment_method="نقدی", authorization="Bearer wallet-admin-token")
    assert error.value.status_code == 400
    world.db.rollback()
    assert_wallet_invariant(world.db, expected_balance=300, context="بعد از رد پرداخت تکراری قسط")


def test_path_admin_update_transaction_keeps_invariant(world):
    """مسیر «ویرایش تراکنش توسط ادمین» (admin.update_transaction): دلتای اختلاف، اتمیک اعمال می‌شود."""
    from routers import admin as admin_router
    from schemas import TransactionUpdate

    receipt_id = pay(world, 100, wallet="institute")["receipt_id"]
    assert_wallet_invariant(world.db, expected_institute=100, expected_balance=100, context="قبل از ویرایش")

    admin_router.update_transaction(receipt_id, TransactionUpdate(amount=250, description="ویرایش مبلغ",
                                                                 date=TODAY_JALALI),
                                    db=world.db, _="admin")
    assert_wallet_invariant(world.db, expected_institute=250, expected_balance=250,
                            context="بعد از ویرایش ۱۰۰→۲۵۰")


def test_path_admin_delete_transaction_keeps_invariant(world):
    """مسیر «حذف تراکنش توسط ادمین» (admin.delete_transaction): اثر کیف باید کامل برگردد."""
    from routers import admin as admin_router

    submit_session(world)                                    # کیف: ‎-۶۰/-۴۰
    charge = world.db.query(models.Transaction).filter(models.Transaction.type == "session_charge").one()

    admin_router.delete_transaction(charge.id, db=world.db, _="admin")
    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=0, expected_balance=0,
                            context="بعد از حذف شارژ جلسه")


def test_path_session_reversal_restores_every_component(world):
    """برگشت جلسه (dependencies.reverse_session_financial_impacts): هر دو مؤلفه دقیقاً برمی‌گردند."""
    from dependencies import reverse_session_financial_impacts

    result = submit_session(world)
    assert_wallet_invariant(world.db, expected_teacher=-60, expected_institute=-40, context="پس از شارژ")

    reverse_session_financial_impacts(result["session_id"], world.db)
    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=0, expected_balance=0,
                            context="پس از برگشت جلسه")


# ==========================================
# پرداخت داخلی: idempotency و استرداد پس از مصرف اعتبار
# ==========================================
def test_idempotent_replay_credits_wallet_only_once(world):
    """پرداخت با همان idempotency_key دوبار ⇒ فقط یک‌بار شارژ (بدون شارژ دوباره)."""
    first = pay(world, 120, wallet="institute", idempotency_key="wallet-key-1")
    assert_wallet_invariant(world.db, expected_institute=120, expected_balance=120, context="پرداخت اول")

    second = pay(world, 120, wallet="institute", idempotency_key="wallet-key-1")
    assert second.get("duplicate") is True, "پاسخ دوم باید replay باشد (duplicate=True)"
    assert_wallet_invariant(world.db, expected_institute=120, expected_balance=120,
                            context="بعد از replay (نباید دوباره شارژ شود)")
    assert deposit_count(world.db) == 1, "replay نباید رسید دوم بسازد"
    assert second["receipt_id"] == first["receipt_id"]


def test_refund_after_credit_was_consumed_by_session_still_keeps_invariant(world):
    """استرداد پس از مصرف اعتبار: کیف می‌تواند منفی شود ولی invariant هرگز نمی‌شکند."""
    deposit_id = pay(world, 100, wallet="both")["receipt_ids"]
    submit_session(world)                                    # اعتبار خرج می‌شود
    for receipt_id in deposit_id:
        refund(world, receipt_id)

    teacher, institute, balance = wallets(world.db)
    assert balance == teacher + institute, f"invariant شکست: {balance} != {teacher}+{institute}"
    # پرداخت ۱۰۰ (۵۰/۵۰) سپس شارژ ۱۰۰ (۶۰/۴۰) سپس استرداد ۱۰۰ ⇒ ‎-۶۰/-۴۰
    assert (teacher, institute, balance) == (-60, -40, -100)


# ==========================================
# هم‌زمانی استرداد (گیت UPDATE مشروط)
# ==========================================
def test_concurrent_double_refund_applies_exactly_once(tmp_path):
    """دو استرداد هم‌زمان از دو اتصال: دقیقاً یکی موفق، کیف فقط یک‌بار کسر می‌شود."""
    engine = make_engine(f"sqlite:///{tmp_path / 'wallet-refund-race.sqlite'}")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        seed_world(db)
        deposit_id = finance.submit_payment(
            FinanceSubmitData(student_id=101, amount=200, target_wallet="institute",
                              description="پرداخت برای استرداد هم‌زمان", payment_method="نقدی",
                              date=TODAY_JALALI),
            db=db, _="admin", authorization="Bearer wallet-admin-token",
        )["receipt_id"]

    barrier = Barrier(2)

    def do_refund(_):
        with factory() as db:
            barrier.wait(timeout=20)
            try:
                finance.refund_transaction(deposit_id, db=db, authorization="Bearer wallet-admin-token", _="admin")
                return 200
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(do_refund, range(2)))

    with factory() as db:
        assert sorted(statuses) == [200, 400], f"دقیقاً یکی باید موفق شود؛ وضعیت‌ها: {statuses}"
        teacher, institute, balance = wallets(db)
        assert balance == teacher + institute, f"invariant شکست: {balance} != {teacher}+{institute}"
        assert (teacher, institute, balance) == (0, 0, 0), (
            f"کسر باید یک‌بار انجام شود (شد {(teacher, institute, balance)})"
        )
        assert db.query(models.Transaction).filter(models.Transaction.type == "reversal").count() == 1
    engine.dispose()


# ==========================================
# لبه‌های خطرناک (ادامه‌ی آدیت — سناریو ۱۳)
# ==========================================
def test_finding_fw2_legacy_both_receipt_edit_does_not_adjust_wallets(world):
    """🔎 یافته‌ی F-W2 (این تست عمداً fail می‌شود تا نقص مستند شود):
    مسیر ویرایش ادمین (`admin.update_transaction`) فقط `target_wallet` های teacher/institute را
    جابه‌جا می‌کند؛ برای رسید قدیمیِ `target_wallet='both'` دلتا **صفر** است (کامنت خودِ کد:
    «هدف نامشخص: هیچ تغییری در کیف‌پول اعمال نمی‌شود»). اما دو مسیر دیگر همین رسیدها را
    می‌شناسند: `refund_transaction` سهم‌ها را برمی‌گرداند و `delete_transaction` هم دلتا می‌دهد.
    نتیجه: با ویرایش مبلغ یک رسید both قدیمی، دفتر (Transaction) عوض می‌شود ولی کیف‌پول نه
    ⇒ عدم‌تطابق دفتر/کیف.

    سناریوی واقع‌گرا: رسید both قدیمی ۱۰۰ (۴۰ معلم/۶۰ آموزشگاه) که کیف‌ها هم قبلاً به همان
    اندازه شارژ شده‌اند؛ ویرایش مبلغ به ۲۰۰ باید ۱۰۰ به جمع کیف اضافه کند."""
    from routers import admin as admin_router
    from schemas import TransactionUpdate

    legacy = receipt(world.db, amount=100, target_wallet="both", share_teacher=40, share_institute=60)
    # شارژ کیف‌ها به همان اندازه که کد قدیمی هنگام ساخت این رسید انجام می‌داد
    world.db.query(models.Student).filter(models.Student.id == 101).update(
        {
            models.Student.wallet_teacher: func.coalesce(models.Student.wallet_teacher, 0) + 40,
            models.Student.wallet_institute: func.coalesce(models.Student.wallet_institute, 0) + 60,
        },
        synchronize_session=False,
    )
    world.db.commit()
    student = world.db.get(models.Student, 101)
    world.db.refresh(student)
    student.sync_wallet_balance()
    world.db.commit()
    before = wallets(world.db)
    assert before == (40, 60, 100)

    admin_router.update_transaction(legacy.id, TransactionUpdate(amount=200, description="ویرایش رسید both",
                                                                 date=TODAY_JALALI),
                                    db=world.db, _="admin")
    teacher, institute, balance = wallets(world.db)
    assert balance == teacher + institute, f"invariant شکست: {balance} != {teacher}+{institute}"
    assert (balance - before[2]) == 100, (
        f"F-W2: ویرایش ۱۰۰→۲۰۰ روی رسید both باید ۱۰۰ به جمع کیف اضافه کند "
        f"(افزایش واقعی: {balance - before[2]}؛ کیف: {teacher}/{institute})"
    )


def test_finding_fw1b_session_charge_edit_leaves_shares_stale(world):
    """🔎 یافته‌ی F-W1b (این تست عمداً fail می‌شود): ویرایش مبلغ session_charge فقط `amount` را
    عوض می‌کند و `share_teacher/share_institute` را دست نمی‌زند ⇒ جمع سهم‌ها با مبلغ ردیف
    ناسازگار می‌شود. گزارش‌های سهم معلم/آموزشگاه (`calculate_*_session_revenue`) دقیقاً همین
    ستون‌ها را جمع می‌زنند، پس عدد گزارش با دفتر هم‌خوان نخواهد بود."""
    from routers import admin as admin_router
    from schemas import TransactionUpdate
    from financial_calculations import calculate_institute_session_revenue

    submit_session(world)
    charge = world.db.query(models.Transaction).filter(models.Transaction.type == "session_charge").one()

    admin_router.update_transaction(charge.id, TransactionUpdate(amount=-130, description="افزایش شارژ جلسه",
                                                                 date=TODAY_JALALI),
                                    db=world.db, _="admin")
    world.db.expire_all()
    charge = world.db.get(models.Transaction, charge.id)

    shares_total = abs(charge.share_teacher or 0) + abs(charge.share_institute or 0)
    assert shares_total == abs(charge.amount), (
        f"F-W1b: جمع سهم‌ها ({shares_total}) باید با مبلغ شارژ ({abs(charge.amount)}) برابر بماند"
    )
    reported = calculate_institute_session_revenue(world.db, RANGE_START, RANGE_END)
    assert reported == 40, f"F-W1b: گزارش سهم آموزشگاه باید ۴۰ بماند/به‌روز شود؛ شد {reported}"


def test_edge_enrollment_payment_refund_reverses_institute_wallet(world):
    """استرداد واریز ثبت‌نامی (type=enrollment_payment، target_wallet=None) — شاخه‌ی M16:
    باید کیف آموزشگاه را برگرداند و invariant نشکند."""
    transaction = models.Transaction(
        student_id=101, enrollment_id=world.enrollment.id, course_id=1, branch_id=1,
        amount=80, payment_method="نقدی", date=TODAY_JALALI, type="enrollment_payment",
        description="واریز ثبت‌نامی",
    )
    world.db.add(transaction)
    world.db.query(models.Student).filter(models.Student.id == 101).update(
        {models.Student.wallet_institute: func.coalesce(models.Student.wallet_institute, 0) + 80},
        synchronize_session=False,
    )
    world.db.commit()
    student = world.db.get(models.Student, 101)
    world.db.refresh(student)
    student.sync_wallet_balance()
    world.db.commit()
    assert_wallet_invariant(world.db, expected_institute=80, expected_balance=80, context="واریز ثبت‌نامی")

    refund(world, transaction.id)
    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=0, expected_balance=0,
                            context="استرداد واریز ثبت‌نامی")


def test_edge_direct_balance_write_is_resynced_to_components(world):
    """اگر کسی wallet_balance را مستقیم و ناسازگار بنویسد، listener پروژه باید آن را به
    جمع دو مؤلفه برگرداند (مؤلفه‌ها منبع حقیقت‌اند)."""
    student = world.db.get(models.Student, 101)
    student.wallet_teacher = 0
    student.wallet_institute = 0
    student.wallet_balance = 9999          # نوشتن عمداً ناسازگار
    world.db.commit()

    assert_wallet_invariant(world.db, expected_teacher=0, expected_institute=0, expected_balance=0,
                            context="بازنویسی مستقیم balance")


def test_edge_absent_penalty_charge_keeps_invariant(world):
    """مسیر جریمه‌ی غیبت غیرموجه (دومین نقطه‌ی تغییر کیف در attendance.py)."""
    world.course.rule_calc_absent = True
    world.db.commit()

    request = AttendanceSubmitData(course_id=world.course.id, date=TODAY_JALALI,
                                   items=[AttendanceItem(student_id=world.student.id, status="Absent",
                                                         excused=False)])
    attendance.submit_session_and_calculate(request, db=world.db,
                                            authorization="Bearer wallet-admin-token", sub_role="admin")
    assert_wallet_invariant(world.db, expected_teacher=-60, expected_institute=-40, expected_balance=-100,
                            context="جریمه‌ی غیبت غیرموجه")
    session = world.db.query(models.SessionLog).order_by(models.SessionLog.id.desc()).first()
    assert session.absent_penalty_teacher == 60 and session.absent_penalty_institute == 40


def test_finding_fw1a_session_charge_edit_writes_fractional_money(world):
    """⚠️ یافته‌ی F-W1 (این تست عمداً fail می‌شود تا نقص مستند شود):
    ویرایش مبلغ یک session_charge توسط ادمین، دلتای کیف را با **نسبت اعشاری** (float) حساب می‌کند
    (`teacher_diff = diff * teacher_ratio` در admin.update_transaction) و آن را روی ستون‌های
    BigInteger می‌نویسد ⇒ کیف پول اعشاری می‌شود (-60.6 و -40.4) که برای واحد «تومان» نامعتبر است.
    invariant همچنان برقرار می‌ماند (چون بالانس از همان دو مؤلفه ساخته می‌شود) ولی مبلغ اعشاری
    در گزارش‌ها/فاکتورها نشت می‌کند."""
    from routers import admin as admin_router
    from schemas import TransactionUpdate

    submit_session(world)                                     # شارژ ۱۰۰ ⇒ ‎-60/-40
    charge = world.db.query(models.Transaction).filter(models.Transaction.type == "session_charge").one()

    admin_router.update_transaction(charge.id, TransactionUpdate(amount=-101, description="اصلاح شارژ جلسه",
                                                                 date=TODAY_JALALI),
                                    db=world.db, _="admin")

    teacher, institute, balance = wallets(world.db)
    assert balance == teacher + institute, f"invariant شکست: {balance} != {teacher}+{institute}"
    assert isinstance(teacher, int) and isinstance(institute, int) and isinstance(balance, int), (
        f"مبالغ کیف باید عدد صحیح (تومان) باشند؛ واقعی: teacher={teacher!r} ({type(teacher).__name__}), "
        f"institute={institute!r} ({type(institute).__name__}), balance={balance!r}"
    )
