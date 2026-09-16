package com.example.kharazmiadmin

import com.google.gson.annotations.SerializedName

// ==========================================
// 1. عمومی و پاسخ‌های ساده
// ==========================================
data class SimpleResponse(val message: String, val price_warning: String? = null) // FIX (audit-v2/blind-approve-2c): هشدار مبلغ؛ غایب=Gson→null و همه مصرف‌کننده‌های قبلی سالم

// پاسخ اختصاصی برای تعلیق
data class SuspendResponse(val message: String, val is_suspended: Boolean)

// ==========================================
// 2. احراز هویت (Auth)
// ==========================================
data class LoginRequest(val mobile: String, val password: String?)
data class LoginResponse(
    val status: String,
    val role: String,
    val user_id: Int,
    val name: String,
    val message: String,
    val sub_role: String? = null,
    val token: String? = null,
    val branch_id: Int? = null
)
data class ChangePasswordRequest(
    val mobile: String,
    val old_password: String,
    val new_password: String
)

// ==========================================
// 3. معلمان (Teachers)
// ==========================================
data class TeacherRegisterData(
    val first_name: String,
    val last_name: String,
    val father_name: String,
    val national_code: String,
    val birth_date: String,
    val mobile: String,
    val password: String,
    val home_phone: String,
    val card_number: String,
    val marital_status: String,
    val gender: String,
    val employment_type: String,
    val profile_image: String? = null
)

data class TeacherSimple(val id: Int, val first_name: String, val last_name: String)

// ==========================================
// 4. دانش‌آموزان (Students)
// ==========================================
data class StudentRegisterData(
    val first_name: String,
    val last_name: String,
    val father_name: String,
    val national_code: String,
    val birth_date: String,
    val student_mobile: String,
    val parent_mobile: String,
    val home_phone: String,
    val address: String,
    val study_status: String,
    val gender: String
)

data class RegisterResponse(val message: String, val id: Int, val teacher_code: Int? = null, val initial_password: String? = null)

data class StudentSearchItem(val id: Int, val name: String)
data class SearchItem(val id: Int, val name: String)

data class StudentItem(val student_id: Int, val student_name: String, val debt: Long, val enrollment_id: Int)

// ==========================================
// 5. کلاس‌ها (Classes)
// ==========================================
data class ClassSubmitData(
    val title: String,
    val code: String,
    val teacher_id: Int,
    val education_type: String,
    val grade_level: String,
    val gender_type: String,
    val days_of_week: String,
    val class_time: String,
    val teacher_session_price: Long,
    val bg_color: String,
    val is_admin_created: Boolean = false
)

data class ClassResponse(val message: String, val id: Int, val status: String? = "success")

data class ClassItem(val id: Int, val title: String, val code: String)

data class ClassItemFull(
    val id: Int, val title: String, val code: String,
    val days_of_week: String, val class_time: String
)

data class PendingClassItem(
    val id: Int,
    val title: String,
    val teacher_name: String,
    val teacher_price: Long,
    val days: String,
    val time: String,
    val base_institute_share: Long,
    val code: String? = null
)

data class ClassDetailsResponse(val students: List<StudentItem>)

// ==========================================
// 6. مالی و ثبت نام (Financial & Enrollment)
// ==========================================
data class InvoiceSubmitData(
    val student_id: Int,
    val course_id: Int,
    val register_date: String,
    val shift: String,
    val total_tuition: Long,
    val paid_amount: Long,
    val payment_method: String,
    val receiver: String
)

data class SubmitResponse(val message: String, val enrollment_id: Int)

data class InstallmentCreate(
    val amount: Int,
    val due_date: String
)

data class AddStudentToClassData(
    val student_id: Int,
    val course_id: Int,
    val register_date: String,
    val shift: String,
    val total_tuition: Int,
    val paid_amount: Int,
    val payment_method: String,
    val receiver: String,
    val discount_type: String = "none",
    val discount_value: Int = 0,
    val installments: List<InstallmentCreate>? = null
)

data class AddStudentResponse(val message: String, val enrollment_id: Int)

// ==========================================
// 7. حضور و غیاب (Attendance)
// ==========================================
data class AttendanceLogRequest(val course_id: Int, val date: String)
data class AttendanceRecord(val student_id: Int, val name: String, val status: String)
data class AttendanceSubmitItem(val student_id: Int, val status: String, val excused: Boolean = false)
data class AttendanceSubmitData(val course_id: Int, val date: String, val items: List<AttendanceSubmitItem>)
data class AttResponse(val message: String, val present_count: Int)

data class SessionSubmitData(val course_id: Int, val date: String, val items: List<SessionItem>)
data class SessionItem(val student_id: Int, val status: String, val excused: Boolean = false)
data class SessionResponse(
    val message: String, 
    val details: SessionFinancialDetails,
    val session_id: Int? = null,
    val session_code: Int? = null
)
data class SessionFinancialDetails(
    val present_count: Int,
    val cost_per_student: Long,
    val teacher_share: Long,
    val institute_share: Long
)

// ==========================================
// 8. ویرایش پروفایل (Edit Profile)
// ==========================================
data class StudentUpdate(
    val first_name: String? = null,
    val last_name: String? = null,
    val father_name: String? = null,
    val national_code: String? = null,
    val birth_date: String? = null,
    val student_mobile: String? = null,
    val parent_mobile: String? = null,
    val home_phone: String? = null,
    val address: String? = null,
    val study_status: String? = null,
    val gender: String? = null,
    val version: Int? = null
)

data class TeacherUpdate(
    val first_name: String? = null,
    val last_name: String? = null,
    val father_name: String? = null,
    val national_code: String? = null,
    val birth_date: String? = null,
    val mobile: String? = null,
    val home_phone: String? = null,
    val marital_status: String? = null,
    val gender: String? = null,
    val employment_type: String? = null,
    val card_number: String? = null,
    val version: Int? = null
)

data class StudentRawProfile(
    val id: Int,
    val first_name: String,
    val last_name: String,
    val father_name: String?,
    val national_code: String,
    val birth_date: String?,
    val student_mobile: String,
    val parent_mobile: String?,
    val home_phone: String?,
    val address: String?,
    val study_status: String?,
    val gender: String?,
    val student_code: Int? = null,
    val version: Int = 1
)

data class TeacherRawProfile(
    val id: Int,
    val first_name: String,
    val last_name: String,
    val father_name: String?,
    val national_code: String,
    val birth_date: String?,
    val mobile: String,
    val home_phone: String?,
    val marital_status: String?,
    val gender: String?,
    val employment_type: String?,
    val card_number: String?,
    val teacher_code: Int? = null,
    val version: Int = 1
)

data class PersonListItem(
    val id: Int,
    val name: String,
    val national_code: String,
    val mobile: String,
    val role: String,
    val is_suspended: Boolean = false
)

// ==========================================
// مدیریت تراکنش‌ها (Transaction Management)
// ==========================================
data class TransactionFullItem(
    val id: Int,
    val student_id: Int,
    val student_name: String,
    val course_id: Int?,
    val course_name: String,
    val amount: Long,
    val date: String,
    val description: String?,
    val type: String,
    val remittance_number: Int? = null
)

data class TransactionUpdateData(
    val amount: Long,
    val description: String,
    val date: String
)

data class AdvancedSearchItem(
    val type: String,
    val id: Int,
    val title: String,
    val subtitle: String,
    val info: String,
    val student_id: Int? = null,
    val course_id: Int? = null,
    // فیلدهای تفکیک بدهی در سرچ
    val debt_teacher: Long? = 0,
    val debt_institute: Long? = 0,
    val total_debt: Long? = 0,
    val unpaid_sessions: Int? = 0,
    val students_in_class: List<SimpleStudentItem>? = null
)

data class SimpleStudentItem(
    val id: Int,
    val name: String,
    val debt: Long,
    @SerializedName("debt_teacher") val debtTeacher: Long = 0,
    @SerializedName("debt_institute") val debtInstitute: Long = 0,
    @SerializedName("total_debt") val totalDebt: Long = 0
)

// ==========================================
// مدل ثبت مالی جدید
// ==========================================
data class FinanceSubmitData(
    val student_id: Int,
    val amount: Long,
    val target_wallet: String,  // "teacher" یا "institute" یا "both"
    val description: String,
    val payment_method: String,
    val date: String,
    val amount_institute: Long? = null,
    val amount_teacher: Long? = null,
    val enrollment_id: Int? = null,  // اتصال پرداخت به ثبت‌نام؛ null یعنی شارژ عمومی (سرور تک‌ثبت‌نامی را خودکار وصل می‌کند)
    val idempotency_key: String? = null  // FIX (audit-v2/idempotency): کلید retry — قبل از اولین تلاش ساخته و تا موفقیت حفظ می‌شود
)

data class FinanceResponse(
    val message: String,
    val receipt_id: Int,
    val new_balance_teacher: Long,
    val new_balance_institute: Long,
    val duplicate: Boolean = false  // FIX (audit-v2/idempotency): true یعنی replay شد و پرداخت تکراری ثبت نشد
)

// ==========================================
// 9. پروفایل کامل (Full Profile) - ✅ اضافه شد
// ==========================================
// این مدل‌ها برای نمایش پروفایل دانش‌آموز ضروری هستند
data class FullStudentProfile(
    val info: StudentInfo,
    val classes: List<String>,
    val transactions: List<String>,
    @SerializedName("wallet_total") val walletTotal: Long = 0,
    @SerializedName("wallet_teacher") val walletTeacher: Long = 0,
    @SerializedName("wallet_institute") val walletInstitute: Long = 0,
    @SerializedName("total_debt") val totalDebt: Long = 0,
    @SerializedName("debt_teacher") val debtTeacher: Long = 0,
    @SerializedName("debt_institute") val debtInstitute: Long = 0,
    val total_paid_institute: Long = 0,
    val teachers_financial: List<TeacherFinancialItem>? = null
)

data class TeacherFinancialItem(
    val course_title: String,
    val teacher_name: String,
    val paid_teacher: Long,
    val debt_teacher: Long,
    val paid_institute: Long,
    val debt_institute: Long
)

data class StudentInfo(
    val name: String,
    val national_code: String,
    val student_mobile: String,
    val parent_mobile: String,
    val address: String,
    val is_suspended: Boolean = false,
    val student_code: Int? = null,
    val profile_image: String? = null
)

// ==========================================
// 12. مدیریت کلاس‌ها (Class Management) - ✅ اضافه شد
// ==========================================
data class ClassListItem(
    val id: Int,
    val title: String,
    val code: String,
    val grade_level: String,
    val gender: String,
    val session_count: Int,
    val teacher_id: Int,
    val teacher_name: String?,
    val students_preview: List<String>,
    val total_debt: Long,
    val debt_to_teacher: Long,
    val debt_to_institute: Long,
    val is_suspended: Boolean = false,
    val bg_color: String? = null
)

// ==========================================
// 13. پروفایل کامل معلم (Full Teacher Profile) - ✅ اضافه شد
// ==========================================
data class TeacherCollaborationSummary(
    @SerializedName("period_days") val periodDays: Int = 30,
    @SerializedName("period_start") val periodStart: String = "",
    @SerializedName("period_end") val periodEnd: String = "",
    @SerializedName("average_delay_minutes") val averageDelayMinutes: Double = 0.0,
    @SerializedName("delay_samples_count") val delaySamplesCount: Int = 0,
    @SerializedName("live_sessions_last_30_days") val liveSessionsLast30Days: Int = 0,
    @SerializedName("total_settlements_count") val totalSettlementsCount: Int = 0,
    @SerializedName("total_settled_amount") val totalSettledAmount: Long = 0,
    @SerializedName("auto_ended_sessions_count") val autoEndedSessionsCount: Int = 0,
    @SerializedName("auto_ended_last_30_days_count") val autoEndedLast30DaysCount: Int = 0
)

data class FullTeacherProfile(
    val info: TeacherInfo,
    val total_students: Int,
    val total_revenue: Long,
    val active_classes_count: Int,
    val classes: List<String>,
    @SerializedName("collaboration_summary") val collaborationSummary: TeacherCollaborationSummary? = null
)

data class TeacherInfo(
    val name: String,
    val mobile: String,
    val national_code: String,
    val status: String,
    val card_number: String? = null,
    val teacher_code: Int? = null,
    val profile_image: String? = null
)

// ==========================================
// 10. مدل‌های نمرات (Grades) - ✅ اضافه شد
// ==========================================
data class GradeItem(
    @SerializedName("course_name") val courseName: String, // تبدیل course_name سرور به courseName اندروید
    @SerializedName("exam_title") val examTitle: String,
    val score: Float,
    @SerializedName("max_score") val maxScore: Float,
    val date: String,
    val description: String?
)

data class StudentRegisterAndEnrollRequest(
    val first_name: String,
    val last_name: String,
    val father_name: String,
    val national_code: String,
    val birth_date: String,
    val student_mobile: String,
    val parent_mobile: String,
    val home_phone: String,
    val address: String,
    val study_status: String,
    val gender: String,
    val course_id: Int?,
    val total_tuition: Int,
    val paid_amount: Int,
    val payment_method: String,
    val receiver: String,
    val discount_type: String,
    val discount_value: Int,
    val installments: List<InstallmentCreate>? = null
)

data class ParentContactItem(
    val student_id: Int,
    val student_name: String,
    val student_mobile: String,
    val parent_mobile: String,
    val classes: List<String>
)

data class StudentGradesResponse(
    val grades: List<GradeItem>,
    val averages: Map<String, Double>
)

data class GradeSubmitData(
    val student_id: Int,
    val course_id: Int,
    val exam_title: String,
    val score: Float,
    val max_score: Float,
    val date: String,
    val description: String
)

data class SettleRequest(val session_ids: List<Int>)

data class TeacherPendingSettlementResponse(
    val total_amount: Long,
    val session_count: Int,
    val pending_sessions: List<PendingSettlementSession>
)

data class PendingSettlementSession(
    val session_id: Int,
    val date: String,
    val class_title: String,
    val amount: Long,
    val present_count: Int,
    val session_code: Int? = null
)

data class TeacherSettlementResponse(
    val message: String,
    val settlement_id: Int,
    val total_amount: Long,
    val session_count: Int
)

data class SettlementHistoryItem(
    val id: Int,
    val total_amount: Long,
    val session_count: Int,
    val settled_at: String
)

data class BulkSmsRequest(val student_ids: List<Int>)
data class BulkSuspendRequest(val course_ids: List<Int>)

data class StudentInstallmentItem(
    val id: Int,
    val course_title: String,
    val amount: Long,
    val due_date: String,
    val is_paid: Boolean,
    val paid_at: String
)

data class InstituteSettings(
    val id: Int,
    val name: String,
    val logo_path: String?,
    val address: String,
    val phone: String,
    val official_email: String?,
    val footer_text: String? = null,
    val card_number: String? = null,
    @SerializedName("live_session_max_minutes") val liveSessionMaxMinutes: Int? = null,
    @SerializedName("teacher_settlement_alert_days") val teacherSettlementAlertDays: Int? = null
)

// ==========================================
// 🎥 کلاس‌های زنده (Live Sessions) - جدید 🆕
// ==========================================

// پاسخ شروع کلاس زنده توسط معلم
data class LiveStartResponse(
    val message: String,
    @SerializedName("live_session_id") val liveSessionId: Int,
    @SerializedName("course_id") val courseId: Int,
    val status: String,
    @SerializedName("start_time") val startTime: String?,
    @SerializedName("started_at_ts") val startedAtTs: Long?,
    @SerializedName("max_minutes") val maxMinutes: Int? = null
)

// پاسخ پایان کلاس زنده توسط معلم
data class LiveEndResponse(
    val message: String,
    @SerializedName("live_session_id") val liveSessionId: Int,
    @SerializedName("ended_automatically") val endedAutomatically: Boolean,
    @SerializedName("session_id") val sessionId: Int? = null,
    @SerializedName("session_code") val sessionCode: Int? = null,
    val details: SessionFinancialDetails? = null
)

// وضعیت جلسه‌ی زنده‌ی فعلی معلم (برای رزومه و تایمر داشبورد معلم)
data class LiveCurrentResponse(
    @SerializedName("live_session_id") val liveSessionId: Int,
    @SerializedName("course_id") val courseId: Int,
    @SerializedName("class_title") val classTitle: String = "",
    @SerializedName("course_code") val courseCode: String = "",
    val status: String,
    @SerializedName("start_time") val startTime: String?,
    @SerializedName("started_at_ts") val startedAtTs: Long?,
    @SerializedName("max_minutes") val maxMinutes: Int? = null
)

// آیتم لیست کلاس‌های زنده برای ادمین/منشی
data class LiveSessionItem(
    @SerializedName("live_session_id") val liveSessionId: Int,
    @SerializedName("course_id") val courseId: Int,
    @SerializedName("class_title") val classTitle: String = "",
    @SerializedName("course_code") val courseCode: String = "",
    @SerializedName("teacher_name") val teacherName: String = "",
    @SerializedName("start_time") val startTime: String? = null,
    @SerializedName("started_at_ts") val startedAtTs: Long? = null,
    @SerializedName("elapsed_minutes") val elapsedMinutes: Int = 0,
    @SerializedName("total_enrolled") val totalEnrolled: Int = 0,
    val present: Int = 0,
    val absent: Int = 0,
    val undetermined: Int = 0
)

// دانش‌آموز در لیست لحظه‌ای کلاس زنده
data class LiveRosterStudent(
    @SerializedName("student_id") val studentId: Int,
    @SerializedName("student_name") val studentName: String,
    val status: String, // Present / Late / Absent / UNSET
    val excused: Boolean = false,
    @SerializedName("student_mobile") val studentMobile: String = "",
    @SerializedName("parent_mobile") val parentMobile: String = ""
)

// پاسخ کامل جزئیات زنده‌ی یک کلاس (روستر)
data class LiveRosterResponse(
    @SerializedName("live_session_id") val liveSessionId: Int,
    @SerializedName("course_id") val courseId: Int,
    @SerializedName("class_title") val classTitle: String = "",
    @SerializedName("course_code") val courseCode: String = "",
    @SerializedName("teacher_name") val teacherName: String = "",
    @SerializedName("start_time") val startTime: String? = null,
    @SerializedName("started_at_ts") val startedAtTs: Long? = null,
    @SerializedName("elapsed_minutes") val elapsedMinutes: Int = 0,
    @SerializedName("total_enrolled") val totalEnrolled: Int = 0,
    val present: Int = 0,
    val absent: Int = 0,
    val undetermined: Int = 0,
    val students: List<LiveRosterStudent> = emptyList()
)
