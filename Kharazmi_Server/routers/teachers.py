from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Header, Request, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Union
from sqlalchemy import desc, or_, text, func
import io
import uuid
import os
import datetime
import secrets

import models
from models import (
    Attendance, Course, Enrollment, Grade, InstituteShare, SessionLog, SmsLog, Student, Teacher, Transaction, User, UserSession, Settlement
)
from schemas import (
    HistoryRequest, LoginRequest, TeacherInfo, FullTeacherProfile, StudentCreate, TeacherCreate, CourseCreate, EnrollmentCreate, GradeCreate, GradeItem, AttendanceLogRequest, AttendanceItem, AttendanceSubmitData, SmsSendRequest, ChangePasswordRequest, StudentProfileInfo, FullStudentProfile, TeacherProfileInfo, FullTeacherProfile, ClassReportInfo, ClassStudentData, ClassSessionHistory, FullClassReport, ShareConfigModel, StudentUpdate, TeacherUpdate, PersonListItem, TransactionUpdate, StudentAttendanceHistoryRequest, AdvancedSearchItem, FinanceSubmitData, PrintReceiptRequest, TransactionTestData, SettleRequest, TeacherListItem
)
from dependencies import get_db, check_admin_access, check_admin_or_secretary_access, check_user_login, get_enrollment_tuition_and_discount, SESSION_EXPIRY_DAYS, hash_password, verify_password, limiter, normalize_mobile, validate_image_upload
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from fastapi.responses import StreamingResponse

router = APIRouter()

# FIX: Bug 22 - reuse the same checksum as schemas and online registration.
from validation import is_valid_iranian_national_code


@router.post("/teachers/register")
@limiter.limit("5/hour")
def register_teacher(request: Request, teacher: TeacherCreate, db: Session = Depends(get_db)):
    if not is_valid_iranian_national_code(teacher.national_code):
        raise HTTPException(status_code=400, detail="کد ملی وارد شده معتبر نیست")

    if db.query(Teacher).filter(Teacher.national_code == teacher.national_code).first():
        raise HTTPException(status_code=400, detail="این معلم قبلاً ثبت شده است")

    # FIX(security): یکتایی موبایل
    # FIX H20: نرمال‌سازی قبل از چک یکتایی و ذخیره (خالی مجاز و دست‌نخورده می‌ماند).
    _raw_mob = (teacher.mobile or "").strip()
    teacher_mobile = normalize_mobile(_raw_mob) if _raw_mob else ""
    if _raw_mob and not teacher_mobile:
        raise HTTPException(status_code=400, detail="فرمت شماره موبایل صحیح نیست")
    if db.query(Teacher).filter(Teacher.mobile == teacher_mobile).first():
        raise HTTPException(status_code=409, detail="این شماره موبایل قبلاً ثبت شده است")

    from dependencies import get_next_sequence_value
    next_code = get_next_sequence_value(db, "teacher", 101)

    # FIX(security): پسورد اولیه تصادفی و مستقل از کد ترتیبی حدس‌زدنی؛ فقط همین یک‌بار در پاسخ برمی‌گردد.
    _READABLE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"  # بدون 0/O/1/l/I
    initial_password = "".join(secrets.choice(_READABLE_ALPHABET) for _ in range(8))

    teacher_data = teacher.dict()
    teacher_data["teacher_code"] = next_code
    teacher_data["mobile"] = teacher_mobile
    teacher_data["password"] = hash_password(initial_password) # رمز عبور به صورت هش شده ذخیره می‌شود

    new_teacher = Teacher(**teacher_data, is_approved=False)
    db.add(new_teacher)
    db.commit()
    return {
        "message": f"درخواست ثبت‌نام ارسال شد. کد معلم شما: {next_code}. منتظر تایید مدیر باشید.",
        "id": new_teacher.id,
        "teacher_code": next_code,
        "initial_password": initial_password
    }


@router.get("/teachers/list", response_model=List[TeacherListItem])
def get_all_teachers(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    sub_role: str = Depends(check_user_login),
    # FIX L8: پیجینیشن اختیاری (پاسخ همچنان آرایه‌ی خام است تا اپ قدیمی نشکند؛
    # پیش‌فرضِ بدون‌پارامتر = همه مثل قبل، برای مهاجرت تدریجی اپ به skip/limit).
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=200),
):
    # FIX L14: موبایل در response_model هست (schemas.py) پس مشکل دسترسی است نه فیلد —
    # ادمین/منشی لیست کامل، معلم فقط خودش، بقیه (شاگرد/والد) 403.
    # FIX(security): هرگز ORM خام برنگردان — فقط فیلدهای غیرحساس (بدون password/card_number/national_code).
    if sub_role not in ("admin", "secretary", "teacher"):
        raise HTTPException(status_code=403, detail="شما دسترسی لازم برای مشاهده‌ی لیست معلم‌ها را ندارید")
    q = db.query(Teacher).filter(Teacher.is_deleted == False)
    if sub_role == "teacher":
        from routers.reports import get_logged_in_teacher  # lazy (مثل auth.py؛ جلوگیری از import چرخه‌ای)
        me = get_logged_in_teacher(db, authorization)
        if me is None or me.is_deleted:
            raise HTTPException(status_code=403, detail="نشست معلم معتبر نیست")
        q = q.filter(Teacher.id == me.id)
    # FIX L8: ترتیب قطعی برای پیجینیشن پایدار (قبلاً .all() بدون order بود).
    q = q.order_by(Teacher.id)
    if skip:
        q = q.offset(skip)
    if limit is not None:
        q = q.limit(limit)
    teachers = q.all()
    return [
        TeacherListItem(
            id=t.id,
            first_name=t.first_name or "",
            last_name=t.last_name or "",
            mobile=t.mobile,
            teacher_code=t.teacher_code,
            profile_image=t.profile_image,
            is_approved=bool(t.is_approved),
            is_suspended=bool(t.is_suspended),
        )
        for t in teachers
    ]


# ==========================================
# 4. API های کلاس
# ==========================================


@router.get("/teachers/{teacher_id}/communication_history")
def get_teacher_communication_history(
    teacher_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    sub_role: str = Depends(check_user_login),
):
    """Combined SMS and internal-message history for an authorized profile view."""
    if sub_role not in ("admin", "secretary", "teacher"):
        raise HTTPException(
            status_code=403,
            detail="شما دسترسی لازم برای مشاهده تاریخچه ارتباطات را ندارید",
        )

    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="معلم یافت نشد")

    if sub_role == "teacher":
        from routers.reports import get_logged_in_teacher

        logged_teacher = get_logged_in_teacher(db, authorization)
        if not logged_teacher or logged_teacher.id != teacher_id:
            raise HTTPException(
                status_code=403,
                detail="شما فقط مجاز به مشاهده تاریخچه ارتباطات خودتان هستید",
            )

    from communication_history import build_teacher_communication_history

    return build_teacher_communication_history(db=db, teacher=teacher)


@router.get("/teachers/{teacher_id}/collaboration_summary")
def get_teacher_collaboration_summary(
    teacher_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    _: str = Depends(check_admin_access),
):
    """Informational collaboration summary, admin only, read-only."""
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="معلم یافت نشد")
    from collaboration_summary import build_teacher_collaboration_summary
    return build_teacher_collaboration_summary(db=db, teacher_id=teacher_id)


@router.get("/teachers/{id}/today_summary")
def get_teacher_today_summary(
    id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    sub_role: str = Depends(check_user_login),
):
    """Real-time read-only summary for the logged-in teacher's dashboard."""
    if sub_role != "teacher":
        raise HTTPException(
            status_code=403,
            detail="این خلاصه فقط برای پنل معلم در دسترس است",
        )

    from routers.reports import get_logged_in_teacher

    logged_teacher = get_logged_in_teacher(db, authorization)
    if not logged_teacher or logged_teacher.id != id:
        raise HTTPException(
            status_code=403,
            detail="شما فقط مجاز به مشاهده وضعیت امروز خودتان هستید",
        )

    from today_summary import build_teacher_today_summary

    summary = build_teacher_today_summary(db=db, teacher_id=id)
    if not summary:
        raise HTTPException(status_code=404, detail="معلم یافت نشد")
    return summary


@router.get("/teachers/{teacher_id}/classes")
def get_my_classes(
    teacher_id: int,
    student_name: Optional[str] = None,
    course_name: Optional[str] = None,
    grade_level: Optional[str] = None,
    start_year: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db), 
    sub_role: str = Depends(check_user_login)
):
    # FIX (L14/Y2): تکمیل تله‌ی گارد نصفه — شاگرد/ولی (و نقش ناشناخته) 403؛ فقط کارکنان عبور می‌کنند.
    if sub_role not in ("admin", "secretary", "teacher"):
        raise HTTPException(status_code=403, detail="شما دسترسی لازم برای مشاهده‌ی اطلاعات معلمان را ندارید")
    # بررسی مالکیت اطلاعات توسط مربی
    if sub_role == "teacher":
        from routers.reports import get_logged_in_teacher
        logged_teacher = get_logged_in_teacher(db, authorization)
        if not logged_teacher or logged_teacher.id != teacher_id:
            raise HTTPException(status_code=403, detail="شما فقط مجاز به دیدن کلاس‌های خودتان هستید")

    # Only non-deleted classes belonging to this teacher!
    q = db.query(Course).filter(Course.teacher_id == teacher_id, Course.is_deleted == False)
    
    if student_name:
        search_s = f"%{student_name}%"
        q = q.join(Enrollment).join(Student).filter(
            or_(
                Student.first_name.ilike(search_s),
                Student.last_name.ilike(search_s)
            )
        )
        
    if course_name:
        q = q.filter(Course.title.ilike(f"%{course_name}%"))
        
    if grade_level:
        q = q.filter(Course.grade_level.ilike(f"%{grade_level}%"))
        
    if start_year:
        q = q.join(Enrollment).filter(Enrollment.register_date.like(f"{start_year}%"))

    courses = q.order_by(desc(Course.id)).all()
    result = []

    for c in courses:
        # 2. Get Top 3 Students for Preview
        enrollments = (
            # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
            db.query(Enrollment).filter(Enrollment.is_deleted == False).filter(Enrollment.course_id == c.id).limit(3).all()
        )
        student_names = []

        for en in enrollments:
            st = db.query(Student).filter(Student.id == en.student_id, Student.is_deleted == False).first()
            if st:
                student_names.append(f"{st.first_name} {st.last_name}")

        # 3. Build Result Dictionary
        result.append(
            {
                "id": c.id,
                "title": c.title,
                "code": c.code,
                "grade_level": c.grade_level,
                "is_admin_approved": c.is_admin_approved,
                "is_suspended": c.is_suspended if c.is_suspended is not None else False,
                "students_preview": student_names,  # <--- CRITICAL NEW FIELD
                "bg_color": c.bg_color or "#FFFFFF",
            }
        )

    return result

@router.get("/teachers/{teacher_id}/incomplete_classes")
def get_teacher_incomplete_classes(
    teacher_id: int, 
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db), 
    sub_role: str = Depends(check_user_login)
):
    # FIX (L14/Y2): تکمیل تله‌ی گارد نصفه — شاگرد/ولی (و نقش ناشناخته) 403؛ فقط کارکنان عبور می‌کنند.
    if sub_role not in ("admin", "secretary", "teacher"):
        raise HTTPException(status_code=403, detail="شما دسترسی لازم برای مشاهده‌ی اطلاعات معلمان را ندارید")
    # بررسی مالکیت اطلاعات توسط مربی
    if sub_role == "teacher":
        from routers.reports import get_logged_in_teacher
        logged_teacher = get_logged_in_teacher(db, authorization)
        if not logged_teacher or logged_teacher.id != teacher_id:
            raise HTTPException(status_code=403, detail="شما فقط مجاز به دیدن کلاس‌های خودتان هستید")

    # کلاس‌هایی که هنوز ثبت‌نامی ندارند و تایید هم نشده‌اند (ناقص)
    courses = db.query(Course).filter(Course.teacher_id == teacher_id, Course.is_admin_approved == False, Course.is_deleted == False).all()
    result = []
    for c in courses:
        # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
        enroll_count = db.query(Enrollment).filter(Enrollment.is_deleted == False).filter(Enrollment.course_id == c.id).count()
        if enroll_count == 0:
            result.append({
                "id": c.id,
                "title": c.title,
                "code": c.code,
                "grade_level": c.grade_level,
                "bg_color": c.bg_color or "#FFFFFF",
            })
    return result


# ==========================================
# 11. API تغییر رمز عبور
# ==========================================
class ChangePasswordRequest(BaseModel):
    mobile: str
    old_password: str
    new_password: str


@router.get("/teachers/{id}/full_profile")
def get_teacher_full_profile(
    id: int, 
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db), 
    sub_role: str = Depends(check_user_login)
):
    # FIX (L14/Y2): تکمیل تله‌ی گارد نصفه — شاگرد/ولی (و نقش ناشناخته) 403؛ فقط کارکنان عبور می‌کنند.
    if sub_role not in ("admin", "secretary", "teacher"):
        raise HTTPException(status_code=403, detail="شما دسترسی لازم برای مشاهده‌ی اطلاعات معلمان را ندارید")
    # بررسی مالکیت اطلاعات توسط مربی
    if sub_role == "teacher":
        from routers.reports import get_logged_in_teacher
        logged_teacher = get_logged_in_teacher(db, authorization)
        if not logged_teacher or logged_teacher.id != id:
            raise HTTPException(status_code=403, detail="شما فقط مجاز به دیدن اطلاعات خودتان هستید")

    # 1. اطلاعات پایه
    teacher = db.query(Teacher).filter(Teacher.id == id, Teacher.is_deleted == False).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="معلم یافت نشد")

    # 2. پیدا کردن کلاس‌ها
    courses = db.query(Course).filter(Course.teacher_id == id).all()

    # 3. محاسبه آمار
    total_students = 0
    total_revenue = 0
    class_names = []

    for c in courses:
        class_names.append(f"{c.title} ({c.code}) - {c.grade_level}")

        # تعداد شاگردان و درآمد این کلاس
        # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
        enrollments = db.query(Enrollment).filter(Enrollment.is_deleted == False).filter(Enrollment.course_id == c.id).all()
        total_students += len(enrollments)

        # جمع مبالغ پرداختی شاگردان این کلاس
        for en in enrollments:
            total_revenue += en.total_paid

    # 4. خلاصه همکاری (فقط برای admin، بدون تغییر منطق مالی - فقط اطلاعات خام)
    collaboration = None
    if sub_role == "admin":
        try:
            from collaboration_summary import build_teacher_collaboration_summary
            collaboration = build_teacher_collaboration_summary(db=db, teacher_id=id)
        except Exception:
            collaboration = None

    return FullTeacherProfile(
        info=TeacherProfileInfo(
            name=f"{teacher.first_name} {teacher.last_name}",
            mobile=teacher.mobile,
            national_code=teacher.national_code,
            status="فعال" if teacher.is_approved else "در انتظار تایید",
            profile_image=teacher.profile_image,
            teacher_code=teacher.teacher_code,
        ),
        total_students=total_students,
        total_revenue=total_revenue,
        active_classes_count=len(courses),
        classes=class_names,
        collaboration_summary=collaboration,
    )


# ==========================================
# 14. API های مدیریت نمرات (Grading System)
# ==========================================


# ثبت نمره توسط معلم


@router.get("/teachers/{teacher_id}")
def get_teacher_profile(teacher_id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(None), sub_role: str = Depends(check_user_login)):
    # FIX (L14/Y2): پروفایل کامل معلم (شامل شماره‌کارت!) — فقط ادمین/منشی + خودِ معلم. شاگرد/ولی 403.
    if sub_role not in ("admin", "secretary", "teacher"):
        raise HTTPException(status_code=403, detail="شما دسترسی لازم برای مشاهده‌ی اطلاعات معلمان را ندارید")
    if sub_role == "teacher":
        from routers.reports import get_logged_in_teacher  # lazy (جلوگیری از import چرخه‌ای)
        logged_teacher = get_logged_in_teacher(db, authorization)
        if not logged_teacher or logged_teacher.id != teacher_id:
            raise HTTPException(status_code=403, detail="شما فقط مجاز به دیدن اطلاعات خودتان هستید")
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id, Teacher.is_deleted == False).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="معلم یافت نشد")
    return {
        "id": teacher.id,
        "first_name": teacher.first_name,
        "last_name": teacher.last_name,
        "father_name": teacher.father_name,
        "national_code": teacher.national_code,
        "birth_date": teacher.birth_date,
        "mobile": teacher.mobile,
        "home_phone": teacher.home_phone,
        "marital_status": teacher.marital_status,
        "gender": teacher.gender,
        "employment_type": teacher.employment_type,
        "card_number": teacher.card_number,
        "version": teacher.version if teacher.version is not None else 1
    }


@router.put("/teachers/update/{teacher_id}")
def update_teacher(teacher_id: int, data: TeacherUpdate, db: Session = Depends(get_db), current_username_or_role: str = Depends(check_admin_or_secretary_access)):
    # استفاده از قفل ردیف دیتابیسی برای امنیت نسخه و تداخل
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id, Teacher.is_deleted == False).with_for_update().first()
    if not teacher:
        raise HTTPException(status_code=404, detail="معلم یافت نشد")

    # تایید مجوزها: اگر مربی تایید شده باشد، خودش دیگر نمی‌تواند مشخصات خود را ویرایش کند
    if current_username_or_role == "teacher" and teacher.is_approved:
        raise HTTPException(status_code=403, detail="مشخصات شما تایید نهایی شده است و دیگر قابل تغییر نیست. برای اصلاح به ادمین مراجعه کنید.")

    # بررسی قفل خوش‌بینانه (Optimistic Locking) برای جلوگیری از هم‌پوشانی ویرایش‌ها
    # FIX L11: version اجباری است — حذف آن از درخواست، گارد را دور می‌زد (اپ می‌فرستد، پس سازگار است).
    if data.version is None:
        raise HTTPException(status_code=400, detail="نسخه‌ی رکورد (version) اجباری است؛ ابتدا رکورد را مجدد بخوانید و دوباره تلاش کنید")
    if data.version is not None:
        current_ver = teacher.version if teacher.version is not None else 1
        if data.version != current_ver:
            raise HTTPException(
                status_code=409, 
                detail="این اطلاعات توسط شخص دیگری تغییر یافته است. لطفاً صفحه را مجدداً بارگذاری کنید."
            )

    # Validation
    if data.first_name is not None and not data.first_name.strip():
        raise HTTPException(status_code=400, detail="نام نمی‌تواند خالی باشد")
    if data.last_name is not None and not data.last_name.strip():
        raise HTTPException(status_code=400, detail="نام خانوادگی نمی‌تواند خالی باشد")
        
    if data.national_code is not None:
        nc = data.national_code.strip()
        # FIX: Bug 22 - edits must pass the checksum too, not just a length check.
        if not is_valid_iranian_national_code(nc):
            raise HTTPException(status_code=400, detail="کد ملی وارد شده معتبر نیست")
        exists = db.query(Teacher).filter(Teacher.national_code == nc, Teacher.id != teacher_id).first()
        if exists:
            raise HTTPException(status_code=400, detail="کد ملی وارد شده قبلاً ثبت شده است")
            
    norm_teacher_mobile = None
    if data.mobile is not None:
        # FIX H20: نرمال‌سازی جایگزین رد خام H1؛ clash و ذخیره با مقدار canonical (خالی مثل قبل 400).
        mob = normalize_mobile(data.mobile)
        if not mob:
            raise HTTPException(status_code=400, detail="شماره موبایل باید ۱۰ یا ۱۱ رقم باشد")
        norm_teacher_mobile = mob
        exists = db.query(Teacher).filter(Teacher.mobile == mob, Teacher.id != teacher_id).first()
        if exists:
            raise HTTPException(status_code=400, detail="شماره موبایل وارد شده قبلاً ثبت شده است")

    _old_mob = teacher.mobile  # FIX H20-B3: برای سینک سایه (قبل از بازنویسی حلقه)

    # Update only provided fields
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "version":
            continue
        if key == "password":
            # FIX(security): هرگز plaintext ذخیره نکن؛ None/خالی = فیلد دست‌نخورده می‌ماند.
            if value and str(value).strip():
                setattr(teacher, key, hash_password(str(value).strip()))
            continue
        if value is not None and isinstance(value, str):
            setattr(teacher, key, value.strip())
        else:
            setattr(teacher, key, value)

    # FIX H20: حلقه‌ی بالا خام-strip ذخیره می‌کند؛ بازنویسی با مقدار نرمال.
    if norm_teacher_mobile is not None:
        teacher.mobile = norm_teacher_mobile

    # FIX H20-B3: سینک username سایه با موبایل جدید (الگوی change_mobile/admin-creds) — قبلاً واگرا می‌ماند و ریزالورها می‌شکستند.
    if norm_teacher_mobile is not None and norm_teacher_mobile != _old_mob:
        _shadow = db.query(User).filter(User.username == _old_mob, User.role == "teacher").first()
        if _shadow is None:
            _sess = db.query(UserSession).filter(UserSession.teacher_id == teacher_id).order_by(UserSession.id.desc()).first()
            if _sess is not None:
                _shadow = db.query(User).filter(User.id == _sess.user_id, User.role == "teacher").first()
        if _shadow is not None:
            _uclash = db.query(User).filter(User.username == norm_teacher_mobile, User.id != _shadow.id).first()
            if _uclash is not None:
                raise HTTPException(status_code=409, detail="این شماره موبایل قبلاً در سیستم ثبت شده است")
            _shadow.username = norm_teacher_mobile

    # افزایش نسخه به ازای ویرایش موفق
    if teacher.version is None:
        teacher.version = 1
    teacher.version += 1

    db.commit()
    return {"message": "اطلاعات معلم با موفقیت بروزرسانی شد"}


# ==========================================
# Profile Image Upload Endpoints
# ==========================================
import uuid


@router.post("/teachers/{id}/upload_photo")
async def upload_teacher_photo(id: int, file: UploadFile = File(...), db: Session = Depends(get_db), authorization: Optional[str] = Header(None), sub_role: str = Depends(check_user_login)):
    teacher = db.query(Teacher).filter(Teacher.id == id, Teacher.is_deleted == False).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="معلم یافت نشد")
    # FIX M25-IDOR: فقط ادمین/منشی یا خودِ معلم.
    if sub_role not in ("admin", "secretary"):
        if sub_role != "teacher":
            raise HTTPException(status_code=403, detail="شما مجاز به تغییر عکس این معلم نیستید")
        from routers.reports import get_logged_in_teacher  # lazy (مثل auth.py؛ جلوگیری از import چرخه‌ای)
        _t = get_logged_in_teacher(db, authorization)
        if _t is None or _t.id != id:
            raise HTTPException(status_code=403, detail="شما مجاز به تغییر عکس این معلم نیستید")
        
    # Read file and validate size
    MAX_SIZE = 5 * 1024 * 1024 # 5 MB
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="حجم فایل نباید بیشتر از ۵ مگابایت باشد")
        
    # FIX M25: پسوند + magic bytes (فایل غیرعکس با پسوند جعلی رد می‌شود).
    file_ext = validate_image_upload(file.filename, contents)
        
    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    filepath = os.path.join("uploads/profiles", unique_filename)
    
    # Write to disk
    with open(filepath, "wb") as f_out:
        f_out.write(contents)
        
    # Delete old file
    if teacher.profile_image:
        old_path = os.path.join("uploads/profiles", teacher.profile_image)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
                
    teacher.profile_image = unique_filename
    db.commit()
    
    return {
        "message": "عکس پروفایل معلم با موفقیت آپلود شد",
        "profile_image": unique_filename,
        "url": f"uploads/profiles/{unique_filename}"
    }


# ==========================================
# Parent Contacts Directory Endpoint
# ==========================================


@router.get("/teachers/list/excel")
def get_teachers_excel(db: Session = Depends(get_db), _: str = Depends(check_admin_or_secretary_access)):
    teachers = db.query(Teacher).filter(Teacher.is_deleted == False).all()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "لیست معلمان"
    ws.views.sheetView[0].rightToLeft = True
    
    headers = ["شناسه", "نام و نام خانوادگی", "کد ملی", "شماره همراه", "تلفن ثابت", "شماره کارت", "نوع استخدام", "کلاس‌های تدریسی", "کل درآمد (تومان)"]
    ws.append(headers)
    
    header_fill = PatternFill(start_color="00695C", end_color="00695C", fill_type="solid")
    header_font = Font(name="Tahoma", size=11, bold=True, color="FFFFFF")
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        
    row_num = 2
    for t in teachers:
        courses = db.query(Course).filter(Course.teacher_id == t.id).all()
        course_titles = ", ".join([c.title for c in courses]) if courses else "ندارد"
        
        course_ids = [c.id for c in courses]
        total_rev = 0
        if course_ids:
            # FIX: Bug 14 - exclude archived SessionLog rows from this active view.
            sessions = db.query(SessionLog).filter(SessionLog.is_deleted == False).filter(SessionLog.course_id.in_(course_ids)).all()
            # FIX: H6(A2) - درآمد معلم از جلسه = مبلغ قراردادی + جریمه‌ی غایبین غیرموجه.
            total_rev = sum((s.final_teacher_cost or 0) + (s.absent_penalty_teacher or 0) for s in sessions)

        row_data = [
            t.id,
            f"{t.first_name} {t.last_name}",
            t.national_code,
            t.mobile,
            t.home_phone or "",
            t.card_number or "",
            t.employment_type or "",
            course_titles,
            total_rev
        ]
        ws.append(row_data)
        
        ws.cell(row=row_num, column=9).number_format = '#,##0'
        
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
        headers={"Content-Disposition": "attachment; filename=teachers_list.xlsx"}
    )


@router.get("/teachers/{teacher_id}/pending_settlement")
def get_pending_settlement(
    teacher_id: int, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None, 
    db: Session = Depends(get_db), 
    authorization: Optional[str] = Header(None),
    sub_role: str = Depends(check_user_login)
):
    # FIX (L14/Y2): طلب/تسویه‌ی معلم — فقط ادمین/منشی + خودِ معلم. شاگرد/ولی 403.
    if sub_role not in ("admin", "secretary", "teacher"):
        raise HTTPException(status_code=403, detail="شما دسترسی لازم برای مشاهده‌ی اطلاعات معلمان را ندارید")
    if sub_role == "teacher":
        from routers.reports import get_logged_in_teacher  # lazy (جلوگیری از import چرخه‌ای)
        logged_teacher = get_logged_in_teacher(db, authorization)
        if not logged_teacher or logged_teacher.id != teacher_id:
            raise HTTPException(status_code=403, detail="شما فقط مجاز به دیدن اطلاعات خودتان هستید")
    # 1. پیدا کردن معلم
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="معلم یافت نشد")

    # کیف پول واحد معلم: جمع مبالغ تسویه‌شده (برای نمایش در کنار طلب فعلی)
    settled_total = sum((s.total_amount or 0) for s in db.query(Settlement).filter(Settlement.teacher_id == teacher_id).all())

    # 2. پیدا کردن تمام کلاس‌های این معلم
    courses = db.query(Course).filter(Course.teacher_id == teacher_id).all()
    course_ids = [c.id for c in courses]
    
    if not course_ids:
        return {"teacher_id": teacher_id, "teacher_name": f"{teacher.first_name} {teacher.last_name}", "total_amount": 0, "session_count": 0, "settled_total_amount": settled_total, "earned_total_amount": settled_total, "pending_sessions": []}
        
    # 3. پیدا کردن تمام جلسات برگزار شده در این کلاس‌ها
    # FIX H3-B3: boundaries may be Jalali or Gregorian — parse and filter in Python
    # (identical behavior for Gregorian input, fixes Jalali input).
    from today_summary import parse_project_date  # lazy, same pattern as routers/analytics.py
    start_day = parse_project_date(start_date) if start_date else None
    end_day = parse_project_date(end_date) if end_date else None
    def _in_range(value):
        parsed = parse_project_date(value)
        if parsed is None:
            return False
        if start_day is not None and parsed < start_day:
            return False
        if end_day is not None and parsed > end_day:
            return False
        return True
    # FIX: Bug 14 - exclude archived SessionLog rows from this active view.
    q_sessions = db.query(SessionLog).filter(SessionLog.is_deleted == False).filter(SessionLog.course_id.in_(course_ids))

    sessions = [s for s in q_sessions.all() if _in_range(s.date)]
    session_map = {s.id: s for s in sessions}
    session_ids = list(session_map.keys())
    
    if not session_ids:
        return {"teacher_id": teacher_id, "teacher_name": f"{teacher.first_name} {teacher.last_name}", "total_amount": 0, "session_count": 0, "settled_total_amount": settled_total, "earned_total_amount": settled_total, "pending_sessions": []}
        
    # 4. پیدا کردن تمام حضور و غیاب‌های تسویه نشده دانش‌آموزان حاضر/تاخیر در این جلسات
    attendances = (
        db.query(Attendance)
        .filter(
            Attendance.session_id.in_(session_ids),
            Attendance.is_billed == False,
            Attendance.status.in_(["Present", "Late"])
        )
        .all()
    )
    
    # 5. محاسبه سهم معلم برای هر حضور غیاب
    course_map = {c.id: c for c in courses}
    pending_sessions = {}  # session_id -> {"date", "class_title", "amount", "present_count"}
    
    for att in attendances:
        sess = session_map[att.session_id]
        cls = course_map[sess.course_id]
        
        if sess.id not in pending_sessions:
            pending_sessions[sess.id] = {
                "session_id": sess.id,
                "date": sess.date,
                "class_title": cls.title,
                # FIX: H6(A2) - طلب معلم از جلسه = مبلغ قراردادی + جریمه‌ی غایبین غیرموجه.
                "amount": (sess.final_teacher_cost or 0) + (sess.absent_penalty_teacher or 0),
                "present_count": 0,
                "penalty_only": False
            }
        pending_sessions[sess.id]["present_count"] += 1

    # FIX H8-gap/follow-up: جلسات تماماً-غایب با جریمه‌ی باز هم طلب‌اند (همان منطق دوشاخه‌ی settle) —
    # با پرچم penalty_only تا در UI با شهریه‌ی عادی اشتباه نشود (حاضر صفر، مبلغ فقط جریمه).
    for _sid, _sess in session_map.items():
        if _sid not in pending_sessions and (_sess.absent_penalty_teacher or 0) > 0 and not _sess.is_penalty_settled:
            _cls = course_map[_sess.course_id]
            pending_sessions[_sid] = {
                "session_id": _sid,
                "date": _sess.date,
                "class_title": _cls.title,
                "amount": (_sess.final_teacher_cost or 0) + (_sess.absent_penalty_teacher or 0),
                "present_count": 0,
                "penalty_only": True,
            }
        
    session_list = list(pending_sessions.values())
    total_amount = sum(item["amount"] for item in session_list)
    
    return {
        "teacher_id": teacher_id,
        "teacher_name": f"{teacher.first_name} {teacher.last_name}",
        "total_amount": total_amount,
        "session_count": len(session_list),
        "settled_total_amount": settled_total,
        "earned_total_amount": settled_total + total_amount,
        "pending_sessions": sorted(session_list, key=lambda x: x["date"], reverse=True)
    }


@router.post("/teachers/{teacher_id}/settle")
def settle_teacher_sessions(
    teacher_id: int,
    req: SettleRequest,
    db: Session = Depends(get_db),
    admin_sub_role: str = Depends(check_admin_access),
    authorization: Optional[str] = Header(None)
):
    # این عملیات فقط برای ادمین مجاز است (dependency بررسی می‌کند)
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="معلم یافت نشد")

    if not req.session_ids:
        raise HTTPException(status_code=400, detail="لیست جلسات برای تسویه نمی‌تواند خالی باشد")

    # 1. واکشی اطلاعات حضور و غیاب‌های تسویه نشده این جلسات برای مربی
    courses = db.query(Course).filter(Course.teacher_id == teacher_id).all()
    course_ids = [c.id for c in courses]

    if not course_ids:
        raise HTTPException(status_code=400, detail="این معلم هیچ کلاسی ندارد")

    # FIX: Bug 14 - exclude archived SessionLog rows from this active view.
    sessions = db.query(SessionLog).filter(SessionLog.is_deleted == False).filter(SessionLog.id.in_(req.session_ids), SessionLog.course_id.in_(course_ids)).all()
    session_ids = [s.id for s in sessions]

    if not session_ids:
        raise HTTPException(status_code=400, detail="جلسه معتبری برای تسویه یافت نشد")

    # FIX H8-P1 (strict): حتی یک جلسه‌ی از قبل تسویه‌شده در لیست ⇒ کل درخواست 400، قبل از هر محاسبه.
    # جلسه «کاملاً تسویه‌شده» = نه حضور بازی دارد (ردیف Present/Late تسویه‌نشده) نه جریمه‌ی بازی
    # (absent_penalty_teacher>0 با is_penalty_settled=False)؛ جلسه با حداقل یک بخشِ باز قابل انتخاب است.
    # (FIX H8-gap: شاخه‌ی جریمه، جلسه‌ی تماماً-غایب را هم قابل تسویه می‌کند — قبلاً با همین گیت 400 می‌گرفت.)
    unbilled_session_ids = {
        r[0] for r in db.query(Attendance.session_id).filter(
            Attendance.session_id.in_(session_ids),
            Attendance.is_billed == False,
            Attendance.status.in_(["Present", "Late"])
        ).distinct().all()
    }
    penalty_open_ids = {
        s.id for s in sessions
        if (s.absent_penalty_teacher or 0) > 0 and not s.is_penalty_settled
    }
    settled_in_list = sorted(set(session_ids) - unbilled_session_ids - penalty_open_ids)
    if settled_in_list:
        raise HTTPException(status_code=400, detail=f"جلسه(های) {settled_in_list} قبلاً تسویه شده‌اند؛ لطفاً آن‌ها را از لیست حذف کنید")

    attendances = (
        db.query(Attendance)
        .filter(
            Attendance.session_id.in_(session_ids),
            Attendance.is_billed == False,
            Attendance.status.in_(["Present", "Late"])
        )
        .all()
    )

    # (FIX H8-gap: خالی‌بودن attendances به‌تنهایی دیگر به معنی «چیزی برای تسویه نیست» نیست —
    # جلسه‌ی تماماً-غایب فقط جریمه دارد؛ چون گیت بالا پاس شده، این شاخه عملاً unreachable است.)
    if not attendances and not penalty_open_ids:
        raise HTTPException(status_code=400, detail="هیچ جلسه تسویه نشده‌ای برای این معلم یافت نشد")

    # 2. محاسبه مبلغ تسویه بر اساس فیلد کلاس
    # FIX: H6(A2) - مبلغ تسویه = مبالغ قراردادی + جریمه‌ی غایبین غیرموجه (سطح-جلسه؛ برای
    # تماماً-غایب همان absent_penalty_teacher است چون final_teacher_cost صفر دارد).
    # (FIX H8-P1: چون گیت بالا پاس شده، هر جلسه حداقل یک بخشِ باز (حضور یا جریمه) دارد.)
    total_amount = sum((s.final_teacher_cost or 0) + (s.absent_penalty_teacher or 0) for s in sessions)

    # FIX H8-P4 (anti-double-click): آپدیت مشروط به‌جای with_for_update (که روی SQLite بی‌اثر است).
    # فقط سطرهای هنوز-تسویه‌نشده فلیپ می‌خورند؛ مغایرت rowcount یعنی ریکوئست موازی همین‌الان تسویه‌شان کرد.
    expected_rows = len(attendances)
    updated_rows = (
        db.query(Attendance)
        .filter(
            Attendance.session_id.in_(session_ids),
            Attendance.is_billed == False,
            Attendance.status.in_(["Present", "Late"])
        )
        .update({Attendance.is_billed: True}, synchronize_session=False)
    )
    if updated_rows != expected_rows:
        db.rollback()
        raise HTTPException(status_code=409, detail="تسویه هم‌زمان انجام شد؛ لطفاً صفحه را رفرش کنید")

    # FIX H8-gap/P4b: فلیپ مشروط فلگ جریمه با همان فلسفه‌ی P4 — روی مسیر تماماً-غایب،
    # گارد rowcount بالا خلأ است (۰=۰) پس بدون این چک، دو ریکوئست موازی جریمه را دوباره می‌پرداختند.
    if penalty_open_ids:
        updated_pen = (
            db.query(SessionLog)
            .filter(SessionLog.id.in_(sorted(penalty_open_ids)), SessionLog.is_penalty_settled == False)
            .update({SessionLog.is_penalty_settled: True}, synchronize_session=False)
        )
        if updated_pen != len(penalty_open_ids):
            db.rollback()
            raise HTTPException(status_code=409, detail="تسویه هم‌زمان انجام شد؛ لطفاً صفحه را رفرش کنید")

    # FIX H8-P2: settled_by باید ادمینِ همین درخواست باشد، نه هاردکد ۱.
    # همان الگوی get_logged_in_teacher در routers/reports.py؛ چون check_admin_access بالا توکن خراب را
    # از قبل رد کرده، fallback به ۱ عملاً نباید هیچ‌وقت اجرا شود (فقط safety net).
    from dependencies import get_session_from_token  # lazy، مثل reports.py
    settled_by = 1
    if authorization:
        try:
            _parts = authorization.split()
            _token = _parts[1] if len(_parts) == 2 and _parts[0].lower() == "bearer" else None
            _sess, _ = get_session_from_token(db, _token) if _token else (None, None)
            if _sess is not None and getattr(_sess, "user_id", None):
                settled_by = _sess.user_id
        except Exception:
            pass

    # FIX H8-P3: پایه‌ی مالی تسویه — مبلغ منفی (خروجی صندوق)، تایپ جدید که در گزارش‌های درآمد شمرده نمی‌شود.
    from today_summary import jalali_date_string  # lazy، مثل routers/analytics.py
    from dependencies import get_next_sequence_value  # lazy، مثل finance.py
    payout = Transaction(
        course_id=None,
        amount=-total_amount,
        type="settlement_payout",
        target_wallet="teacher",
        date=jalali_date_string(datetime.date.today()),
        description=f"تسویه معلم {teacher.first_name} {teacher.last_name}",
        remittance_number=get_next_sequence_value(db, "remittance_settlement", 100001)
    )
    db.add(payout)

    # 3. ثبت رکورد تسویه نهایی
    new_settlement = Settlement(
        teacher_id=teacher_id,
        total_amount=total_amount,
        session_count=len(session_ids),
        settled_by_user_id=settled_by
    )
    db.add(new_settlement)
    db.commit()
    
    return {
        "message": "تسویه‌حساب با موفقیت انجام و مبالغ پرداخت شد",
        "settlement_id": new_settlement.id,
        "total_amount": total_amount,
        "session_count": len(session_ids)
    }


@router.get("/teachers/{teacher_id}/settlement_history")
def get_settlement_history(
    teacher_id: int, 
    db: Session = Depends(get_db), 
    authorization: Optional[str] = Header(None),
    sub_role: str = Depends(check_user_login)
):
    # FIX (L14/Y2): تاریخچه‌ی تسویه‌ی معلم — فقط ادمین/منشی + خودِ معلم. شاگرد/ولی 403.
    if sub_role not in ("admin", "secretary", "teacher"):
        raise HTTPException(status_code=403, detail="شما دسترسی لازم برای مشاهده‌ی اطلاعات معلمان را ندارید")
    if sub_role == "teacher":
        from routers.reports import get_logged_in_teacher  # lazy (جلوگیری از import چرخه‌ای)
        logged_teacher = get_logged_in_teacher(db, authorization)
        if not logged_teacher or logged_teacher.id != teacher_id:
            raise HTTPException(status_code=403, detail="شما فقط مجاز به دیدن اطلاعات خودتان هستید")
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="معلم یافت نشد")
        
    history = (
        db.query(Settlement)
        .filter(Settlement.teacher_id == teacher_id)
        .order_by(desc(Settlement.id))
        .all()
    )
    
    result = []
    for h in history:
        result.append({
            "id": h.id,
            "total_amount": h.total_amount,
            "session_count": h.session_count,
            "settled_at": h.settled_at.strftime("%Y/%m/%d %H:%M") if h.settled_at else "---"
        })
    return result
