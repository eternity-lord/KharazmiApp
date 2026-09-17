from pydantic import BaseModel, Field
from typing import List, Optional, Union
from pydantic import Field
from pydantic.fields import FieldInfo
from pydantic import BaseModel
import datetime
# FIX: Bug 22 - validate identity writes and cross-field score bounds centrally.
from pydantic import field_validator, model_validator
from validation import (
    NationalCodeRequest,
    validate_attendance_status,
    validate_installment_amount,
    validate_jalali_due_date,
)

class HistoryRequest(BaseModel):
    course_id: int

class LoginRequest(BaseModel):
    mobile: str
    password: Optional[str] = None

class TeacherInfo(BaseModel):
    name: str
    mobile: str
    national_code: str
    status: str

# FIX: Bug 22 - apply the national-code checksum to this write path.
class StudentCreate(NationalCodeRequest):
    first_name: str
    last_name: str
    father_name: str
    national_code: str
    birth_date: str
    student_mobile: str
    parent_mobile: str
    home_phone: str
    address: str
    study_status: str
    gender: str

# FIX: Bug 22 - apply the national-code checksum to this write path.
class TeacherCreate(NationalCodeRequest):
    first_name: str
    last_name: str
    father_name: str
    national_code: str
    birth_date: str
    mobile: str
    password: str
    home_phone: str
    marital_status: str
    gender: str
    employment_type: str
    card_number: str
    profile_image: Optional[str] = None

class CourseCreate(BaseModel):
    title: str
    code: str
    teacher_id: int
    education_type: str
    grade_level: str
    gender_type: str
    class_type: str = "خصوصی"
    days_of_week: str = "نامشخص"
    class_time: str = "نامشخص"
    teacher_session_price: int = Field(ge=0)  # FIX: Bug 22 - a session price cannot be negative.
    rule_prepay_institute: bool = False
    rule_prepay_teacher: bool = False
    rule_calc_absent: bool = True
    bg_color: str = "#FFFFFF"

class InstallmentCreate(BaseModel):
    # FIX (F-T1/F-T2): همان اعتبارسنجی مرکزی مسیر مستقل قسط — مبلغ صحیح مثبت + تاریخ شمسی موجود.
    amount: int = Field(gt=0)
    due_date: str

    @field_validator("amount", mode="before")
    @classmethod
    def _validate_amount(cls, value):
        return validate_installment_amount(value)

    @field_validator("due_date")
    @classmethod
    def _validate_due_date(cls, value):
        return validate_jalali_due_date(value)

class EnrollmentCreate(BaseModel):
    student_id: int
    course_id: int
    register_date: str
    shift: str
    total_tuition: int = Field(gt=0)  # شهریه ثبت‌نام باید مثبت باشد
    paid_amount: int = Field(ge=0)  # FIX: Bug 22 - zero means no initial payment; negatives are invalid.
    payment_method: str
    receiver: str
    discount_type: Optional[str] = "none"
    discount_value: Optional[int] = 0
    installments: Optional[List[InstallmentCreate]] = None


# مدل‌های مربوط به نمره

class GradeCreate(BaseModel):
    student_id: int
    course_id: int
    exam_title: str
    # FIX: Bug 22 - reject negative/non-finite scores and invalid denominators.
    score: float = Field(ge=0, allow_inf_nan=False)
    max_score: float = Field(gt=0, allow_inf_nan=False)
    date: str
    description: str = ""

    # FIX: Bug 22 - a grade must be bounded by the submitted maximum, before any database write.
    @model_validator(mode="after")
    def score_within_maximum(self):
        if self.score > self.max_score:
            raise ValueError("نمره نمی‌تواند بیشتر از نمرهٔ کل باشد")
        return self

class GradeItem(BaseModel):
    course_name: str
    exam_title: str
    score: float
    max_score: float
    date: str

class AttendanceLogRequest(BaseModel):
    course_id: int
    date: str

class AttendanceItem(BaseModel):
    student_id: int
    status: str
    excused: Optional[bool] = False

    # FIX (F-S4): فقط Present / Late / Absent (قرارداد رسمی کلاینت اندروید + همه‌ی فیلترهای سرور).
    @field_validator("status")
    @classmethod
    def _validate_status(cls, value):
        return validate_attendance_status(value)

class AttendanceSubmitData(BaseModel):
    course_id: int
    date: str
    # FIX (F-S3): جلسه‌ی بی‌محتوا ممنوع — پیش‌تر items=[] یک SessionLog می‌ساخت و تاریخ کلاس را
    # قفل می‌کرد (ثبت واقعی بعدی ۴۰۹ می‌گرفت). مرز HTTP ⇒ ۴۲۲ (رفتار استاندارد FastAPI).
    items: List[AttendanceItem] = Field(min_length=1)

class SmsSendRequest(BaseModel):
    target_group: str
    message_text: str

class ChangePasswordRequest(BaseModel):
    mobile: str
    old_password: str
    new_password: str

class StudentProfileInfo(BaseModel):
    name: str
    national_code: str
    student_mobile: str
    parent_mobile: str
    address: str
    is_suspended: bool = False

class FullStudentProfile(BaseModel):
    info: StudentProfileInfo
    classes: List[str]
    transactions: List[str]
    total_debt: int

class TeacherProfileInfo(BaseModel):
    name: str
    mobile: str
    national_code: str
    status: str  # فعال/غیرفعال
    profile_image: Optional[str] = None
    teacher_code: Optional[int] = None


class TeacherCollaborationSummary(BaseModel):
    period_days: int = 30
    period_start: str
    period_end: str
    average_delay_minutes: float
    delay_samples_count: int
    live_sessions_last_30_days: int
    total_settlements_count: int
    total_settled_amount: int
    auto_ended_sessions_count: int
    auto_ended_last_30_days_count: int


class FullTeacherProfile(BaseModel):
    info: TeacherProfileInfo
    total_students: int
    total_revenue: int  # درآمدزایی کل
    active_classes_count: int
    classes: List[str]  # لیست نام کلاس‌ها
    collaboration_summary: Optional[TeacherCollaborationSummary] = None

class ClassReportInfo(BaseModel):
    title: str
    code: str
    teacher_name: str
    session_count: int  # تعداد جلسات برگزار شده
    total_students: int
    total_revenue: int  # کل درآمد وصول شده
    total_debt: int  # کل مطالبات (بدهی‌ها)

class ClassStudentData(BaseModel):
    name: str
    mobile: str
    paid: int
    debt: int

class ClassSessionHistory(BaseModel):
    date: str
    present_count: int
    absent_count: int

class FullClassReport(BaseModel):
    info: ClassReportInfo
    students: List[ClassStudentData]
    sessions: List[ClassSessionHistory]

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

# FIX: Bug 22 - apply the national-code checksum to this write path.
class StudentUpdate(NationalCodeRequest):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    father_name: Optional[str] = None
    national_code: Optional[str] = None
    birth_date: Optional[str] = None
    student_mobile: Optional[str] = None
    parent_mobile: Optional[str] = None
    home_phone: Optional[str] = None
    address: Optional[str] = None
    study_status: Optional[str] = None
    gender: Optional[str] = None
    version: Optional[int] = None

# FIX: Bug 22 - apply the national-code checksum to this write path.
class TeacherUpdate(NationalCodeRequest):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    father_name: Optional[str] = None
    national_code: Optional[str] = None
    birth_date: Optional[str] = None
    mobile: Optional[str] = None
    password: Optional[str] = None
    home_phone: Optional[str] = None
    marital_status: Optional[str] = None
    gender: Optional[str] = None
    employment_type: Optional[str] = None
    card_number: Optional[str] = None
    profile_image: Optional[str] = None
    version: Optional[int] = None

class PersonListItem(BaseModel):
    id: int
    name: str
    national_code: str
    mobile: str
    role: str  # 'student' or 'teacher'
    is_suspended: bool = False


# FIX(security): آیتم امن لیست معلم‌ها — بدون password، بدون card_number، بدون national_code.
class TeacherListItem(BaseModel):
    id: int
    first_name: str
    last_name: str
    mobile: Optional[str] = None
    teacher_code: Optional[int] = None
    profile_image: Optional[str] = None
    is_approved: bool = False
    is_suspended: bool = False


# FIX(security): آیتم امن تاریخچه پیامک — message_text باید قبل از ساخت، ماسک شده باشد (کدهای OTP).
class SmsHistoryItem(BaseModel):
    id: int
    target_group: Optional[str] = None
    message_text: Optional[str] = None
    sent_count: Optional[int] = None
    date: Optional[str] = None


# 1. جستجوی دانش‌آموزان (همه یا با فیلتر)

class TransactionUpdate(BaseModel):
    amount: int
    description: str
    date: str


# 1. دریافت لیست کامل تراکنش‌ها (با قابلیت جستجو)

class StudentAttendanceHistoryRequest(BaseModel):
    student_id: int
    course_id: int

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
    enrollment_id: Optional[int] = None  # اتصال پرداخت به یک ثبت‌نام خاص (اختیاری؛ اگر خالی باشد و شاگرد فقط یک ثبت‌نام فعال داشته باشد، خودکار وصل می‌شود)
    idempotency_key: Optional[str] = None  # FIX (audit-v2/idempotency): اختیاری و backward-compatible — کلاینت قدیمی نفرستد = رفتار فعلی

class PrintReceiptRequest(BaseModel):
    transaction_id: int
    print_type: str  # "print" or "pdf"

class TransactionTestData(BaseModel):
    student_id: int
    amount: int = Field(gt=0)  # FIX: Bug 22 - even the payment diagnostic must require a positive credit.
    target_wallet: str
    description: str
    payment_method: str
    date: str

class SettleRequest(BaseModel):
    session_ids: List[int]

# FIX: Bug 22 - apply the national-code checksum to this write path.
class StudentRegisterAndEnrollRequest(NationalCodeRequest):
    first_name: str
    last_name: str
    father_name: str
    national_code: str
    birth_date: str
    student_mobile: str
    parent_mobile: str
    home_phone: str
    address: str
    study_status: str
    gender: str
    course_id: Optional[int] = None
    total_tuition: Optional[int] = 0
    paid_amount: int = Field(default=0, ge=0)  # FIX: Bug 22 - permit unpaid registration, not null/negative payments.
    payment_method: Optional[str] = "-"
    receiver: Optional[str] = "-"
    discount_type: Optional[str] = "none"
    discount_value: Optional[int] = 0
    register_date: Optional[str] = "1404/09/01"
    shift: Optional[str] = "عصر"
    installments: Optional[List[InstallmentCreate]] = None

class BulkSmsRequest(BaseModel):
    student_ids: List[int]

class BulkSuspendRequest(BaseModel):
    course_ids: List[int]

class ParentOtpRequest(BaseModel):
    mobile: str

class ParentLoginRequest(BaseModel):
    mobile: str
    otp: str

class ChildSelectRequest(BaseModel):
    student_id: int
    temp_token: str

class InstituteSettingsModel(BaseModel):
    name: str
    logo_path: Optional[str] = None
    address: str
    phone: str
    official_email: Optional[str] = None
    footer_text: Optional[str] = "با تشکر از اعتماد شما - آموزشگاه هوشمند خوارزمی"
    card_number: Optional[str] = "۶۰۳۷۹۹۷۹۷۹۷۹۷۹۷۹"
    manager_mobile_1: Optional[str] = "09121112222"
    manager_mobile_2: Optional[str] = "09123334444"
    card_number_1: Optional[str] = "۶۰۳۷۹۹۷۹۷۹۷۹۷۹۷۹"
    card_holder_1: Optional[str] = "خانم لطفی"
    card_number_2: Optional[str] = "۵۸۹۲۱۰۱۰۱۰۱۰۱۰۱۰"
    card_holder_2: Optional[str] = "آقای علوی"
    teachers_active: Optional[bool] = True
    live_session_max_minutes: Optional[int] = 180
    teacher_settlement_alert_days: Optional[int] = Field(default=None, ge=1, le=3650)


# ==========================================
# 🆕 طرح‌واره‌ی جدول قیمت‌گذاری ۵ نفره 🆕
# ==========================================
class PricingRowModel(BaseModel):
    category: str
    count_1: int
    count_2: int
    count_3: int
    count_4: int
    count_5: int

class PricingTableUpdateModel(BaseModel):
    rows: List[PricingRowModel]
