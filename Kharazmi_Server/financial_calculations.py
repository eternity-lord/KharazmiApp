from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional
import hashlib
import models

# =========================================================================
# 📊 لایه محاسبات مالی متمرکز و یگانه خوارزمی (Centralized Financial Calculations)
# =========================================================================

# FIX H3-B3: report boundaries may be Jalali (monthly summary) or Gregorian (dashboard),
# and Transaction.date mixes both by row type (session_charge rows are Gregorian, deposit
# rows are Jalali). No SQL string range can bound that — parse via the central converter
# and filter in Python. Non-date SQL predicates are kept so volume stays bounded.
from today_summary import parse_project_date


def _parse_loose(value):
    """parse_project_date that also tolerates date/datetime objects (their str() form parses fine)."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    return parse_project_date(value)


def _parse_report_range(start_date, end_date):
    """Parse range boundaries to real dates; (None, None) when unparseable (fail-closed → 0)."""
    start = _parse_loose(start_date)
    end = _parse_loose(end_date)
    if start is None or end is None:
        return None, None
    return start, end


def _row_date_in_range(value, start, end) -> bool:
    parsed = _parse_loose(value)
    return parsed is not None and start <= parsed <= end


def calculate_institute_session_revenue(db: Session, start_date: str, end_date: str, branch_id: Optional[int] = None) -> int:
    """
    سود نظری آموزشگاه: مجموع سهم آموزشگاه از جلسات کلاسی برگزار شده (session_charge)
    فیلتر استاندارد: is_deleted==False و is_reversed==False
    FIX H3-B3: تاریخ‌ها با مبدل مرکزی parse و در پایتون فیلتر می‌شوند (ستون دو تقویمه).
    """
    start, end = _parse_report_range(start_date, end_date)
    if start is None:
        return 0
    query = db.query(models.Transaction.share_institute, models.Transaction.date).filter(
        models.Transaction.type == "session_charge",
        models.Transaction.is_deleted == False,
        models.Transaction.is_reversed == False
    )
    if branch_id is not None:
        query = query.filter(models.Transaction.branch_id == branch_id)
    return sum(int(share or 0) for share, date_value in query.all() if _row_date_in_range(date_value, start, end))


def collected_revenue_rows(db: Session, start_date: str, end_date: str,
                           branch_id: Optional[int] = None, course_id: Optional[int] = None,
                           include_undated: bool = False):
    """ردیف‌های خام «وصولی نقدی آموزشگاه» در بازه — منبع یگانهٔ KPI/گزارش/نمودار (FIX O-07/O-08).

    خروجی: فهرست `(amount, date)` با date **خامِ** ذخیره‌شده (ممکن است شمسی، میلادی، با ساعت،
    یا نامعلوم باشد) تا مصرف‌کننده (نمودار) خودش با مبدل مرکزی قلم زمانی بسازد.
    فیلترها: `type=="deposit"`، `target_wallet=="institute"`، مبلغ مثبت، حذف/برگشتی نشده،
    و بازهٔ تاریخ (پارس در پایتون چون ستون دو تقویمه است — H3-B3).

    `include_undated=True` ⇒ ردیف‌های بی‌تاریخ/نامعتبر هم برمی‌گردند (مصرف: نمودار درآمد که
    آن‌ها را در قلم «بی‌تاریخ» نشان می‌دهد). جمع‌های مالی (KPI/گزارش) عمداً فقط تاریخ‌دارها را
    می‌شمارند و پول بی‌تاریخ از مسیر شمارندهٔ جدا (O-10) گزارش می‌شود.
    """
    start, end = _parse_report_range(start_date, end_date)
    if start is None:
        return []
    query = db.query(models.Transaction.amount, models.Transaction.date).filter(
        models.Transaction.target_wallet == "institute",
        models.Transaction.type == "deposit",
        models.Transaction.amount > 0,
        models.Transaction.is_deleted == False,
        models.Transaction.is_reversed == False
    )
    if branch_id is not None:
        query = query.filter(models.Transaction.branch_id == branch_id)
    if course_id is not None:
        query = query.filter(models.Transaction.course_id == course_id)
    rows = query.all()
    if include_undated:
        return [(int(amount or 0), date_value) for amount, date_value in rows
                if _row_date_in_range(date_value, start, end)
                or _parse_loose(date_value) is None]
    return [(int(amount or 0), date_value) for amount, date_value in rows
            if _row_date_in_range(date_value, start, end)]


def calculate_institute_collected_revenue(db: Session, start_date: str, end_date: str, branch_id: Optional[int] = None) -> int:
    """
    سود وصول‌شده آموزشگاه: مجموع مبالغ واریزی واقعی دانش‌آموزان به حساب آموزشگاه (deposit)
    فیلتر استاندارد: is_deleted==False و is_reversed==False
    FIX H3-B3: تاریخ‌ها با مبدل مرکزی parse و در پایتون فیلتر می‌شوند (ستون دو تقویمه).
    FIX O-07: بدنه به helper مشترک `collected_revenue_rows` منتقل شد تا نمودار درآمد هم
    دقیقاً همان ردیف‌ها را ببیند (جمع ستون‌های نمودار == همین عدد).
    """
    return sum(amount for amount, _ in collected_revenue_rows(db, start_date, end_date, branch_id))


def count_undated_payments(db: Session, target_wallet: Optional[str] = None,
                           branch_id: Optional[int] = None, course_ids: Optional[list] = None):
    """(تعداد، مبلغ) پرداخت‌های مثبتِ **بی‌تاریخ** — هشدار «پول بی‌تاریخ» در گزارش‌ها (FIX O-10).

    «بی‌تاریخ» = تاریخی که مبدل مرکزی نمی‌تواند پارس کند (خالی/NULL/نامعتبر). این ردیف‌ها به
    هیچ بازهٔ ماه/سالی نسبت داده نمی‌شوند، پس عمداً در جمع‌های بازه‌دار (وصولی/سود) نمی‌آیند
    (سیاست E1: هیچ ردیفی بی‌صدا حذف نمی‌شود)؛ این شمارنده فقط آن‌ها را آشکار می‌کند.
    """
    query = db.query(models.Transaction.amount, models.Transaction.date).filter(
        models.Transaction.type == "deposit",
        models.Transaction.amount > 0,
        models.Transaction.is_deleted == False,
        models.Transaction.is_reversed == False
    )
    if target_wallet is not None:
        query = query.filter(models.Transaction.target_wallet == target_wallet)
    if branch_id is not None:
        query = query.filter(models.Transaction.branch_id == branch_id)
    if course_ids is not None:
        # مثل منطق کارکرد معلم: هم پرداخت‌های همان کلاس‌ها، هم پرداخت‌های عمومی (بدون کلاس)
        query = query.filter(or_(models.Transaction.course_id.in_(course_ids),
                                 models.Transaction.course_id.is_(None)))
    amounts = [int(amount or 0) for amount, date_value in query.all()
               if _parse_loose(date_value) is None]
    return len(amounts), sum(amounts)


def calculate_total_turnover(db: Session, start_date: str, end_date: str, branch_id: Optional[int] = None) -> int:
    """
    گردش مالی کل مجموعه: مجموع کل مبالغ فیزیکی دریافتی از تمام دانش‌آموزان (کل واریزی‌ها)
    فیلتر استاندارد: is_deleted==False و is_reversed==False
    FIX H3-B3: تاریخ‌ها با مبدل مرکزی parse و در پایتون فیلتر می‌شوند (ستون دو تقویمه).
    """
    start, end = _parse_report_range(start_date, end_date)
    if start is None:
        return 0
    query = db.query(models.Transaction.amount, models.Transaction.date).filter(
        models.Transaction.type == "deposit",
        models.Transaction.amount > 0,
        models.Transaction.is_deleted == False,
        models.Transaction.is_reversed == False
    )
    if branch_id is not None:
        query = query.filter(models.Transaction.branch_id == branch_id)
    return sum(int(amount or 0) for amount, date_value in query.all() if _row_date_in_range(date_value, start, end))


def calculate_teacher_session_revenue(db: Session, teacher_id: int, start_date: str, end_date: str) -> int:
    """
    کارکرد ناخالص معلم: مجموع سهم معلم از جلسات کلاسی برگزار شده (session_charge)
    فیلتر استاندارد: is_deleted==False و is_reversed==False
    FIX H3-B3: تاریخ‌ها با مبدل مرکزی parse و در پایتون فیلتر می‌شوند (ستون دو تقویمه).
    """
    start, end = _parse_report_range(start_date, end_date)
    if start is None:
        return 0
    # واکشی کلاس‌های معلم
    courses = db.query(models.Course).filter(models.Course.teacher_id == teacher_id).all()
    course_ids = [c.id for c in courses]
    if not course_ids:
        return 0

    query = db.query(models.Transaction.share_teacher, models.Transaction.date).filter(
        models.Transaction.type == "session_charge",
        models.Transaction.course_id.in_(course_ids),
        models.Transaction.is_deleted == False,
        models.Transaction.is_reversed == False
    )
    return sum(int(share or 0) for share, date_value in query.all() if _row_date_in_range(date_value, start, end))


def calculate_teacher_collected_revenue(db: Session, teacher_id: int, start_date: str, end_date: str) -> int:
    """
    مبالغ تسویه‌شده یا دریافتی مستقیم معلم: مجموع مبالغ واریزی به کیف پول مربی (deposit)
    فیلتر استاندارد: is_deleted==False و is_reversed==False
    FIX H3-B3: تاریخ‌ها با مبدل مرکزی parse و در پایتون فیلتر می‌شوند (ستون دو تقویمه).
    """
    start, end = _parse_report_range(start_date, end_date)
    if start is None:
        return 0
    courses = db.query(models.Course).filter(models.Course.teacher_id == teacher_id).all()
    course_ids = [c.id for c in courses]

    # مبالغ واریزی مستقیم برای کلاس‌های معلم
    query_direct = db.query(models.Transaction.amount, models.Transaction.date).filter(
        models.Transaction.target_wallet == "teacher",
        models.Transaction.amount > 0,
        models.Transaction.course_id.in_(course_ids),
        models.Transaction.is_deleted == False,
        models.Transaction.is_reversed == False
    )
    collected_direct = sum(int(amount or 0) for amount, date_value in query_direct.all() if _row_date_in_range(date_value, start, end))

    # مبالغ عمومی واریزی برای شاگردان این معلم
    # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
    enrolled_student_ids = [r[0] for r in db.query(models.Enrollment.student_id).filter(models.Enrollment.is_deleted == False).filter(models.Enrollment.course_id.in_(course_ids)).distinct().all()]
    collected_general = 0
    if enrolled_student_ids:
        query_general = db.query(models.Transaction.amount, models.Transaction.date).filter(
            models.Transaction.target_wallet == "teacher",
            models.Transaction.amount > 0,
            models.Transaction.course_id == None,
            models.Transaction.student_id.in_(enrolled_student_ids),
            models.Transaction.is_deleted == False,
            models.Transaction.is_reversed == False
        )
        collected_general = sum(int(amount or 0) for amount, date_value in query_general.all() if _row_date_in_range(date_value, start, end))

    return collected_direct + collected_general


# FIX: Bug 16 - calculate contractual debt once, using discounted tuition and recorded payments.
def calculate_enrollment_debt(enrollment) -> int:
    from dependencies import get_enrollment_tuition_and_discount
    if enrollment.is_deleted or not enrollment.total_tuition:
        return 0
    final_tuition, _ = get_enrollment_tuition_and_discount(enrollment)
    return max(0, int(final_tuition) - int(enrollment.total_paid or 0))


# FIX: Bug 16 - priced enrollments take precedence; wallets are only a legacy, unpriced fallback.
def calculate_student_debt(db: Session, student) -> int:
    # FIX: Bugs 13/16 - only active tuition is owed; keep archived rows solely to detect cancellation.
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.student_id == student.id).all()
    active = [enrollment for enrollment in enrollments if not enrollment.is_deleted]
    priced = [enrollment for enrollment in active if (enrollment.total_tuition or 0) > 0]
    if priced:
        return sum(calculate_enrollment_debt(enrollment) for enrollment in priced)
    if enrollments and not active:
        return 0
    return max(0, -(student.wallet_teacher or 0)) + max(0, -(student.wallet_institute or 0))


# FIX: H5/H6 - منطق یگانه‌ی تقسیم سهم جلسه؛ استخراج‌شده از submit/edit تا فقط یک‌بار نوشته/تست شود.
def _distribute_remainder(base: int, remainder: int, count: int, seed: str, salt: str) -> list:
    """FIX L2: توزیع عادلانه‌ی باقیمانده — به‌جای idxهای اول، از آفست چرخشی قطعی
    (sha256 پایدار روی seed جلسه؛ هر جلسه نفرات متفاوتی) شروع می‌شود.
    دقیقاً remainder تا ‎+۱‎، پس جمع کل حفظ می‌شود. بدون seed، رفتار legacy حفظ می‌شود."""
    if count <= 0:
        return []
    if not seed:
        return [base + (1 if idx < remainder else 0) for idx in range(count)]
    start = int(hashlib.sha256(f"{seed}:{salt}".encode("utf-8")).hexdigest(), 16) % count
    return [base + (1 if (idx - start) % count < remainder else 0) for idx in range(count)]


# FIX (audit-v2/blind-approve): سقف نرخ هر-شاگرد-هر-جلسه در ثبت کلاس توسط خود معلم.
# مبنا: teacher_session_price واحد سرانه است (پایین: T_total = price × present) و seed واقعی
# ۵۰۰٬۰۰۰ است؛ پس ۵٬۰۰۰٬۰۰۰ (۱۰ برابر) اشتباه تایپی/سوءاستفاده (مثل ۹۹۹٬۹۹۹٬۹۹۹) را می‌گیرد
# و کلاس مشروع را نه. ادمین/منشی از سقف معاف‌اند (آگاهانه) ولی approve بالای سقف
# price_warning برمی‌گرداند (همان ثابت — admin.approve_class).
MAX_TEACHER_SESSION_PRICE = 5_000_000


def compute_session_shares(db: Session, course, present_count: int, absent_unexcused_count: int, rotation_seed: str = "") -> dict:
    """محاسبه‌ی متمرکز سهم جلسه.

    ورودی: نشست دیتابیس، آبجکت کلاس، تعداد حاضرین، تعداد غایبین غیرموجه مشمول جریمه.
    خروجی: دیکشنری با کلیدهای T_total/I_total قراردادی، میانگین‌های پایه، توزیع‌ها،
    هزینه‌ی سرانه، و جمع جریمه‌های غایبین (U × base).

    - H5: T_total اول از course.teacher_session_price × present_count؛ فقط اگر صفر/None
      بود fallback به PricingTable با N_capped=min(present_count,5).
    - H5: I_total از InstituteShare با N_capped_institute=min(present_count,15)؛ اگر
      present_count>0 و سطری نبود، HTTPException واضح.
    - H6(A2): جریمه‌ها فقط «محاسبه» می‌شوند؛ انباشت مقدار واقعیِ شارژشده در
      ستون‌های SessionLog بر عهده‌ی حلقه‌ی فراخوان است.
    """
    result = {
        "category": None,  # FIX L13: بدون حدس پیش‌فرض؛ مقطع واقعی پایین تعیین می‌شود.
        "N_capped": 0,
        "N_capped_institute": 0,
        "T_total": 0,
        "I_total": 0,
        "teacher_share_per_student": 0,
        "institute_share_per_student": 0,
        "teacher_share_distribution": [],
        "institute_share_distribution": [],
        "total_cost_per_student": 0,
        "penalty_teacher_total": 0,
        "penalty_institute_total": 0,
    }
    if not present_count or present_count <= 0:
        # FIX F1-A: جلسه‌ی تماماً-غایب — جریمه بر مبنای U (تعداد غایب غیرموجه)، نه present.
        # T_total/I_total صفر می‌مانند (تدریس نشده = شهریه‌ی قراردادی ندارد) ولی base_sرانه‌ی
        # جریمه ساخته می‌شود تا حلقه‌ی فراخوان (که برای غایب از *_per_student استفاده می‌کند)
        # بدون هیچ تغییری شارژ + انباشت کند. این شاخه فقط وقتی present==0 فعال است؛ مسیر
        # عادی (present>0) پایین، دست‌نخورده. رفتار خطا عین H5 (400 مقطع / 500 تعرفه).
        unexcused_zero = absent_unexcused_count or 0
        if unexcused_zero > 0:
            _u = unexcused_zero
            _n_cap_t = min(_u, 5)
            _n_cap_i = min(_u, 15)
            result["N_capped"] = _n_cap_t
            result["N_capped_institute"] = _n_cap_i
            # معلم: نرخ کلاس، وگرنه fallback به PricingTable با N بر مبنای U.
            if course.rule_prepay_teacher:
                _pen_base_t = 0
            else:
                _unit = course.teacher_session_price or 0
                if _unit > 0:
                    _pen_base_t = _unit
                else:
                    # آینه‌ی L13 پایین (عمداً تکراری، تا مسیر عادی دست‌نخورده بماند).
                    _g = (course.grade_level or "").strip().replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
                    _g = " ".join(_g.split())
                    if _g in ("اول", "دوم", "سوم", "چهارم", "پنجم", "ششم", "ابتدایی", "دبستان"):
                        _cat = "elementary"
                    elif _g in ("هفتم", "هشتم", "نهم", "راهنمایی", "متوسطه اول"):
                        _cat = "middle_school"
                    elif _g in ("دهم", "یازدهم", "دوازدهم", "دبیرستان", "متوسطه دوم"):
                        _cat = "high_school"
                    else:
                        _cat = None
                    result["category"] = _cat
                    if _cat is None:
                        raise HTTPException(
                            status_code=400,
                            detail=f"مقطع تحصیلی «{course.grade_level}» نامعتبر است؛ مقطع را اصلاح کنید یا نرخ جلسه را روی کلاس ثبت کنید",
                        )
                    _row_t = db.query(models.PricingTable).filter(models.PricingTable.category == _cat).first()
                    if _row_t is None:
                        raise HTTPException(
                            status_code=400,  # O-06: نبود تعرفه = تنظیمات ناقص (۴۰۰)، نه خرابی سرور؛ گارد H5 (خطای واضح به‌جای جلسهٔ مجانی) دست‌نخورده
                            detail="تعرفه‌ی سهم معلم برای این مقطع یافت نشد؛ لطفاً ابتدا جدول تعرفه را ثبت کنید",
                        )
                    _pen_base_t = getattr(_row_t, f"count_{_n_cap_t}", 0) // _u
            # آموزشگاه: همیشه از InstituteShare با N بر مبنای U.
            if course.rule_prepay_institute:
                _pen_base_i = 0
            else:
                _share_row = db.query(models.InstituteShare).first()
                if _share_row is None:
                    raise HTTPException(
                        status_code=400,  # O-06: نبود تعرفه = تنظیمات ناقص (۴۰۰)، نه خرابی سرور؛ گارد H5 (خطای واضح به‌جای جلسهٔ مجانی) دست‌نخورده
                        detail="تنظیمات سهم آموزشگاه یافت نشد؛ لطفاً ابتدا تعرفه‌ی سهم آموزشگاه را ثبت کنید",
                    )
                _pen_base_i = (getattr(_share_row, f"count_{_n_cap_i}", 0) or 0) // _u
            result.update({
                "teacher_share_per_student": int(_pen_base_t),
                "institute_share_per_student": int(_pen_base_i),
                "total_cost_per_student": int(_pen_base_t) + int(_pen_base_i),
                "penalty_teacher_total": int(_u) * int(_pen_base_t),
                "penalty_institute_total": int(_u) * int(_pen_base_i),
            })
        return result

    # FIX L13: مقطع از روی لیست ثابت با تطبیق دقیق (نه substring) — مقادیر ناشناخته (از جمله
    # «متوسطه»ی تنها، «کنکور»، «سایر»، «نامشخص») category=None می‌گیرند و فقط اگر واقعاً در
    # قیمت‌گذاری fallback لازم باشند خطای واضح می‌دهند (کلاسِ دارای نرخ، بی‌نیاز از مقطع است).
    _grade = (course.grade_level or "").strip().replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    _grade = " ".join(_grade.split())
    if _grade in ("اول", "دوم", "سوم", "چهارم", "پنجم", "ششم", "ابتدایی", "دبستان"):
        category = "elementary"
    elif _grade in ("هفتم", "هشتم", "نهم", "راهنمایی", "متوسطه اول"):
        category = "middle_school"
    elif _grade in ("دهم", "یازدهم", "دوازدهم", "دبیرستان", "متوسطه دوم"):
        category = "high_school"
    else:
        category = None
    result["category"] = category

    N_capped = min(present_count, 5)
    N_capped_institute = min(present_count, 15)
    result["N_capped"] = N_capped
    result["N_capped_institute"] = N_capped_institute

    # الف) سهم مربی — H5: اولویت با نرخ ثبت‌شده روی خود کلاس
    if course.rule_prepay_teacher:
        T_total, base_t, teacher_dist = 0, 0, [0] * present_count
    else:
        unit_price = course.teacher_session_price or 0
        if unit_price > 0:
            T_total = unit_price * present_count
        else:
            # FIX L13: بدون نرخ کلاس، مقطع نامعتبر = تعرفه‌ی نامشخص — حدس نمی‌زنیم، خطای واضح.
            if category is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"مقطع تحصیلی «{course.grade_level}» نامعتبر است؛ مقطع را اصلاح کنید یا نرخ جلسه را روی کلاس ثبت کنید",
                )
            row_teacher = db.query(models.PricingTable).filter(models.PricingTable.category == category).first()
            # FIX L-carryover-2 (فلسفه‌ی H5، مثل گارد InstituteShare): بدون ردیف تعرفه،
            # T_total=0 ساکت یعنی جلسه‌ی مجانی — خطای واضح به‌جای ادامه.
            if row_teacher is None:
                raise HTTPException(
                    status_code=400,  # O-06: نبود تعرفه = تنظیمات ناقص (۴۰۰)، نه خرابی سرور؛ گارد H5 (خطای واضح به‌جای جلسهٔ مجانی) دست‌نخورده
                    detail="تعرفه‌ی سهم معلم برای این مقطع یافت نشد؛ لطفاً ابتدا جدول تعرفه را ثبت کنید",
                )
            T_total = getattr(row_teacher, f"count_{N_capped}", 0)
        base_t = T_total // present_count
        remainder_t = T_total - (base_t * present_count)
        teacher_dist = _distribute_remainder(base_t, remainder_t, present_count, rotation_seed, "t")

    # ب) سهم آموزشگاه — H5: همیشه از InstituteShare
    if course.rule_prepay_institute:
        I_total, base_i, institute_dist = 0, 0, [0] * present_count
    else:
        share_row = db.query(models.InstituteShare).first()
        if share_row is None:
            raise HTTPException(
                status_code=400,  # O-06: نبود تعرفه = تنظیمات ناقص (۴۰۰)، نه خرابی سرور؛ گارد H5 (خطای واضح به‌جای جلسهٔ مجانی) دست‌نخورده
                detail="تنظیمات سهم آموزشگاه یافت نشد؛ لطفاً ابتدا تعرفه‌ی سهم آموزشگاه را ثبت کنید",
            )
        I_total = getattr(share_row, f"count_{N_capped_institute}", 0) or 0
        base_i = I_total // present_count
        remainder_i = I_total - (base_i * present_count)
        institute_dist = _distribute_remainder(base_i, remainder_i, present_count, rotation_seed, "i")

    unexcused = absent_unexcused_count or 0
    result.update({
        "T_total": int(T_total),
        "I_total": int(I_total),
        "teacher_share_per_student": int(base_t),
        "institute_share_per_student": int(base_i),
        "teacher_share_distribution": [int(x) for x in teacher_dist],
        "institute_share_distribution": [int(x) for x in institute_dist],
        "total_cost_per_student": int(base_t) + int(base_i),
        "penalty_teacher_total": int(unexcused) * int(base_t),
        "penalty_institute_total": int(unexcused) * int(base_i),
    })
    return result

