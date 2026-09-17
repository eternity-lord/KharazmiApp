import os
import datetime
import random
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, Field
# FIX: Bug 22 - public registration uses the same identity validation as staff registration.
from validation import NationalCodeRequest
from sqlalchemy.orm import Session
from sqlalchemy import or_  # FIX (F-C7): ایمپورت گمشده — کل مسیر ثبت‌نام آنلاین 500 می‌داد (NameError موقع اجرا؛ import-main نمی‌گیرد).
from sqlalchemy import desc

import models
from models import Lead, Student, Enrollment, Course, Transaction, SmsLog
from dependencies import get_db, check_user_login, require_permission, NotificationService, get_next_sequence_value, ensure_student_shadow_users, normalize_mobile

router = APIRouter()

# Pydantic Schemas
class LeadCreateRequest(BaseModel):
    name: str
    mobile: str
    interested_course: str
    source: str = "Web"
    notes: Optional[str] = None
    next_follow_up: Optional[str] = None
    branch_id: Optional[int] = None

class LeadResponseModel(BaseModel):
    id: int
    name: str
    mobile: str
    interested_course: str
    source: str
    status: str
    notes: Optional[str] = None
    next_follow_up: Optional[str] = None
    created_at: str

class LeadNoteRequest(BaseModel):
    notes: str
    next_follow_up: Optional[str] = None
    status: Optional[str] = None

# FIX: Bug 22 - validate the public registration payload before creating any records.
class OnlineRegisterRequest(NationalCodeRequest):
    first_name: str
    last_name: str
    father_name: str
    national_code: str
    student_mobile: str
    parent_mobile: str
    course_id: int
    paid_amount: int = Field(ge=0)  # FIX: Bug 22 - unpaid registration is valid; negative credits are not.
    payment_method: str = "کارتخوان"

# --- 1. Admin/Secretary: Create CRM Lead ---
@router.post("/crm/leads/create", response_model=LeadResponseModel)
def create_crm_lead(
    req: LeadCreateRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    role: str = Depends(require_permission("student.create")),
    _login_role: str = Depends(check_user_login)
):
    from routers.analytics import get_user_branch_filter

    resolved_branch = get_user_branch_filter(db, authorization, req.branch_id)
    # Preserve compatibility for legacy central-admin clients while ensuring
    # every newly-created lead is attributable to a branch.
    resolved_branch = resolved_branch or req.branch_id or 1
    # FIX H20: نرمال‌سازی موبایل سرنخ (خالی مجاز) — convert بعدی مقدار تمیز می‌برد.
    _raw_mob = (req.mobile or "").strip()
    lead_mobile = normalize_mobile(_raw_mob) if _raw_mob else ""
    if _raw_mob and not lead_mobile:
        raise HTTPException(status_code=400, detail="فرمت شماره موبایل صحیح نیست")
    new_lead = Lead(
        name=req.name,
        mobile=lead_mobile,
        interested_course=req.interested_course,
        source=req.source,
        status="NEW",
        notes=req.notes,
        next_follow_up=req.next_follow_up,
        branch_id=resolved_branch,
    )
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    return LeadResponseModel(
        id=new_lead.id,
        name=new_lead.name,
        mobile=new_lead.mobile,
        interested_course=new_lead.interested_course,
        source=new_lead.source,
        status=new_lead.status,
        notes=new_lead.notes,
        next_follow_up=new_lead.next_follow_up,
        created_at=new_lead.created_at.strftime("%Y/%m/%d")
    )

# --- 2. Admin/Secretary: View Leads Pipeline List ---
@router.get("/crm/leads/list", response_model=List[LeadResponseModel])
def get_crm_leads_list(
    db: Session = Depends(get_db),
    role: str = Depends(require_permission("student.read")),
    _login_role: str = Depends(check_user_login)
):
    leads = db.query(Lead).order_by(desc(Lead.id)).all()
    return [
        LeadResponseModel(
            id=l.id,
            name=l.name,
            mobile=l.mobile,
            interested_course=l.interested_course,
            source=l.source,
            status=l.status,
            notes=l.notes,
            next_follow_up=l.next_follow_up,
            created_at=l.created_at.strftime("%Y/%m/%d")
        )
        for l in leads
    ]

# --- 3. Admin/Secretary: Add Notes & Update Lead status ---
@router.post("/crm/leads/{id}/notes")
def add_lead_notes(
    id: int,
    req: LeadNoteRequest,
    db: Session = Depends(get_db),
    role: str = Depends(require_permission("student.update")),
    _login_role: str = Depends(check_user_login)
):
    lead = db.query(Lead).filter(Lead.id == id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="سرنخ یافت نشد")
        
    lead.notes = req.notes
    if req.next_follow_up:
        lead.next_follow_up = req.next_follow_up
    if req.status:
        lead.status = req.status
        
    db.commit()
    return {"message": "یادداشت پیگیری با موفقیت ثبت شد"}

# --- 4. Admin/Secretary: Convert Lead to Student ---
@router.post("/crm/leads/{id}/convert")
def convert_lead_to_student(
    id: int,
    course_id: Optional[int] = None,
    db: Session = Depends(get_db),
    role: str = Depends(require_permission("student.create")),
    _login_role: str = Depends(check_user_login)
):
    lead = db.query(Lead).filter(Lead.id == id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="سرنخ یافت نشد")
        
    # FIX H20: نرمال‌سازی موبایل ذخیره‌شده‌ی سرنخ (legacy ممکن است خام باشد)؛ نامعتبرِ غیرخالی یعنی سرنخ نیاز به اصلاح دارد.
    _raw_mob = (lead.mobile or "").strip()
    lead_mobile = normalize_mobile(_raw_mob) if _raw_mob else ""
    if _raw_mob and not lead_mobile:
        raise HTTPException(status_code=400, detail="فرمت شماره موبایل این سرنخ معتبر نیست؛ ابتدا آن را اصلاح کنید")
    # Check duplicate student
    existing_st = db.query(Student).filter(Student.student_mobile == lead_mobile).first()
    if existing_st:
        raise HTTPException(status_code=400, detail="دانش‌آموزی با این شماره موبایل قبلاً در سیستم ثبت‌نام شده است")
        
    # Convert to Student
    next_code = get_next_sequence_value(db, "student", 100001)
    new_student = Student(
        first_name=lead.name,
        last_name="",
        father_name="",
        national_code=f"0000{random.randint(100000, 999999)}", # temporary code
        birth_date="",
        student_mobile=lead_mobile,
        parent_mobile="",
        home_phone="",
        address="ثبت شده از سرنخ",
        study_status="در حال تحصیل",
        gender="نامشخص",
        student_code=next_code,
        branch_id=lead.branch_id,
    )
    db.add(new_student)
    db.flush()
    lead.status = "REGISTERED"
    lead.converted_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    lead.converted_student_id = new_student.id

    # Enroll in course if course_id is supplied
    # FIX (F-C3): تک‌کامیت — ثبت‌نام قبل از کامیت ساخته می‌شود تا کرش وسط، سرنخِ REGISTEREDِ
    # بدون ثبت‌نام نسازد (پنجره‌ی کرش، نه ریس همزمانی؛ UPDATE مشروط به INSERT جدا نمی‌خورد).
    if course_id:
        course = db.query(Course).filter(Course.id == course_id).first()
        if course:
            enroll = Enrollment(
                student_id=new_student.id,
                course_id=course_id,
                branch_id=course.branch_id or lead.branch_id,
                register_date=datetime.datetime.now().strftime("%Y/%m/%d"),
                shift="عصر",
                total_tuition=1000000,
                total_paid=0
            )
            db.add(enroll)
    db.commit()
            
    return {"message": f"سرنخ با موفقیت به دانش‌آموز '{lead.name}' با کد {next_code} تبدیل شد.", "student_id": new_student.id}

# --- 5. Public: Online Registration (Transaction-safe, duplicate prevention) ---
@router.post("/crm/register_online")
def public_online_registration(req: OnlineRegisterRequest, db: Session = Depends(get_db)):
    # Start Transaction-safe block
    try:
        # FIX H20: نرمال‌سازی قبل از چک تکراری و ذخیره (خالی مجاز و دست‌نخورده می‌ماند).
        _raw_sm = (req.student_mobile or "").strip()
        _sm = normalize_mobile(_raw_sm) if _raw_sm else ""
        if _raw_sm and not _sm:
            raise HTTPException(status_code=400, detail="فرمت شماره موبایل دانش‌آموز صحیح نیست")
        _raw_pm = (req.parent_mobile or "").strip()
        _pm = normalize_mobile(_raw_pm) if _raw_pm else ""
        if _raw_pm and not _pm:
            raise HTTPException(status_code=400, detail="فرمت شماره موبایل ولی صحیح نیست")
        # Check if student already exists by mobile or national code
        student = db.query(Student).filter(
            or_(
                Student.student_mobile == _sm,
                Student.national_code == req.national_code
            )
        ).first()
        
        is_new_student = False
        if not student:
            is_new_student = True
            # Create new Student
            next_code = get_next_sequence_value(db, "student", 100001)
            student = Student(
                first_name=req.first_name,
                last_name=req.last_name,
                father_name=req.father_name,
                national_code=req.national_code,
                birth_date="",
                student_mobile=_sm,
                parent_mobile=_pm,
                home_phone="",
                address="ثبت‌نام آنلاین وب‌سایت",
                study_status="در حال تحصیل",
                gender="نامشخص",
                student_code=next_code
            )
            db.add(student)
            db.flush() # Generate student.id
            
        course = db.query(Course).filter(Course.id == req.course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="کلاس انتخابی یافت نشد")
            
        # Check if already enrolled in this course
        already_enrolled = db.query(Enrollment).filter(Enrollment.student_id == student.id, Enrollment.course_id == req.course_id).first()
        if already_enrolled:
            raise HTTPException(status_code=400, detail="شما قبلاً در این کلاس ثبت‌نام کرده‌اید")
            
        # Create Enrollment
        today = datetime.datetime.now().strftime("%Y/%m/%d")
        enroll = Enrollment(
            student_id=student.id,
            course_id=req.course_id,
            # FIX (F-C2/S3 تکمیلی): شعبه‌ی ثبت‌نام — همان منطق تراکنش (شاگرد، وگرنه کلاس).
            # بدون آن، analytics که با Enrollment.branch_id فیلتر می‌کند (analytics.py:177/185/193)
            # این ثبت‌نام را برای کاربر شعبه‌دار از دست می‌داد (NULL هرگز =شعبه نمی‌شود).
            branch_id=student.branch_id if student.branch_id is not None else course.branch_id,
            register_date=today,
            shift="عصر",
            total_tuition=1000000, # default price or tuition
            total_paid=req.paid_amount
        )
        db.add(enroll)
        db.flush() # Generate enrollment.id
        
        # Finance integration: Create Transaction (deposit/payment)
        if req.paid_amount > 0:
            student.wallet_institute = (student.wallet_institute or 0) + req.paid_amount
            # FIX: Bug 18 - derive the total only through the shared wallet helper.
            student.sync_wallet_balance()
            
            db.add(Transaction(
                student_id=student.id,
                course_id=req.course_id,
                enrollment_id=enroll.id,
                # FIX (F-C2): branch_id طبق H7 — شعبه‌ی شاگرد، وگرنه شعبه‌ی کلاس.
                branch_id=student.branch_id if student.branch_id is not None else course.branch_id,
                amount=req.paid_amount,
                payment_method=req.payment_method,
                date=today,
                type="tuition",
                target_wallet="institute",
                description="ثبت‌نام آنلاین و پرداخت پیش‌پرداخت شهریه"
            ))
            
        db.commit()
        
        # Automation dispatches: SMS, In-App and Push notification
        try:
            # 1. SMS Log
            msg = f"ثبت‌نام آنلاین دانش‌آموز {req.first_name} {req.last_name} در کلاس {course.title} با موفقیت انجام شد."
            db.add(SmsLog(
                target_group=f"online_reg_{student.id}",
                message_text=msg,
                sent_count=1,
                date=datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
            ))
            db.commit()
            
            # 2. Push/In-App Notification
            if student.user_id is None:
                ensure_student_shadow_users(db, student)
            NotificationService.send_notification(
                db=db,
                recipient_user_id=student.user_id,
                recipient_role="student",
                type="payment",
                title="✅ ثبت‌نام آنلاین موفقیت‌آمیز",
                body=f"ثبت‌نام شما در کلاس '{course.title}' با موفقیت انجام شد و مبلغ {req.paid_amount:,} تومان ثبت گردید."
            )
        except Exception as notif_err:
            print(f"⚠️ Error dispatching online registration notification: {notif_err}")
            
        return {
            "status": "success",
            "message": "ثبت‌نام آنلاین شما با موفقیت انجام شد",
            "student_id": student.id,
            "enrollment_id": enroll.id,
            "is_new_student": is_new_student
        }
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"خطا در فرآیند ثبت‌نام تراکنشی: {str(e)}")
