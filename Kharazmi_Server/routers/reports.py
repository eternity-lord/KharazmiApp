from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Header
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Union
from sqlalchemy import desc, or_, text, func
import io
import uuid
import os
import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

import models
from models import (
    Attendance, Course, Enrollment, Grade, InstituteShare, SessionLog, SmsLog, Student, Teacher, Transaction, User, UserSession, InstituteSettings
)
from schemas import (
    HistoryRequest, LoginRequest, TeacherInfo, FullTeacherProfile, StudentCreate, TeacherCreate, CourseCreate, EnrollmentCreate, GradeCreate, GradeItem, AttendanceLogRequest, AttendanceItem, AttendanceSubmitData, SmsSendRequest, ChangePasswordRequest, StudentProfileInfo, FullStudentProfile, TeacherProfileInfo, FullTeacherProfile, ClassReportInfo, ClassStudentData, ClassSessionHistory, FullClassReport, ShareConfigModel, StudentUpdate, TeacherUpdate, PersonListItem, TransactionUpdate, StudentAttendanceHistoryRequest, AdvancedSearchItem, FinanceSubmitData, PrintReceiptRequest, TransactionTestData
)
from dependencies import get_db, check_admin_access, check_admin_or_secretary_access, check_user_login, check_student_access, get_enrollment_tuition_and_discount, SESSION_EXPIRY_DAYS, resolve_effective_sub_role, display_name, safe_person_name

# FIX: Bug 16 - share the tuition-minus-payment debt calculation across financial views.
from financial_calculations import calculate_student_debt

router = APIRouter()

from financial_calculations import (
    calculate_institute_session_revenue,
    calculate_institute_collected_revenue,
    calculate_total_turnover,
    calculate_teacher_session_revenue,
    calculate_teacher_collected_revenue
)

def get_user_branch_filter(db: Session, authorization: Optional[str], branch_id: Optional[int]) -> Optional[int]:
    # FIX: JWT-aware + teacher_id handling
    if not authorization:
        return branch_id
    try:
        from dependencies import get_session_from_token
        token = authorization.split()[1]
        session, _ = get_session_from_token(db, token)
        if session:
            if session.sub_role in ["student", "parent"]:
                return branch_id
            user = db.query(User).filter(User.id == session.user_id).first()
            if user and user.branch_id is not None:
                return user.branch_id
            # اگر معلم است و User ندارد، از Teacher.branch_id
            if getattr(session, "teacher_id", None):
                teacher = db.query(Teacher).filter(Teacher.id == session.teacher_id).first()
                if teacher and teacher.branch_id is not None:
                    return teacher.branch_id
    except Exception:
        pass
    return branch_id

def _parsed_project_date(value):
    """تاریخ (شمسی/میلادی) را parse می‌کند؛ مقدار نامعلوم/نامعتبر ⇒ None (بدون استثنا)."""
    from today_summary import parse_project_date  # lazy، الگوی موجود پروژه
    try:
        return parse_project_date(value)
    except Exception:
        return None


def _date_in_range(value, start_day, end_day) -> bool:
    """فیلتر بازهٔ تاریخ با سیاست «هیچ ردیف مالی بی‌صدا حذف نشود» (FIX A3).

    پیش‌تر این تابع در `reports.py` برای هر مقدار غیرقابل‌parse — از جمله `date = NULL` —
    `return False` می‌داد و ردیف از گزارش‌ها (نمودار درآمد، روند حضور، چارت سهم‌ها و گزارش
    مالی) حذف می‌شد؛ حتی وقتی کاربر هیچ بازه‌ای درخواست نکرده بود. نتیجه: جمع مالی آموزشگاه
    کمتر از واقع نمایش داده می‌شد. (همان باگی که در «طلب تسویه‌نشدهٔ معلم» رفع شد.)

    سیاست فعلی:
      • بدون بازه ⇒ همهٔ ردیف‌ها می‌آیند (تاریخ‌دار و بی‌تاریخ).
      • با بازه ⇒ فقط ردیف‌های دارای تاریخِ معتبر محدود می‌شوند؛ ردیف بی‌تاریخ/نامعتبر
        می‌ماند (نمی‌توان اثبات کرد بیرون بازه است) و هیچ تاریخ جعلی ساخته نمی‌شود.
    """
    parsed = _parsed_project_date(value)
    if parsed is None:
        return True
    if start_day is not None and parsed < start_day:
        return False
    if end_day is not None and parsed > end_day:
        return False
    return True


def _api_date_or_blank(value) -> str:
    """تاریخِ قابل‌نمایش در API: تاریخ معتبر ⇒ همان مقدار ذخیره‌شده؛ نامعلوم ⇒ "".

    کلاینت‌ها (اپ اندروید) مدل `String` غیر-null دارند؛ فرستادن `null` یا تاریخ جعلی
    ممنوع است. مقدار خام دیتابیس هم دست‌کاری نمی‌شود.
    """
    return value if _parsed_project_date(value) is not None else ""


@router.get("/reports/chart-data")
def get_chart_data(
    class_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    _: str = Depends(check_admin_or_secretary_access)  # FIX (L14/Y4): نمودارهای درآمد/حضور سطح موسسه — فقط کارکنان
):
    # FIX H3-B3: boundaries may be Jalali (app ranges) or Gregorian; Transaction.date mixes both
    # by row type, so SQL string ranges can't bound it — parse and filter in Python.
    # FIX(A3): فیلتر/نمایش تاریخ از helper مشترک ماژول می‌آید (ردیف بی‌تاریخ حذف نمی‌شود).
    start_day = _parsed_project_date(start_date) if start_date else None
    end_day = _parsed_project_date(end_date) if end_date else None

    def _in_range(value):  # سازگاری با فراخوانی‌های همین تابع
        return _date_in_range(value, start_day, end_day)

    # 1. Income Chart (existing + filters)
    # FIX: Bug 12 - exclude archived Transaction rows from this active view.
    q_income = db.query(Transaction).filter(Transaction.is_deleted == False, Transaction.is_reversed == False)
    if class_id:
        q_income = q_income.filter(Transaction.course_id == class_id)

    incomes = [t for t in q_income.all() if _in_range(t.date)]
    total_income = sum(t.amount for t in incomes)

    income_data = [
        {"day": "شنبه", "amount": total_income // 5},
        {"day": "یکشنبه", "amount": total_income // 4},
        {"day": "دوشنبه", "amount": total_income // 3},
        {"day": "سه‌شنبه", "amount": total_income // 2},
        {"day": "چهارشنبه", "amount": total_income},
    ]

    # 2. Student Chart (existing)
    boys = db.query(Student).filter(Student.gender == "آقا").count()
    girls = db.query(Student).filter(Student.gender == "خانم").count()
    student_stats = [{"label": "آقا", "count": boys}, {"label": "خانم", "count": girls}]

    # 3. Chart 1: Attendance Trend
    # FIX: Bug 14 - exclude archived SessionLog rows from this active view.
    q_sessions = db.query(SessionLog).filter(SessionLog.is_deleted == False)
    if class_id:
        q_sessions = q_sessions.filter(SessionLog.course_id == class_id)

    sessions = [s for s in q_sessions.all() if _in_range(s.date)]
    # FIX(A3): ترتیب قطعی (deterministic) — تاریخ معتبر صعودی، ردیف‌های بی‌تاریخ در انتها و
    # در تاریخ یکسان، id صعودی. پیش‌تر ترتیب به رفتار دیتابیس در NULL وابسته بود (در SQLite
    # اول، در PostgreSQL آخر) ⇒ خروجی بین محیط‌ها تفاوت داشت.
    sessions.sort(key=lambda s: (_parsed_project_date(s.date) is None,
                                 _parsed_project_date(s.date) or datetime.date.min,
                                 s.id))
    session_ids = [s.id for s in sessions]
    attendance_trend = []
    
    if session_ids:
        from sqlalchemy import func
        stats = (
            db.query(
                Attendance.session_id,
                Attendance.status,
                func.count(Attendance.id)
            )
            .filter(Attendance.session_id.in_(session_ids))
            .group_by(Attendance.session_id, Attendance.status)
            .all()
        )
        
        session_stats = {sid: {"present": 0, "absent": 0} for sid in session_ids}
        for sid, status_val, count in stats:
            if sid in session_stats:
                if status_val in ["Present", "Late"]:
                    session_stats[sid]["present"] += count
                elif status_val == "Absent":
                    session_stats[sid]["absent"] += count
                    
        for s in sessions:
            stat = session_stats.get(s.id, {"present": 0, "absent": 0})
            present = stat["present"]
            absent = stat["absent"]
            total = present + absent
            pct = (present / total * 100) if total > 0 else 100.0
            attendance_trend.append({
                # FIX(A3): مقدار نامعلوم ⇒ "" (بدون تاریخ جعلی و بدون null برای کلاینت)
                "date": _api_date_or_blank(s.date),
                "present": present,
                "absent": absent,
                "percentage": round(pct, 1)
            })

    # 4. Chart 2: Shares Chart
    # استخراج و اعتبارسنجی نقش ادمین برای نمایش چارت سهم‌ها به منشی
    sub_role = "secretary"
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            session = db.query(UserSession).filter(UserSession.token == token).first()
            if session:
                user = db.query(User).filter(User.id == session.user_id).first()
                if user:
                    # FIX(A1): نقش با سیاست کمترین سطح دسترسی (سهم معلم/آموزشگاه
                    # فقط برای ادمین واقعی نمایش داده می‌شود، نه رکورد بی‌نقش).
                    sub_role = resolve_effective_sub_role(user)

    shares_chart = None
    if sub_role == "admin":
        # FIX: Bug 12 - exclude archived Transaction rows from this active view.
        q_shares = db.query(Transaction).filter(Transaction.is_deleted == False, Transaction.is_reversed == False)
        if class_id:
            q_shares = q_shares.filter(Transaction.course_id == class_id)

        # FIX H3-B3: same as income/sessions above — parsed Python filter (_in_range already in scope).
        shares_trans = [t for t in q_shares.all() if _in_range(t.date)]
        total_teacher_share = sum(t.share_teacher for t in shares_trans if t.share_teacher is not None)
        total_institute_share = sum(t.share_institute for t in shares_trans if t.share_institute is not None)
        
        shares_chart = {
            "teacher": total_teacher_share,
            "institute": total_institute_share
        }

    return {
        "income_chart": income_data,
        "student_chart": student_stats,
        "attendance_trend": attendance_trend,
        "shares_chart": shares_chart
    }


# ==========================================
# 3. API های ثبت نام
# ==========================================


@router.get("/reports/financial")
def get_financial_report(
    start_date: str = None,
    end_date: str = None,
    branch_id: Optional[int] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    _: str = Depends(check_admin_access)
):
    resolved_branch = get_user_branch_filter(db, authorization, branch_id)
    # FIX H3-B3: boundaries may be Jalali or Gregorian; Transaction.date mixes both by row type —
    # parse and filter in Python (same pattern as get_chart_data above).
    # FIX(A3): همان helper مشترک — ردیف بی‌تاریخ از گزارش مالی حذف نمی‌شود.
    start_day = _parsed_project_date(start_date) if start_date else None
    end_day = _parsed_project_date(end_date) if end_date else None

    def _in_range(value):
        return _date_in_range(value, start_day, end_day)
    # FIX: Bug 12 - exclude archived Transaction rows from this active view.
    query = db.query(Transaction).filter(Transaction.is_deleted == False, Transaction.is_reversed == False)
    if resolved_branch is not None:
        query = query.filter(Transaction.branch_id == resolved_branch)

    trans = [t for t in query.order_by(desc(Transaction.id)).all() if _in_range(t.date)]
    report = []
    for t in trans:
        st_name = "ناشناس"
        student_id = None
        if t.enrollment_id:
            en = db.query(Enrollment).filter(Enrollment.id == t.enrollment_id).first()
            if en:
                st = db.query(Student).filter(Student.id == en.student_id).first()
                if st:
                    st_name = display_name(st, "نامشخص")
                    student_id = st.id
        elif t.student_id:
            st = db.query(Student).filter(Student.id == t.student_id).first()
            if st:
                st_name = display_name(st, "نامشخص")
                student_id = st.id
        report.append(
            {
                "student_id": student_id,
                "student_name": st_name,
                "amount": t.amount,
                # FIX(A3): تاریخ نامعلوم ⇒ "" (نه null؛ نه تاریخ جعلی)
                "date": _api_date_or_blank(t.date),
                "description": t.description,
                "payment_method": t.payment_method,
            }
        )
    return report


@router.get("/reports/debtors")
def get_debtors_report(
    branch_id: Optional[int] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    _: str = Depends(check_admin_access)
):
    resolved_branch = get_user_branch_filter(db, authorization, branch_id)
    query = db.query(Student)
    if resolved_branch is not None:
        query = query.filter(Student.branch_id == resolved_branch)
    all_students = query.all()
    res = []
    for student in all_students:
        # Calculate debt from wallet_teacher and wallet_institute
        w_t = student.wallet_teacher if student.wallet_teacher is not None else 0
        w_i = student.wallet_institute if student.wallet_institute is not None else 0

        debt_teacher = abs(w_t) if w_t < 0 else 0
        debt_institute = abs(w_i) if w_i < 0 else 0
        # FIX: Bug 16 - report unpaid discounted tuition, not only negative wallets.
        total_debt = calculate_student_debt(db, student)

        # Only include students with debt
        if total_debt > 0:
            res.append(
                {
                    "student_id": student.id,
                    "student_name": display_name(student, "نامشخص"),
                    "amount": total_debt,
                    "date": "-",
                    "description": "بدهی",
                    "payment_method": "-",
                }
            )
    return res


# Test endpoint to verify debt calculation


@router.get("/reports/debtors/excel")
def get_debtors_excel(
    branch_id: Optional[int] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    _: str = Depends(check_admin_access)
):
    resolved_branch = get_user_branch_filter(db, authorization, branch_id)
    query = db.query(Student)
    if resolved_branch is not None:
        query = query.filter(Student.branch_id == resolved_branch)
    all_students = query.all()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "لیست بدهکاران"
    ws.views.sheetView[0].rightToLeft = True
    
    headers = ["شناسه", "نام و نام خانوادگی", "بدهی به معلم (تومان)", "بدهی به آموزشگاه (تومان)", "کل بدهی (تومان)", "تلفن همراه", "تلفن والدین"]
    ws.append(headers)
    
    header_fill = PatternFill(start_color="00695C", end_color="00695C", fill_type="solid")
    header_font = Font(name="Tahoma", size=11, bold=True, color="FFFFFF")
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        
    row_num = 2
    for student in all_students:
        w_t = student.wallet_teacher if student.wallet_teacher is not None else 0
        w_i = student.wallet_institute if student.wallet_institute is not None else 0

        debt_teacher = abs(w_t) if w_t < 0 else 0
        debt_institute = abs(w_i) if w_i < 0 else 0
        # FIX: Bug 16 - report unpaid discounted tuition, not only negative wallets.
        total_debt = calculate_student_debt(db, student)

        if total_debt > 0:
            row_data = [
                student.id,
                display_name(student, "نامشخص"),
                debt_teacher,
                debt_institute,
                total_debt,
                student.student_mobile,
                student.parent_mobile or ""
            ]
            ws.append(row_data)
            
            ws.cell(row=row_num, column=3).number_format = '#,##0'
            ws.cell(row=row_num, column=4).number_format = '#,##0'
            ws.cell(row=row_num, column=5).number_format = '#,##0'
            
            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=row_num, column=col_num)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = Font(name="Tahoma", size=10)
                
            row_num += 1
            
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
        
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=debtors_list.xlsx"}
    )


# ==========================================
# 🆕 گزارش‌گیری جدید و صورت‌حساب دانش‌آموز 🆕
# ==========================================

def get_current_shamsi_date():
    # FIX H3-B3: unified on the central converter (was a second ~30-line day-counting implementation).
    from today_summary import gregorian_to_jalali  # lazy import, same pattern as routers/analytics.py
    return gregorian_to_jalali(datetime.date.today())


def get_logged_in_teacher(db: Session, authorization: Optional[str]) -> Optional[Teacher]:
    # FIX: مقاوم به تغییر موبایل – اول teacher_id مستقیم، بعد fallback به mobile
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1]
    # FIX: از helper جدید برای JWT + fallback استفاده کن
    try:
        from dependencies import get_session_from_token
        session, _ = get_session_from_token(db, token)
    except Exception:
        session = db.query(UserSession).filter(UserSession.token == token).first()
    if not session:
        return None
    # اگر teacher_id مستقیم ذخیره شده باشد (فیکس Bug 3)
    if getattr(session, "teacher_id", None):
        t = db.query(Teacher).filter(Teacher.id == session.teacher_id).first()
        if t:
            return t
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or user.role != "teacher":
        return None
    teacher = db.query(Teacher).filter(Teacher.mobile == user.username).first()
    if teacher:
        return teacher
    # فقط برای کاربر معلم: ممکن است session.user_id در مهاجرت قدیمی همان Teacher.id باشد
    return db.query(Teacher).filter(Teacher.id == session.user_id).first()


@router.get("/reports/financial_summary")
def get_financial_summary(
    user_type: str,  # "institute" or "teacher"
    teacher_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    branch_id: Optional[int] = None,  # Added branch_id 🆕
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    sub_role: str = Depends(check_user_login)
):
    # FIX (L14/Y4): تکمیل تله — شاگرد/ولی 403؛ معلم در ادامه به خلاصه‌ی خودش قفل می‌شود (کد موجود).
    if sub_role not in ("admin", "secretary", "teacher"):
        raise HTTPException(status_code=403, detail="شما دسترسی لازم برای مشاهده خلاصه مالی را ندارید")
    resolved_branch = get_user_branch_filter(db, authorization, branch_id)
    # بررسی و محدودسازی در صورتی که کاربر جاری معلم باشد
    logged_teacher = get_logged_in_teacher(db, authorization)
    if logged_teacher:
        user_type = "teacher"
        teacher_id = logged_teacher.id

    curr_jy, curr_jm, _ = get_current_shamsi_date()
    if not year:
        year = curr_jy
    if not month:
        month = curr_jm

    month_prefix = f"{year}/{month:02d}/%"
    year_prefix = f"{year}/%"

    start_date = f"{year}/{month:02d}/01"
    end_date = f"{year}/{month:02d}/31"
    
    start_year_date = f"{year}/01/01"
    end_year_date = f"{year}/12/30"

    if user_type == "institute":
        # گزارش ماهانه آموزشگاه با استفاده از توابع متمرکز
        total_m = calculate_institute_session_revenue(db, start_date, end_date, resolved_branch)
        collected_m = calculate_institute_collected_revenue(db, start_date, end_date, resolved_branch)
        uncollected_m = max(0, total_m - collected_m)

        # گزارش سالانه آموزشگاه
        total_y = calculate_institute_session_revenue(db, start_year_date, end_year_date, resolved_branch)
        collected_y = calculate_institute_collected_revenue(db, start_year_date, end_year_date, resolved_branch)
        uncollected_y = max(0, total_y - collected_y)

        return {
            "user_type": "institute",
            "year": year,
            "month": month,
            "monthly": {
                "total": int(total_m),
                "collected": int(collected_m),
                "uncollected": int(uncollected_m)
            },
            "yearly": {
                "total": int(total_y),
                "collected": int(collected_y),
                "uncollected": int(uncollected_y)
            }
        }

    elif user_type == "teacher":
        if not teacher_id:
            raise HTTPException(status_code=400, detail="شناسه معلم الزامی است")

        teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="معلم یافت نشد")

        # محاسبات ماهانه و سالانه معلم با توابع متمرکز
        total_m = calculate_teacher_session_revenue(db, teacher_id, start_date, end_date)
        collected_m = calculate_teacher_collected_revenue(db, teacher_id, start_date, end_date)
        uncollected_m = max(0, total_m - collected_m)

        total_y = calculate_teacher_session_revenue(db, teacher_id, start_year_date, end_year_date)
        collected_y = calculate_teacher_collected_revenue(db, teacher_id, start_year_date, end_year_date)
        uncollected_y = max(0, total_y - collected_y)

        return {
            "user_type": "teacher",
            "teacher_id": teacher_id,
            "teacher_name": display_name(teacher, "نامشخص"),
            "year": year,
            "month": month,
            "monthly": {
                "total": int(total_m),
                "collected": int(collected_m),
                "uncollected": int(uncollected_m)
            },
            "yearly": {
                "total": int(total_y),
                "collected": int(collected_y),
                "uncollected": int(uncollected_y)
            }
        }


@router.get("/reports/student_statement")
def get_student_statement(
    student_id: int,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    role: str = Depends(check_user_login)
):
    # FIX (L14/Y1): صورت‌حساب/چاپ هر شاگرد — فقط ادمین/منشی، معلمِ درگیر، خودِ شاگرد/ولیِ همان فرزند.
    check_student_access(student_id, authorization, db, role)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="دانش‌آموز یافت نشد")

    # FIX: Bug 12 - exclude archived Transaction rows from this active view.
    total_paid_institute = db.query(func.sum(Transaction.amount)).filter(Transaction.is_deleted == False, Transaction.is_reversed == False).filter(
        Transaction.student_id == student_id,
        Transaction.target_wallet == "institute",
        Transaction.amount > 0
    ).scalar() or 0

    wallet_inst = student.wallet_institute if student.wallet_institute is not None else 0
    total_debt_institute = abs(wallet_inst) if wallet_inst < 0 else 0

    settings = db.query(InstituteSettings).first()
    if not settings:
        settings = InstituteSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return {
        "student_id": student.id,
        "student_name": display_name(student, "نامشخص"),
        "student_code": student.student_code or str(100000 + student.id),
        "total_paid_institute": int(total_paid_institute),
        "total_debt_institute": int(total_debt_institute),
        # FIX: Bug 16 - expose contractual debt separately; do not assign all tuition to one wallet.
        "total_debt": calculate_student_debt(db, student),
        "institute_card_number": settings.card_number or "۶۰۳۷۹۹۷۹۷۹۷۹۷۹۷۹",
        "institute_name": settings.name,
        "address": settings.address,
        "phone": settings.phone,
        "footer_text": settings.footer_text
    }


@router.get("/reports/student_statement/print", response_class=HTMLResponse)
def print_student_statement(
    student_id: int,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    role: str = Depends(check_user_login)
):
    # FIX (L14/Y1): صورت‌حساب/چاپ هر شاگرد — فقط ادمین/منشی، معلمِ درگیر، خودِ شاگرد/ولیِ همان فرزند.
    check_student_access(student_id, authorization, db, role)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return "<h3>دانش‌آموز یافت نشد</h3>"

    # FIX: Bug 12 - exclude archived Transaction rows from this active view.
    total_paid_institute = db.query(func.sum(Transaction.amount)).filter(Transaction.is_deleted == False, Transaction.is_reversed == False).filter(
        Transaction.student_id == student_id,
        Transaction.target_wallet == "institute",
        Transaction.amount > 0
    ).scalar() or 0

    wallet_inst = student.wallet_institute if student.wallet_institute is not None else 0
    total_debt_institute = abs(wallet_inst) if wallet_inst < 0 else 0

    settings = db.query(InstituteSettings).first()
    if not settings:
        settings = InstituteSettings()

    card_num = settings.card_number or "۶۰۳۷۹۹۷۹۷۹۷۹۷۹۷۹"
    inst_name = settings.name
    address = settings.address
    phone = settings.phone
    footer = settings.footer_text

    current_date = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>صورت‌حساب آموزشگاه</title>
        <style>
            @font-face {{
                font-family: 'Tahoma';
                src: local('Tahoma');
            }}
            body {{
                font-family: 'Tahoma', sans-serif;
                margin: 0;
                padding: 10px;
                color: #212121;
                background-color: #ffffff;
                font-size: 13px;
                line-height: 1.6;
            }}
            .ticket {{
                max-width: 320px;
                margin: 0 auto;
                padding: 15px;
                border: 1px dashed #00695C;
                border-radius: 8px;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px dashed #00695C;
                padding-bottom: 10px;
                margin-bottom: 15px;
            }}
            .header h2 {{
                margin: 5px 0;
                font-size: 16px;
                color: #00695C;
            }}
            .header p {{
                margin: 3px 0;
                font-size: 11px;
                color: #666666;
            }}
            .row-info {{
                display: flex;
                justify-content: space-between;
                margin: 8px 0;
                border-bottom: 1px dotted #eeeeee;
                padding-bottom: 4px;
            }}
            .label {{
                font-weight: bold;
                color: #555555;
            }}
            .value {{
                color: #000000;
            }}
            .highlight {{
                color: #D32F2F;
                font-weight: bold;
                font-size: 14px;
            }}
            .success-val {{
                color: #388E3C;
                font-weight: bold;
                font-size: 14px;
            }}
            .footer {{
                text-align: center;
                border-top: 2px dashed #00695C;
                padding-top: 10px;
                margin-top: 20px;
                font-size: 11px;
            }}
            .card-box {{
                background-color: #E8F5E9;
                border: 1px solid #C8E6C9;
                border-radius: 4px;
                padding: 8px;
                margin-top: 10px;
                text-align: center;
            }}
            .card-number {{
                font-weight: bold;
                font-size: 15px;
                color: #2E7D32;
                letter-spacing: 1px;
                margin: 4px 0 0 0;
            }}
            @media print {{
                body {{
                    padding: 0;
                }}
                .ticket {{
                    border: none;
                    max-width: 100%;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="ticket">
            <div class="header">
                <h2>{inst_name}</h2>
                <p>صورت‌حساب رسمی دانش‌آموز</p>
                <p>تاریخ چاپ: {current_date}</p>
            </div>
            
            <div class="row-info">
                <span class="label">نام دانش‌آموز:</span>
                <span class="value">{display_name(student, 'نامشخص')}</span>
            </div>
            <div class="row-info">
                <span class="label">کد دانش‌آموزی:</span>
                <span class="value">{student.student_code or str(100000 + student.id)}</span>
            </div>
            <div class="row-info">
                <span class="label">کد ملی:</span>
                <span class="value">{student.national_code}</span>
            </div>
            
            <div style="margin-top: 15px; border-bottom: 1px solid #00695C; padding-bottom: 5px; font-weight: bold; color: #00695C;">خلاصه تراز مالی آموزشگاه:</div>
            
            <div class="row-info">
                <span class="label">مجموع کل واریزی‌ها:</span>
                <span class="value success-val">{total_paid_institute:,} تومان</span>
            </div>
            <div class="row-info">
                <span class="label">مانده بدهی به آموزشگاه:</span>
                <span class="value highlight">{total_debt_institute:,} تومان</span>
            </div>
            
            <div class="card-box">
                <div class="label" style="color: #2E7D32;">شماره کارت جهت واریز بدهی:</div>
                <p class="card-number">{card_num}</p>
            </div>
            
            <div class="footer">
                <p>{footer}</p>
                <p style="font-size: 9px; color: #888888;">آدرس: {address} | تلفن: {phone}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content


@router.get("/reports/student_profile/print", response_class=HTMLResponse)
def print_student_profile(
    student_id: int,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    role: str = Depends(check_user_login)
):
    # FIX (L14/Y1): صورت‌حساب/چاپ هر شاگرد — فقط ادمین/منشی، معلمِ درگیر، خودِ شاگرد/ولیِ همان فرزند.
    check_student_access(student_id, authorization, db, role)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return "<h3>دانش‌آموز یافت نشد</h3>"

    # FIX: Bug 12 - exclude archived Transaction rows from this active view.
    total_paid_institute = db.query(func.sum(Transaction.amount)).filter(Transaction.is_deleted == False, Transaction.is_reversed == False).filter(
        Transaction.student_id == student_id,
        Transaction.target_wallet == "institute",
        Transaction.amount > 0
    ).scalar() or 0

    wallet_inst = student.wallet_institute if student.wallet_institute is not None else 0
    total_debt_institute = abs(wallet_inst) if wallet_inst < 0 else 0

    teachers_financial = []
    for en in student.enrollments:
        # FIX: Bug 13 - archived enrollment links remain available, but not in active balances.
        if en.is_deleted or not en.course:
            continue
        course = en.course
        teacher = db.query(Teacher).filter(Teacher.id == course.teacher_id).first()
        teacher_name = display_name(teacher, "نامشخص") if teacher else "بدون معلم"
        
        # FIX: Bug 12 - exclude archived Transaction rows from this active view.
        paid_teacher = db.query(func.sum(Transaction.amount)).filter(Transaction.is_deleted == False, Transaction.is_reversed == False).filter(
            Transaction.student_id == student_id,
            Transaction.course_id == course.id,
            Transaction.target_wallet == "teacher",
            Transaction.amount > 0
        ).scalar() or 0
        
        # FIX: Bug 12 - exclude archived Transaction rows from this active view.
        billed_teacher = db.query(func.sum(Transaction.share_teacher)).filter(Transaction.is_deleted == False, Transaction.is_reversed == False).filter(
            Transaction.student_id == student_id,
            Transaction.course_id == course.id,
            Transaction.type == "session_charge"
        ).scalar() or 0
        
        debt_teacher_course = max(0, billed_teacher - paid_teacher)
        
        teachers_financial.append({
            "course_title": course.title,
            "teacher_name": teacher_name,
            "paid": int(paid_teacher),
            "debt": int(debt_teacher_course)
        })

    settings = db.query(InstituteSettings).first()
    if not settings:
        settings = InstituteSettings()

    inst_name = settings.name
    address = settings.address
    phone = settings.phone
    footer = settings.footer_text

    current_date = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")

    teachers_html_rows = ""
    for tf in teachers_financial:
        teachers_html_rows += f"""
        <div class="teacher-block" style="border: 1px solid #e0e0e0; border-radius: 4px; padding: 8px; margin-bottom: 8px; background-color: #fafafa;">
            <div class="row-info" style="font-weight: bold; border-bottom: 1px solid #eee; padding-bottom: 4px; margin-bottom: 4px;">
                <span>{tf['course_title']} ({tf['teacher_name']})</span>
            </div>
            <div class="row-info">
                <span class="label">کل واریزی به معلم:</span>
                <span class="value success-val" style="color: #388E3C; font-weight: bold;">{tf['paid']:,} تومان</span>
            </div>
            <div class="row-info">
                <span class="label">بدهی به معلم:</span>
                <span class="value highlight" style="color: #D32F2F; font-weight: bold;">{tf['debt']:,} تومان</span>
            </div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>خلاصه‌ی اطلاعات دانش‌آموز</title>
        <style>
            @font-face {{
                font-family: 'Tahoma';
                src: local('Tahoma');
            }}
            body {{
                font-family: 'Tahoma', sans-serif;
                margin: 0;
                padding: 10px;
                color: #212121;
                background-color: #ffffff;
                font-size: 13px;
                line-height: 1.6;
            }}
            .ticket {{
                max-width: 450px;
                margin: 0 auto;
                padding: 15px;
                border: 1px dashed #00695C;
                border-radius: 8px;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px dashed #00695C;
                padding-bottom: 10px;
                margin-bottom: 15px;
            }}
            .header h2 {{
                margin: 5px 0;
                font-size: 16px;
                color: #00695C;
            }}
            .header p {{
                margin: 3px 0;
                font-size: 11px;
                color: #666666;
            }}
            .section-title {{
                margin-top: 15px;
                margin-bottom: 8px;
                border-bottom: 1px solid #00695C;
                padding-bottom: 4px;
                font-weight: bold;
                color: #00695C;
            }}
            .row-info {{
                display: flex;
                justify-content: space-between;
                margin: 6px 0;
                border-bottom: 1px dotted #eeeeee;
                padding-bottom: 3px;
            }}
            .label {{
                font-weight: bold;
                color: #555555;
            }}
            .value {{
                color: #000000;
            }}
            .highlight {{
                color: #D32F2F;
                font-weight: bold;
            }}
            .success-val {{
                color: #388E3C;
                font-weight: bold;
            }}
            .footer {{
                text-align: center;
                border-top: 2px dashed #00695C;
                padding-top: 10px;
                margin-top: 20px;
                font-size: 11px;
            }}
            @media print {{
                body {{
                    padding: 0;
                }}
                .ticket {{
                    border: none;
                    max-width: 100%;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="ticket">
            <div class="header">
                <h2>{inst_name}</h2>
                <p>خلاصه اطلاعات هویتی و تراز مالی جدید دانش‌آموز</p>
                <p>تاریخ گزارش: {current_date}</p>
            </div>
            
            <div class="section-title">مشخصات هویتی</div>
            <div class="row-info">
                <span class="label">نام و نام خانوادگی:</span>
                <span class="value" style="font-weight: bold;">{display_name(student, 'نامشخص')}</span>
            </div>
            <div class="row-info">
                <span class="label">کد دانش‌آموزی:</span>
                <span class="value">{student.student_code or str(100000 + student.id)}</span>
            </div>
            <div class="row-info">
                <span class="label">کد ملی:</span>
                <span class="value">{student.national_code}</span>
            </div>
            <div class="row-info">
                <span class="label">نام پدر:</span>
                <span class="value">{student.father_name or "---"}</span>
            </div>
            <div class="row-info">
                <span class="label">تاریخ تولد:</span>
                <span class="value">{student.birth_date or "---"}</span>
            </div>
            <div class="row-info">
                <span class="label">موبایل ۱ (دانش‌آموز):</span>
                <span class="value">{student.student_mobile}</span>
            </div>
            <div class="row-info">
                <span class="label">موبایل ۲ (والدین):</span>
                <span class="value">{student.parent_mobile or "---"}</span>
            </div>
            
            <div class="section-title">تراز مالی آموزشگاه</div>
            <div class="row-info">
                <span class="label">کل واریزی‌ها به آموزشگاه:</span>
                <span class="value success-val">{total_paid_institute:,} تومان</span>
            </div>
            <div class="row-info">
                <span class="label">مانده بدهی به آموزشگاه:</span>
                <span class="value highlight">{total_debt_institute:,} تومان</span>
            </div>
            
            <div class="section-title">تراز مالی معلمان</div>
            {teachers_html_rows if teachers_html_rows else "<p style='color:#888; text-align:center;'>کلاس ثبت‌نام شده‌ای وجود ندارد</p>"}
            
            <div class="footer">
                <p>{footer}</p>
                <p style="font-size: 9px; color: #888888;">آدرس: {address} | تلفن: {phone}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content
