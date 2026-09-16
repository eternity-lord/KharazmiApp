from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Header
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Union
from sqlalchemy import desc, or_, text, func
import io
import json
import uuid
import os
import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from fastapi.responses import StreamingResponse

import models
from models import (
    Attendance, Course, Enrollment, Grade, InstituteShare, SessionLog, SmsLog, Student, Teacher, Transaction, User, UserSession, Installment
)
from schemas import (
    HistoryRequest, LoginRequest, TeacherInfo, FullTeacherProfile, StudentCreate, TeacherCreate, CourseCreate, EnrollmentCreate, GradeCreate, GradeItem, AttendanceLogRequest, AttendanceItem, AttendanceSubmitData, SmsSendRequest, ChangePasswordRequest, StudentProfileInfo, FullStudentProfile, TeacherProfileInfo, FullTeacherProfile, ClassReportInfo, ClassStudentData, ClassSessionHistory, FullClassReport, ShareConfigModel, StudentUpdate, TeacherUpdate, PersonListItem, TransactionUpdate, StudentAttendanceHistoryRequest, AdvancedSearchItem, FinanceSubmitData, PrintReceiptRequest, TransactionTestData
)
from dependencies import get_db, check_admin_access, check_admin_or_secretary_access, check_user_login, get_enrollment_tuition_and_discount, SESSION_EXPIRY_DAYS

# FIX: Bug 16 - share the tuition-minus-payment debt calculation across financial views.
from financial_calculations import calculate_student_debt, calculate_enrollment_debt, MAX_TEACHER_SESSION_PRICE

router = APIRouter()

def parse_time_to_minutes(time_str):
    # E.g. "16:00-17:30" or "16:00" or "16"
    try:
        time_str = time_str.strip().replace(" ", "")
        if "-" in time_str:
            parts = time_str.split("-")
            start_str = parts[0]
            end_str = parts[1]
        else:
            start_str = time_str
            end_str = None
            
        def to_min(t_s):
            if ":" in t_s:
                h, m = t_s.split(":")
                return int(h) * 60 + int(m)
            else:
                return int(t_s) * 60
                
        start_m = to_min(start_str)
        if end_str:
            end_m = to_min(end_str)
        else:
            end_m = start_m + 90 # پیش‌فرض ۹۰ دقیقه برای جلسه کلاسی تک‌ساعته
        return start_m, end_m
    except Exception:
        return None

def days_overlap(day1, day2):
    day1 = day1.strip()
    day2 = day2.strip()
    if day1 == day2:
        return True
        
    even_days = {"شنبه", "دوشنبه", "چهارشنبه", "زوج"}
    odd_days = {"یکشنبه", "سه‌شنبه", "پنج‌شنبه", "فرد"}
    
    if day1 in even_days and day2 in even_days:
        if day1 == "زوج" or day2 == "زوج" or day1 == day2:
            return True
    if day1 in odd_days and day2 in odd_days:
        if day1 == "فرد" or day2 == "فرد" or day1 == day2:
            return True
            
    return False

@router.post("/classes/create")
def create_class(course: CourseCreate, override: bool = False, db: Session = Depends(get_db), authorization: Optional[str] = Header(None), sub_role: str = Depends(check_user_login)):
    # FIX (audit-v2/blind-approve-2a): ساخت کلاس فقط ادمین/منشی/معلم — شاگرد/ولی 403.
    # معلم فقط برای خودش (teacher_id اجباری، ورودی کلاینت نادیده) و با سقف نرخ؛ ادمین/منشی
    # معاف از سقف‌اند چون آگاهانه ثبت می‌کنند (approve بالای سقف جداگانه هشدار می‌دهد).
    if sub_role not in ("admin", "secretary"):
        from routers.reports import get_logged_in_teacher
        me = get_logged_in_teacher(db, authorization)
        if not me:
            raise HTTPException(status_code=403, detail="فقط ادمین، منشی یا معلم می‌تواند کلاس تعریف کند")
        course.teacher_id = me.id
        if (course.teacher_session_price or 0) > MAX_TEACHER_SESSION_PRICE:
            raise HTTPException(status_code=400, detail=f"نرخ هر جلسه برای هر شاگرد نمی‌تواند بیشتر از {MAX_TEACHER_SESSION_PRICE:,} تومان باشد؛ برای نرخ بالاتر با ادمین هماهنگ کنید")
    from dependencies import get_next_sequence_value
    next_code = str(get_next_sequence_value(db, "class", 100001))

    course_data = course.dict()
    course_data["code"] = next_code

    if not override:
        # بررسی تداخل زمانی کلاس‌های غیرمعلق همین معلم
        teacher_courses = db.query(Course).filter(Course.teacher_id == course.teacher_id, Course.is_suspended == False).all()
        for tc in teacher_courses:
            if days_overlap(tc.days_of_week, course.days_of_week):
                time1 = parse_time_to_minutes(tc.class_time)
                time2 = parse_time_to_minutes(course.class_time)
                if time1 and time2:
                    start1, end1 = time1
                    start2, end2 = time2
                    if start1 < end2 and start2 < end1:
                        # تداخل شناسایی شد! فرستادن هشدار به ادمین کلاینت
                        return {
                            "status": "warning",
                            "message": f"⚠️ تداخل زمانی با کلاس '{tc.title}' در روز '{tc.days_of_week}' ساعت '{tc.class_time}' شناسایی شد.",
                            "clash_course": {
                                "title": tc.title,
                                "days": tc.days_of_week,
                                "time": tc.class_time
                            }
                        }

    new_course = Course(**course_data)
    db.add(new_course)
    db.commit()
    return {
        "status": "success",
        "message": "کلاس تعریف شد", 
        "id": new_course.id,
        "code": next_code
    }


@router.get("/classes/list")
def get_all_classes(
    teacher_name: Optional[str] = None,
    student_name: Optional[str] = None,
    course_name: Optional[str] = None,
    grade_level: Optional[str] = None,
    start_year: Optional[str] = None,
    db: Session = Depends(get_db), 
    _: str = Depends(check_admin_or_secretary_access)  # FIX (L14/Y3): کاتالوگ+بدهی کلاس‌ها — فقط کارکنان (تک‌مصرف: ClassManagement)
):
    # پایش فیلترهای چندگانه جستجو (Multi-part advanced search)
    q = db.query(Course).filter(Course.is_deleted == False)
    
    if teacher_name:
        search_t = f"%{teacher_name}%"
        q = q.join(Teacher).filter(
            or_(
                Teacher.first_name.ilike(search_t),
                Teacher.last_name.ilike(search_t)
            )
        )
        
    if student_name:
        search_s = f"%{student_name}%"
        # FIX: Bug 13 - class search must not treat archived enrollments as current membership.
        q = q.join(Enrollment).join(Student).filter(
            Enrollment.is_deleted == False,
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
        # FIX: Bug 13 - year-based searches use active enrollments too.
        q = q.join(Enrollment).filter(Enrollment.is_deleted == False, Enrollment.register_date.like(f"{start_year}%"))

    courses = q.order_by(desc(Course.id)).all()
    result = []

    for c in courses:
        # 1. Get Teacher Name
        teacher = db.query(Teacher).filter(Teacher.id == c.teacher_id).first()
        t_name = f"{teacher.first_name} {teacher.last_name}" if teacher else "نامشخص"

        # 2. Get Top 10 Students for Preview (Updated from 3 to 10)
        enrollments = (
            # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
            db.query(Enrollment).filter(Enrollment.is_deleted == False).filter(Enrollment.course_id == c.id).limit(10).all()
        )
        student_names = []
        for en in enrollments:
            st = db.query(Student).filter(Student.id == en.student_id, Student.is_deleted == False).first()
            if st:
                student_names.append(f"{st.first_name} {st.last_name}")

        # 3. Calculate debt for the class
        total_debt = 0
        debt_to_teacher = 0
        debt_to_institute = 0
        total_paid = 0
        paid_to_teacher = 0
        paid_to_institute = 0

        # Get all students in this class
        all_enrollments = (
            # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
            db.query(Enrollment).filter(Enrollment.is_deleted == False).filter(Enrollment.course_id == c.id).all()
        )

        print(f"\n=== کلاس {c.id} - {c.title} ===")
        print(f"تعداد دانش‌آموزان: {len(all_enrollments)}")

        for en in all_enrollments:
            st = db.query(Student).filter(Student.id == en.student_id, Student.is_deleted == False).first()
            if st:
                # Calculate student's debt
                w_t = st.wallet_teacher if st.wallet_teacher is not None else 0
                w_i = st.wallet_institute if st.wallet_institute is not None else 0

                # If negative, it's debt
                student_debt_teacher = abs(w_t) if w_t < 0 else 0
                student_debt_institute = abs(w_i) if w_i < 0 else 0

                # If positive, it's paid amount (credit)
                student_paid_teacher = w_t if w_t > 0 else 0
                student_paid_institute = w_i if w_i > 0 else 0

                print(
                    f"  دانش‌آموز {st.id}: wallet_teacher={w_t}, wallet_institute={w_i}"
                )
                print(
                    f"    بدهی به معلم: {student_debt_teacher}, بدهی به آموزشگاه: {student_debt_institute}"
                )
                print(
                    f"    پرداخت به معلم: {student_paid_teacher}, پرداخت به آموزشگاه: {student_paid_institute}"
                )

                debt_to_teacher += student_debt_teacher
                debt_to_institute += student_debt_institute
                # FIX: Bug 16 - a class owes its own remaining tuition, not another class's wallet debt.
                total_debt += calculate_enrollment_debt(en) if en.total_tuition else student_debt_teacher + student_debt_institute

                paid_to_teacher += student_paid_teacher
                paid_to_institute += student_paid_institute
                total_paid += student_paid_teacher + student_paid_institute

        print(
            f"مجموع بدهی کلاس: {total_debt} (معلم: {debt_to_teacher}, آموزشگاه: {debt_to_institute})"
        )
        print(
            f"مجموع پرداختی کلاس: {total_paid} (معلم: {paid_to_teacher}, آموزشگاه: {paid_to_institute})"
        )

        # 4. Get actual session count from session_logs
        session_count = (
            # FIX: Bug 14 - exclude archived SessionLog rows from this active view.
            db.query(SessionLog).filter(SessionLog.is_deleted == False).filter(SessionLog.course_id == c.id).count()
        )

        print(f"تعداد جلسات برگزار شده: {session_count}")

        # 5. Add to result
        result.append(
            {
                "id": c.id,
                "title": c.title,
                "code": c.code,
                "grade_level": c.grade_level,
                "gender": c.gender_type,
                "teacher_id": c.teacher_id,
                "teacher_name": t_name,
                "students_preview": student_names,
                "session_count": session_count,
                "total_debt": total_debt,
                "debt_to_teacher": debt_to_teacher,
                "debt_to_institute": debt_to_institute,
                "total_paid": total_paid,
                "paid_to_teacher": paid_to_teacher,
                "paid_to_institute": paid_to_institute,
                "is_suspended": c.is_suspended if c.is_suspended is not None else False,
            }
        )

    return result


@router.get("/classes/{course_id}/details")
def get_class_details(course_id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(None), sub_role: str = Depends(check_user_login)):
    # FIX (E2E-B5): کلاس آرشیوی مثل ناموجود است — 404 به‌جای برگرداندن دیتای آرشیوشده (الگوی add_enrollment).
    course = db.query(Course).filter(Course.id == course_id, Course.is_deleted == False).first()
    if not course:
        raise HTTPException(status_code=404, detail="کلاس یافت نشد")
    # FIX (L14/Y3): گزارش کلاس — ادمین/منشی + معلمِ مالک کلاس (الگوی audit-v2/#11). شاگرد/ولی 403.
    if sub_role not in ("admin", "secretary"):
        if sub_role != "teacher":
            raise HTTPException(status_code=403, detail="شما مجاز به مشاهده اطلاعات این کلاس نیستید")
        from routers.reports import get_logged_in_teacher  # lazy (جلوگیری از import چرخه‌ای)
        _me = get_logged_in_teacher(db, authorization)
        if not _me or course.teacher_id != _me.id:
            raise HTTPException(status_code=403, detail="شما مجاز به مشاهده اطلاعات این کلاس نیستید")
    # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
    enrollments = db.query(Enrollment).filter(Enrollment.is_deleted == False).filter(Enrollment.course_id == course_id).all()
    students_list = []
    for enroll in enrollments:
        st = db.query(Student).filter(Student.id == enroll.student_id, Student.is_deleted == False).first()
        if not st:
            continue
        final_tuition, discount_amt = get_enrollment_tuition_and_discount(enroll)
        debt = final_tuition - enroll.total_paid
        students_list.append(
            {
                "student_name": f"{st.first_name} {st.last_name}",
                "student_id": st.id,
                "student_code": st.student_code,
                "total_tuition": final_tuition,
                "paid": enroll.total_paid,
                "debt": debt,
                "enrollment_id": enroll.id,
                "discount_type": getattr(enroll, "discount_type", "none") or "none",
                "discount_value": getattr(enroll, "discount_value", 0) or 0,
                "discount_amount": discount_amt
            }
        )
    return {"course_info": course, "students": students_list}


@router.post("/classes/{course_id}/suspend")
def suspend_class(course_id: int, db: Session = Depends(get_db), _: str = Depends(check_admin_or_secretary_access)):  # FIX H10-S: تعلیق فقط ادمین/منشی (الگوی C1)
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="کلاس یافت نشد")

    # تغییر وضعیت تعلیق (اگر True بود False میشه و برعکس)
    course.is_suspended = not course.is_suspended
    db.commit()

    status_text = "معلق (غیرفعال)" if course.is_suspended else "فعال"
    return {
        "message": f"وضعیت کلاس به {status_text} تغییر کرد.",
        "is_suspended": course.is_suspended,
    }


@router.post("/admin/classes/{course_id}/suspend_s")
def suspend_class_admin(course_id: int, db: Session = Depends(get_db), _: str = Depends(check_admin_or_secretary_access)):  # FIX H10-S: تعلیق فقط ادمین/منشی (الگوی C1)
    """
    endpoint مخصوص ادمین برای تعلیق/فعال‌سازی کلاس (دکمه S)
    کلاس را معلق می‌کند یا فعال می‌سازد و برای معلم غیرفعال/فعال می‌شود
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="کلاس یافت نشد")

    # تغییر وضعیت تعلیق (toggle)
    course.is_suspended = not course.is_suspended
    db.commit()

    status_text = "معلق (غیرفعال)" if course.is_suspended else "فعال"
    return {
        "message": f"وضعیت کلاس به {status_text} تغییر کرد.",
        "is_suspended": course.is_suspended,
    }


@router.post("/enrollments/add")
def add_enrollment(data: EnrollmentCreate, db: Session = Depends(get_db), _: str = Depends(check_admin_or_secretary_access)):
    # اعتبارسنجی وجود دانش‌آموز و کلاس (جلوگیری از رکورد یتیم)
    student = db.query(Student).filter(Student.id == data.student_id, Student.is_deleted == False).first()
    if not student:
        raise HTTPException(status_code=404, detail="دانش‌آموز یافت نشد")
    # FIX H10: دانش‌آموز معلق، ثبت‌نام جدید نمی‌شود.
    if student.is_suspended:
        raise HTTPException(status_code=403, detail="این دانش‌آموز در حال حاضر معلق است و ثبت‌نام جدید امکان‌پذیر نیست")
    # FIX H10: کلاس آرشیوی مثل ناموجود است (404 پایین) — قبلاً اصلاً چک نمی‌شد.
    course = db.query(Course).filter(Course.id == data.course_id, Course.is_deleted == False).first()
    if not course:
        raise HTTPException(status_code=404, detail="کلاس مورد نظر یافت نشد")
    # FIX H10: ثبت‌نام جدید در کلاس معلق ممنوع.
    if course.is_suspended:
        raise HTTPException(status_code=403, detail="این کلاس در حال حاضر معلق است و ثبت‌نام جدید امکان‌پذیر نیست")

    # چک تکراری نبودن
    exists = (
        # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
        db.query(Enrollment).filter(Enrollment.is_deleted == False)
        .filter(
            Enrollment.student_id == data.student_id,
            Enrollment.course_id == data.course_id,
        )
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=400, detail="این دانش‌آموز قبلاً در این کلاس ثبت شده است"
        )

    # Validation of discount
    d_type = data.discount_type or "none"
    d_val = data.discount_value or 0

    if d_type == "percentage":
        if d_val < 0 or d_val > 100:
            raise HTTPException(status_code=400, detail="درصد تخفیف باید بین ۰ و ۱۰۰ باشد")
    elif d_type == "fixed":
        if d_val < 0 or d_val > data.total_tuition:
            raise HTTPException(status_code=400, detail="مبلغ تخفیف ثابت نمی‌تواند بیشتر از شهریه پایه باشد")
    else:
        d_type = "none"
        d_val = 0

    # FIX S3: Enrollment.branch_id همان منطق Transaction.branch_id (student.branch_id وگرنه course.branch_id) — قبلاً همیشه NULL می‌ماند
    new_enroll = Enrollment(
        student_id=data.student_id,
        course_id=data.course_id,
        branch_id=student.branch_id if student.branch_id is not None else course.branch_id,
        register_date=data.register_date,
        shift=data.shift,
        total_tuition=data.total_tuition,
        total_paid=data.paid_amount,
        discount_type=d_type,
        discount_value=d_val
    )
    db.add(new_enroll)
    db.flush() # جهت تولید آیدی ثبت‌نام کلاسی

    # ذخیره فیزیکی اقساط شهریه در صورت ارسال از کلاینت
    if data.installments:
        for inst in data.installments:
            db.add(Installment(
                enrollment_id=new_enroll.id,
                amount=inst.amount,
                due_date=inst.due_date,
                is_paid=False
            ))

    # 💰 منطق جدید مالی: واریز به کیف پول
    if data.paid_amount > 0:
        from dependencies import get_next_sequence_value  # lazy، مثل submit_payment
        # FIX (F-C1): تک‌کامیت — new_enroll.id بعد از flush موجود است پس enrollment_id همان‌جا
        # ست می‌شود (کامیت دوم و ریسک یتیم‌شدن لینک حذف شد) + branch_id طبق H7 (شاگرد، وگرنه
        # کلاس) + شماره‌ی حواله از همان شمارنده‌ی submit_payment (Bug 11).
        new_trans = Transaction(
            enrollment_id=new_enroll.id,
            student_id=data.student_id,
            course_id=data.course_id,
            branch_id=student.branch_id if student.branch_id is not None else course.branch_id,
            amount=data.paid_amount,
            payment_method=data.payment_method,
            date=data.register_date,
            receiver=data.receiver,
            description="شارژ کیف پول (ثبت نام)",
            type="enrollment_payment",  # اضافه کردن نوع برای شناسایی بهتر
            target_wallet="institute",
            remittance_number=get_next_sequence_value(db, "remittance_institute", 100001),
        )
        db.add(new_trans)

        # شارژ حساب دانش‌آموز
        st = db.query(Student).filter(Student.id == data.student_id).first()
        # FIX: Bug 18 - book initial credit in the institute wallet, as the other registration paths do.
        st.wallet_institute = (st.wallet_institute or 0) + data.paid_amount
        st.sync_wallet_balance()

    db.commit()

    return {
        "message": "ثبت نام انجام شد و حساب شارژ شد",
        "enrollment_id": new_enroll.id,
    }


@router.delete("/enrollments/{enrollment_id}")
def delete_enrollment(enrollment_id: int, db: Session = Depends(get_db), _: str = Depends(check_admin_access)):
    # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
    enrollment = db.query(Enrollment).filter(Enrollment.is_deleted == False).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(
            status_code=404, detail="این دانش‌آموز در این کلاس ثبت نام نشده است"
        )

    from dependencies import perform_delete_enrollment
    perform_delete_enrollment(enrollment, db)
    db.commit()
    return {"message": "دانش‌آموز از کلاس حذف شد و حساب‌ها اصلاح گردید."}


@router.get("/classes/{id}/full_report")
def get_class_full_report(id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(None), sub_role: str = Depends(check_user_login)):
    # 1. اطلاعات پایه کلاس و معلم
    # FIX (E2E-B5): دوقلوی هم‌الگو — کلاس آرشیوی 404.
    course = db.query(Course).filter(Course.id == id, Course.is_deleted == False).first()
    if not course:
        raise HTTPException(status_code=404, detail="کلاس یافت نشد")
    # FIX (L14/Y3): گزارش کلاس — ادمین/منشی + معلمِ مالک کلاس (الگوی audit-v2/#11). شاگرد/ولی 403.
    if sub_role not in ("admin", "secretary"):
        if sub_role != "teacher":
            raise HTTPException(status_code=403, detail="شما مجاز به مشاهده اطلاعات این کلاس نیستید")
        from routers.reports import get_logged_in_teacher  # lazy (جلوگیری از import چرخه‌ای)
        _me = get_logged_in_teacher(db, authorization)
        if not _me or course.teacher_id != _me.id:
            raise HTTPException(status_code=403, detail="شما مجاز به مشاهده اطلاعات این کلاس نیستید")

    teacher = db.query(Teacher).filter(Teacher.id == course.teacher_id).first()
    t_name = f"{teacher.first_name} {teacher.last_name}" if teacher else "نامشخص"

    # 2. اطلاعات دانش‌آموزان و مالی
    # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
    enrollments = db.query(Enrollment).filter(Enrollment.is_deleted == False).filter(Enrollment.course_id == id).all()

    student_list = []
    total_rev = 0
    total_deb = 0

    for en in enrollments:
        st = db.query(Student).filter(Student.id == en.student_id, Student.is_deleted == False).first()
        if not st:
            continue
        # FIX: Bug 16 - do not overwrite discounted tuition minus paid with a wallet-only estimate.
        debt = calculate_enrollment_debt(en) if en.total_tuition else calculate_student_debt(db, st)

        total_rev += en.total_paid
        total_deb += debt

        student_list.append(
            ClassStudentData(
                name=f"{st.first_name} {st.last_name}",
                mobile=st.student_mobile,
                paid=en.total_paid,
                debt=debt,
            )
        )

    # 3. محاسبه جلسات برگزار شده (اصلاح شده با ساختار جدید) ✅
    # اول لیست جلسات این کلاس رو میگیریم
    # FIX: Bug 14 - exclude archived SessionLog rows from this active view.
    sessions = db.query(SessionLog).filter(SessionLog.is_deleted == False).filter(SessionLog.course_id == id).all()

    session_history = []
    for sess in sessions:
        # برای هر جلسه، تعداد حاضرین و غایبین رو از جدول Attendance میشماریم
        p_count = (
            db.query(Attendance)
            .filter(Attendance.session_id == sess.id, Attendance.status == "Present")
            .count()
        )
        a_count = (
            db.query(Attendance)
            .filter(Attendance.session_id == sess.id, Attendance.status == "Absent")
            .count()
        )

        session_history.append(
            ClassSessionHistory(
                date=sess.date, present_count=p_count, absent_count=a_count
            )
        )

    return FullClassReport(
        info=ClassReportInfo(
            title=course.title,
            code=course.code,
            teacher_name=t_name,
            session_count=len(sessions),
            total_students=len(enrollments),
            total_revenue=total_rev,
            total_debt=total_deb,
        ),
        students=student_list,
        sessions=session_history,
    )


# ==========================================
# 16. API تنظیمات سهم آموزشگاه (Share Config)
# ==========================================


# مدل ورودی و خروجی
class ShareConfigModel(BaseModel):
    count_1: int
    count_2: int
    count_3: int
    count_4: int
    count_5: int
    count_6: int
    count_7: int
    count_8: int
    count_9: int
    count_10: int
    count_11: int
    count_12: int
    count_13: int
    count_14: int
    count_15: int


@router.get("/classes/{class_id}/students_full/excel")
def get_class_students_excel(class_id: int, db: Session = Depends(get_db), _: str = Depends(check_admin_or_secretary_access)):
    course = db.query(Course).filter(Course.id == class_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="کلاس یافت نشد")
        
    # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
    enrollments = db.query(Enrollment).filter(Enrollment.is_deleted == False).filter(Enrollment.course_id == class_id).all()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "لیست دانش‌آموزان کلاس"
    ws.views.sheetView[0].rightToLeft = True
    
    ws.append([f"کلاس: {course.title}", "", f"کد کلاس: {course.code}"])
    ws.append([])
    
    headers = ["شناسه", "نام و نام خانوادگی", "شهریه پایه (تومان)", "نوع تخفیف", "تخفیف انتخابی", "مبلغ تخفیف (تومان)", "شهریه نهایی (تومان)", "کل پرداختی (تومان)", "بدهی به معلم", "بدهی به آموزشگاه", "بدهی کل", "جلسات حاضر", "جلسات غایب", "درصد حضور"]
    ws.append(headers)
    
    ws.cell(row=1, column=1).font = Font(name="Tahoma", size=12, bold=True, color="004D40")
    ws.cell(row=1, column=3).font = Font(name="Tahoma", size=12, bold=True, color="004D40")
    
    header_fill = PatternFill(start_color="00695C", end_color="00695C", fill_type="solid")
    header_font = Font(name="Tahoma", size=11, bold=True, color="FFFFFF")
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        
    row_num = 4
    for enroll in enrollments:
        st = db.query(Student).filter(Student.id == enroll.student_id, Student.is_deleted == False).first()
        if st:
            final_tuition, discount_amt = get_enrollment_tuition_and_discount(enroll)
            w_t = st.wallet_teacher if st.wallet_teacher is not None else 0
            w_i = st.wallet_institute if st.wallet_institute is not None else 0

            debt_teacher = abs(w_t) if w_t < 0 else 0
            debt_institute = abs(w_i) if w_i < 0 else 0
            # FIX: Bug 16 - prefer this enrollment's tuition balance; keep unpriced legacy billing.
            total_debt = calculate_enrollment_debt(enroll) if enroll.total_tuition else debt_teacher + debt_institute

            # FIX: Bug 14 - exclude archived SessionLog rows from this active view.
            sessions = db.query(SessionLog).filter(SessionLog.is_deleted == False).filter(SessionLog.course_id == class_id).all()
            present_count = 0
            absent_count = 0
            for session in sessions:
                att = db.query(Attendance).filter(Attendance.session_id == session.id, Attendance.student_id == st.id).first()
                if att:
                    if att.status in ["Present", "Late"]:
                        present_count += 1
                    elif att.status == "Absent":
                        absent_count += 1
                        
            total_s = present_count + absent_count
            att_rate = (present_count / total_s * 100) if total_s > 0 else 100.0
            
            d_type = getattr(enroll, "discount_type", "none") or "none"
            d_type_farsi = "درصدی" if d_type == "percentage" else "مبلغ ثابت" if d_type == "fixed" else "بدون تخفیف"
            d_val_disp = f"{enroll.discount_value}%" if d_type == "percentage" else enroll.discount_value
            
            row_data = [
                st.id,
                f"{st.first_name} {st.last_name}",
                enroll.total_tuition,
                d_type_farsi,
                d_val_disp,
                discount_amt,
                final_tuition,
                enroll.total_paid,
                debt_teacher,
                debt_institute,
                total_debt,
                present_count,
                absent_count,
                f"{att_rate:.1f}%"
            ]
            ws.append(row_data)
            
            ws.cell(row=row_num, column=3).number_format = '#,##0'
            ws.cell(row=row_num, column=6).number_format = '#,##0'
            ws.cell(row=row_num, column=7).number_format = '#,##0'
            ws.cell(row=row_num, column=8).number_format = '#,##0'
            ws.cell(row=row_num, column=9).number_format = '#,##0'
            ws.cell(row=row_num, column=10).number_format = '#,##0'
            ws.cell(row=row_num, column=11).number_format = '#,##0'
            
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
        headers={"Content-Disposition": f"attachment; filename=class_students_{class_id}.xlsx"}
    )


@router.get("/classes/{id}/students_full")
def get_class_students_full(id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(None), sub_role: str = Depends(check_user_login)):
    # FIX (E2E-B5): دوقلوی هم‌الگو — کلاس آرشیوی 404.
    course = db.query(Course).filter(Course.id == id, Course.is_deleted == False).first()
    if not course:
        raise HTTPException(status_code=404, detail="کلاس یافت نشد")
    # FIX (L14/Y3): گزارش کلاس — ادمین/منشی + معلمِ مالک کلاس (الگوی audit-v2/#11). شاگرد/ولی 403.
    if sub_role not in ("admin", "secretary"):
        if sub_role != "teacher":
            raise HTTPException(status_code=403, detail="شما مجاز به مشاهده اطلاعات این کلاس نیستید")
        from routers.reports import get_logged_in_teacher  # lazy (جلوگیری از import چرخه‌ای)
        _me = get_logged_in_teacher(db, authorization)
        if not _me or course.teacher_id != _me.id:
            raise HTTPException(status_code=403, detail="شما مجاز به مشاهده اطلاعات این کلاس نیستید")

    # FIX: Bug 13 - exclude archived Enrollment rows from this active view.
    enrollments = db.query(Enrollment).filter(Enrollment.is_deleted == False).filter(Enrollment.course_id == id).all()
    students_list = []

    for enroll in enrollments:
        st = db.query(Student).filter(Student.id == enroll.student_id, Student.is_deleted == False).first()
        if st:
            final_tuition, discount_amt = get_enrollment_tuition_and_discount(enroll)
            # محاسبه دقیق بدهی‌ها از کیف پول
            w_t = st.wallet_teacher if st.wallet_teacher is not None else 0
            w_i = st.wallet_institute if st.wallet_institute is not None else 0

            debt_teacher = abs(w_t) if w_t < 0 else 0
            debt_institute = abs(w_i) if w_i < 0 else 0
            # FIX: Bug 16 - prefer this enrollment's tuition balance; keep unpriced legacy billing.
            total_debt = calculate_enrollment_debt(enroll) if enroll.total_tuition else debt_teacher + debt_institute

            # محاسبه تعداد جلسات حاضر و غایب
            # دریافت تمام جلسات این کلاس
            # FIX: Bug 14 - exclude archived SessionLog rows from this active view.
            sessions = db.query(SessionLog).filter(SessionLog.is_deleted == False).filter(SessionLog.course_id == id).all()
            present_count = 0
            absent_count = 0

            for session in sessions:
                attendance = (
                    db.query(Attendance)
                    .filter(
                        Attendance.session_id == session.id,
                        Attendance.student_id == st.id,
                    )
                    .first()
                )

                if attendance:
                    if attendance.status == "Present" or attendance.status == "Late":
                        present_count += 1
                    elif attendance.status == "Absent":
                        absent_count += 1

            students_list.append(
                {
                    "student_id": st.id,
                    "student_code": st.student_code,
                    "student_name": f"{st.first_name} {st.last_name}",
                    "national_code": st.national_code,
                    "mobile": st.student_mobile,
                    "total_tuition": final_tuition,
                    "paid": enroll.total_paid,
                    "debt": total_debt,
                    "debt_teacher": debt_teacher,
                    "debt_institute": debt_institute,
                    "wallet_teacher": w_t,
                    "wallet_institute": w_i,
                    "present_count": present_count,
                    "absent_count": absent_count,
                    "total_sessions": len(sessions),
                    "attendance_rate": round((present_count / len(sessions) * 100), 2)
                    if len(sessions) > 0
                    else 0,
                    "is_suspended": st.is_suspended
                    if st.is_suspended is not None
                    else False,
                    "enrollment_id": enroll.id,
                    "discount_type": getattr(enroll, "discount_type", "none") or "none",
                    "discount_value": getattr(enroll, "discount_value", 0) or 0,
                    "discount_amount": discount_amt
                }
            )

    return {
        "course_info": {
            "id": course.id,
            "title": course.title,
            "code": course.code,
            "teacher_id": course.teacher_id,
            "is_suspended": course.is_suspended
            if course.is_suspended is not None
            else False,
        },
        "students": students_list,
    }


# ==========================================
# 🔥 بخش جدید: مدیریت مالی هوشمند (نسخه 2)
# ==========================================


# 1. مدل‌های ورودی و خروجی جدید
class AdvancedSearchItem(BaseModel):
    type: str
    id: int
    title: str
    subtitle: str
    info: str
    student_id: Optional[int] = None
    course_id: Optional[int] = None
    debt_teacher: Optional[int] = 0
    debt_institute: Optional[int] = 0
    total_debt: Optional[int] = 0
    unpaid_sessions: Optional[int] = 0
    students_in_class: Optional[List[dict]] = None


class FinanceSubmitData(BaseModel):
    student_id: int
    amount: int
    target_wallet: str  # "teacher" یا "institute" یا "both"
    description: str
    payment_method: str
    date: str
    amount_institute: Optional[int] = None
    amount_teacher: Optional[int] = None


@router.delete("/classes/{course_id}")
def delete_class_endpoint(
    course_id: int,
    forgive_session_charges: bool = True,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    _: str = Depends(check_admin_access)
):
    # حذف مستقیم و فوری فقط برای ادمین (معلم/منشی از مسیر درخواست + تایید استفاده می‌کنند)
    course = db.query(Course).filter(Course.id == course_id, Course.is_deleted == False).first()
    if not course:
        raise HTTPException(status_code=404, detail="کلاس یافت نشد")

    snapshot = _build_class_deletion_snapshot(db, course)
    _apply_class_deletion(db, course, forgive_session_charges)
    # ثبت ردیف تاییدشده برای یکدستی تاریخچه حسابرسی
    # FIX H9: شناسه‌ی تصمیم‌گیرنده باید کاربر واقعی همین درخواست باشد (الگوی H8-P2).
    # چون check_admin_access بالا توکن خراب را از قبل رد کرده، None عملاً نباید بماند (فقط safety net).
    from dependencies import get_session_from_token  # lazy، مثل H8
    _actor_user_id = None
    if authorization:
        try:
            _parts = authorization.split()
            _token = _parts[1] if len(_parts) == 2 and _parts[0].lower() == "bearer" else None
            _sess, _ = get_session_from_token(db, _token) if _token else (None, None)
            if _sess is not None and getattr(_sess, "user_id", None):
                _actor_user_id = _sess.user_id
        except Exception:
            pass
    db.add(models.ClassDeletionRequest(
        course_id=course.id,
        requested_by_role="admin",
        requested_by_user_id=_actor_user_id,
        forgive_session_charges=forgive_session_charges,
        status="approved",
        snapshot_json=json.dumps(snapshot, ensure_ascii=False, default=str),
        decided_at=datetime.datetime.now(),
        decided_by_user_id=_actor_user_id
    ))
    db.commit()
    return {"message": "کلاس با موفقیت حذف و آرشیو شد."}


# ==========================================
# فلوی درخواست حذف کلاس + تایید ادمین
# ==========================================
class DeletionRequestCreate(BaseModel):
    forgive_session_charges: bool = False


class DeletionDecisionRequest(BaseModel):
    admin_note: Optional[str] = None


def _build_class_deletion_snapshot(db: Session, course) -> dict:
    """اسنپ‌شات لحظه درخواست: جلسات رفته و بدهی هر شاگرد + اثر حذف بر معلم."""
    sessions = db.query(SessionLog).filter(SessionLog.is_deleted == False, SessionLog.course_id == course.id).all()
    session_ids = [s.id for s in sessions]
    enrollments = db.query(Enrollment).filter(Enrollment.is_deleted == False, Enrollment.course_id == course.id).all()
    students_rows = []
    total_debt = 0
    total_paid = 0
    for en in enrollments:
        st = db.query(Student).filter(Student.id == en.student_id).first()
        attended = 0
        if session_ids:
            attended = db.query(func.count(Attendance.id)).filter(
                Attendance.session_id.in_(session_ids),
                Attendance.student_id == en.student_id,
                Attendance.status.in_(["Present", "Late"])
            ).scalar() or 0
        final_tuition, _ = get_enrollment_tuition_and_discount(en)
        paid = en.total_paid or 0
        debt = calculate_enrollment_debt(en)
        total_debt += debt
        total_paid += paid
        students_rows.append({
            "student_id": en.student_id,
            "name": f"{st.first_name} {st.last_name}" if st else "نامشخص",
            "sessions_attended": attended,
            "tuition_final": final_tuition,
            "total_paid": paid,
            "debt": debt,
            "wallet_teacher": st.wallet_teacher if st and st.wallet_teacher is not None else 0,
            "wallet_institute": st.wallet_institute if st and st.wallet_institute is not None else 0,
        })
    # طلب معلم از همین کلاس (اثر حذف بر معلم) — همان منطق pending_settlement محدود به این کلاس
    teacher_pending = 0
    if session_ids:
        unbilled = {r[0] for r in db.query(Attendance.session_id).filter(
            Attendance.session_id.in_(session_ids),
            Attendance.is_billed == False,
            Attendance.status.in_(["Present", "Late"])
        ).distinct().all()}
        # FIX: H6(A2) - طلب معلم = مبالغ قراردادی + جریمه‌ی غایبین غیرموجه.
        # FIX H8-gap/follow-up: شاخه‌ی جریمه هم طلب است (همان منطق دوشاخه‌ی settle).
        teacher_pending = sum((s.final_teacher_cost or 0) + (s.absent_penalty_teacher or 0) for s in sessions if s.id in unbilled or ((s.absent_penalty_teacher or 0) > 0 and not s.is_penalty_settled))
    return {
        "course_id": course.id,
        "course_title": course.title,
        "course_code": course.code,
        "sessions_total": len(session_ids),
        "students": students_rows,
        "totals": {
            "students": len(students_rows),
            "total_debt": total_debt,
            "total_paid": total_paid,
            "teacher_pending_this_class": teacher_pending,
        },
    }


def _apply_class_deletion(db: Session, course, forgive_session_charges: bool):
    """اعمال حذف: آرشیو کلاس و ثبت‌نام‌ها + (در صورت تیک) ابطال مالی جلسات."""
    from dependencies import perform_delete_enrollment
    course.is_deleted = True
    enrollments = db.query(Enrollment).filter(Enrollment.is_deleted == False, Enrollment.course_id == course.id).all()
    for en in enrollments:
        perform_delete_enrollment(en, db, forgive_session_charges=forgive_session_charges)
    if forgive_session_charges:
        # جلسات از چرخه مالی خارج می‌شوند ولی سابقه‌شان برای تاریخچه می‌ماند
        db.query(SessionLog).filter(SessionLog.is_deleted == False, SessionLog.course_id == course.id).update(
            {SessionLog.is_deleted: True}, synchronize_session="fetch"
        )


@router.post("/classes/{course_id}/request_delete")
def request_class_deletion(
    course_id: int,
    data: DeletionRequestCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    sub_role: str = Depends(check_user_login)
):
    # معلم (فقط کلاس خودش) و منشی (همه کلاس‌ها) درخواست می‌دهند؛ ادمین مستقیم حذف می‌کند
    if sub_role not in ["secretary", "teacher"]:
        raise HTTPException(status_code=403, detail="ادمین از مسیر حذف مستقیم استفاده می‌کند")
    course = db.query(Course).filter(Course.id == course_id, Course.is_deleted == False).first()
    if not course:
        raise HTTPException(status_code=404, detail="کلاس یافت نشد")
    from dependencies import get_current_user
    current_user = get_current_user(authorization, db)
    teacher_id = None
    if sub_role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.mobile == current_user.username).first()
        if not teacher or course.teacher_id != teacher.id:
            raise HTTPException(status_code=403, detail="شما مجاز به حذف کلاس‌های معلمان دیگر نیستید")
        teacher_id = teacher.id
    pending = db.query(models.ClassDeletionRequest).filter(
        models.ClassDeletionRequest.course_id == course.id,
        models.ClassDeletionRequest.status == "pending"
    ).first()
    if pending:
        raise HTTPException(status_code=400, detail="برای این کلاس یک درخواست حذف باز وجود دارد")
    snapshot = _build_class_deletion_snapshot(db, course)
    req = models.ClassDeletionRequest(
        course_id=course.id,
        requested_by_role=sub_role,
        requested_by_user_id=current_user.id,
        requested_by_teacher_id=teacher_id,
        forgive_session_charges=data.forgive_session_charges,
        status="pending",
        snapshot_json=json.dumps(snapshot, ensure_ascii=False, default=str)
    )
    db.add(req)
    db.commit()
    return {"request_id": req.id, "status": "pending", "message": "درخواست حذف ثبت شد و پس از تایید ادمین اعمال می‌گردد."}


@router.get("/classes/deletion_requests")
def list_class_deletion_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(check_admin_access)
):
    q = db.query(models.ClassDeletionRequest).order_by(desc(models.ClassDeletionRequest.id))
    if status:
        q = q.filter(models.ClassDeletionRequest.status == status)
    result = []
    for r in q.all():
        course = db.query(Course).filter(Course.id == r.course_id).first()
        requester_name = "نامشخص"
        if r.requested_by_teacher_id:
            t = db.query(Teacher).filter(Teacher.id == r.requested_by_teacher_id).first()
            if t:
                requester_name = f"{t.first_name} {t.last_name}"
        elif r.requested_by_user_id:
            u = db.query(User).filter(User.id == r.requested_by_user_id).first()
            if u:
                requester_name = u.username
        try:
            snapshot = json.loads(r.snapshot_json) if r.snapshot_json else {}
        except Exception:
            snapshot = {}
        result.append({
            "request_id": r.id,
            "course_id": r.course_id,
            "course_title": course.title if course else "کلاس حذف شده",
            "course_code": course.code if course else "",
            "requested_by_role": r.requested_by_role,
            "requester_name": requester_name,
            "forgive_session_charges": r.forgive_session_charges,
            "status": r.status,
            "admin_note": r.admin_note,
            "created_at": r.created_at.strftime("%Y/%m/%d %H:%M") if r.created_at else "---",
            "snapshot": snapshot,
        })
    return result


@router.post("/classes/deletion_requests/{request_id}/approve")
def approve_class_deletion(request_id: int, db: Session = Depends(get_db), _: str = Depends(check_admin_access), authorization: Optional[str] = Header(None)):
    # FIX H9: شناسه‌ی تصمیم‌گیرنده باید کاربر واقعی همین درخواست باشد (الگوی H8-P2).
    # چون check_admin_access بالا توکن خراب را از قبل رد کرده، None عملاً نباید بماند (فقط safety net).
    from dependencies import get_session_from_token  # lazy، مثل H8
    _actor_user_id = None
    if authorization:
        try:
            _parts = authorization.split()
            _token = _parts[1] if len(_parts) == 2 and _parts[0].lower() == "bearer" else None
            _sess, _ = get_session_from_token(db, _token) if _token else (None, None)
            if _sess is not None and getattr(_sess, "user_id", None):
                _actor_user_id = _sess.user_id
        except Exception:
            pass
    req = db.query(models.ClassDeletionRequest).filter(models.ClassDeletionRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="این درخواست قبلاً تعیین تکلیف شده است")
    course = db.query(Course).filter(Course.id == req.course_id, Course.is_deleted == False).first()
    if not course:
        req.status = "rejected"
        req.admin_note = "کلاس قبلاً حذف شده بود"
        req.decided_at = datetime.datetime.now()
        req.decided_by_user_id = _actor_user_id
        db.commit()
        raise HTTPException(status_code=400, detail="کلاس قبلاً حذف شده است؛ درخواست بسته شد")
    _apply_class_deletion(db, course, req.forgive_session_charges)
    req.status = "approved"
    req.decided_at = datetime.datetime.now()
    req.decided_by_user_id = _actor_user_id
    db.commit()
    return {"message": "حذف کلاس تایید و اعمال شد."}


@router.post("/classes/deletion_requests/{request_id}/reject")
def reject_class_deletion(request_id: int, data: DeletionDecisionRequest, db: Session = Depends(get_db), _: str = Depends(check_admin_access), authorization: Optional[str] = Header(None)):
    # FIX H9: شناسه‌ی تصمیم‌گیرنده باید کاربر واقعی همین درخواست باشد (الگوی H8-P2).
    # چون check_admin_access بالا توکن خراب را از قبل رد کرده، None عملاً نباید بماند (فقط safety net).
    from dependencies import get_session_from_token  # lazy، مثل H8
    _actor_user_id = None
    if authorization:
        try:
            _parts = authorization.split()
            _token = _parts[1] if len(_parts) == 2 and _parts[0].lower() == "bearer" else None
            _sess, _ = get_session_from_token(db, _token) if _token else (None, None)
            if _sess is not None and getattr(_sess, "user_id", None):
                _actor_user_id = _sess.user_id
        except Exception:
            pass
    req = db.query(models.ClassDeletionRequest).filter(models.ClassDeletionRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="این درخواست قبلاً تعیین تکلیف شده است")
    req.status = "rejected"
    req.admin_note = data.admin_note
    req.decided_at = datetime.datetime.now()
    req.decided_by_user_id = _actor_user_id
    db.commit()
    return {"message": "درخواست حذف رد شد؛ کلاس دست نخورده باقی ماند."}


class ClassUpdateInfoModel(BaseModel):
    title: Optional[str] = None
    grade_level: Optional[str] = None

# FIX (grade-289/srv): لیست معتبر مقاطع = همان لیست L13 در financial_calculations.py
# (ابتدایی/راهنمایی/دبیرستان + معادل‌ها) به‌علاوه‌ی مقادیر مشروعِ غیرتعرفه‌ای که مسیر ساخت
# (اسپینر AddClass) می‌پذیرد: «کنکور»، «فارغ‌التحصیل»، «سایر». L13 خودش این‌ها را
# category=None می‌کند و فقط هنگام نیاز واقعی به تعرفه خطای واضح می‌دهد؛ پس این‌جا هم
# معتبرند و فقط آشغال واقعی (مثل «نامشخص» یا تایپی) 400 می‌گیرد.
_VALID_GRADE_LEVELS = frozenset({
    "اول", "دوم", "سوم", "چهارم", "پنجم", "ششم", "ابتدایی", "دبستان",
    "هفتم", "هشتم", "نهم", "راهنمایی", "متوسطه اول",
    "دهم", "یازدهم", "دوازدهم", "دبیرستان", "متوسطه دوم",
    "کنکور", "فارغ‌التحصیل", "سایر",
})

@router.put("/classes/update_info/{course_id}")
def update_class_info(
    course_id: int, 
    data: ClassUpdateInfoModel, 
    db: Session = Depends(get_db), 
    authorization: Optional[str] = Header(None),
    sub_role: str = Depends(check_user_login)
):
    course = db.query(Course).filter(Course.id == course_id, Course.is_deleted == False).first()
    if not course:
        raise HTTPException(status_code=404, detail="کلاس یافت نشد")

    # FIX (audit-v2/H-caller): فقط ادمین/منشی یا معلمِ مالکِ همین کلاس — قبلاً هر لاگینی
    # (حتی شاگرد) عنوان و grade_level هر کلاسی را عوض می‌کرد. معلمِ مالک عمداً مجاز است چون
    # ClassDetail اپ (مسیر مشروع معلم) همین اندپوینت را صدا می‌زند (قدم ۴)؛ باقی‌مانده‌ی آگاهانه:
    # grade_level روی تعرفه اثر دارد پس تغییرش توسط معلم بعداً باید audit شود (follow-up).
    if sub_role not in ("admin", "secretary"):
        from routers.reports import get_logged_in_teacher
        logged = get_logged_in_teacher(db, authorization)
        if not logged or logged.id != course.teacher_id:
            raise HTTPException(status_code=403, detail="شما مجاز به ویرایش اطلاعات این کلاس نیستید")
        
    if data.title is not None and data.title.strip():
        course.title = data.title.strip()
    if data.grade_level is not None and data.grade_level.strip():
        # FIX (grade-289/srv): اعتبارسنجی به‌جای پذیرش کورکورانه — نرمال‌سازی دقیقاً مثل L13.
        _g = data.grade_level.strip().replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
        _g = " ".join(_g.split())
        if _g not in _VALID_GRADE_LEVELS:
            raise HTTPException(status_code=400, detail=f"مقطع تحصیلی «{data.grade_level.strip()}» نامعتبر است")
        course.grade_level = data.grade_level.strip()
        
    db.commit()
    return {"message": "اطلاعات کلاس با موفقیت ویرایش شد."}


# ==========================================
# اصلاح شده: جستجوی پیشرفته با محاسبه دقیق بدهی
# ==========================================
