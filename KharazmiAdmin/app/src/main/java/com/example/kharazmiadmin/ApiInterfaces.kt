package com.example.kharazmiadmin

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming
import okhttp3.ResponseBody

// ==========================================
// تمام رابط‌های API اینجا تعریف می‌شوند
// تا با تغییر یک اکتیویتی، بقیه خراب نشوند.
// ==========================================

// 1. اینترفیس قدیمی (برای حضور و غیاب و تایید کلاس)
interface InvoiceApi {
    @GET("classes/{id}/details")
    suspend fun getClassDetails(@Path("id") id: Int): ClassDetailsResponse

    @DELETE("enrollments/{enrollment_id}")
    suspend fun deleteEnrollment(@Path("enrollment_id") id: Int): SimpleResponse
}

// 2. اینترفیس جدید (برای ثبت حواله هوشمند)
data class StudentClassStatus(
    val total_amount: Long,
    val paid_to_teacher: Long,
    val paid_to_institute: Long,
    val due_to_teacher: Long,
    val due_to_institute: Long,
    val course_id: Int? = null,
    val enrollment_id: Int? = null
)

interface NewInvoiceApi {
    @GET("finance/search_advanced")
    suspend fun searchAdvanced(@Query("query") q: String): List<AdvancedSearchItem>

    @POST("finance/pay")
    suspend fun submitPayment(@Body data: FinanceSubmitData): FinanceResponse

    @GET("admin/students/{id}/full_profile")
    suspend fun getFullStudentProfile(@Path("id") id: Int): FullStudentProfile

    @GET("finance/student_class_status")
    suspend fun getStudentClassStatus(
        @Query("student_id") studentId: Int,
        @Query("course_id") courseId: Int?,
        @Query("course_code") courseCode: String?
    ): StudentClassStatus
}

// 3. اینترفیس‌های دیگر (اختیاری برای نظم بیشتر در آینده)
interface ClassApi {
    @GET("classes/list")
    suspend fun getAllClasses(): List<ClassListItem>

    @POST("classes/{id}/suspend")
    suspend fun suspendClass(@Path("id") id: Int): SuspendResponse

    @POST("admin/classes/{id}/suspend_s")
    suspend fun suspendClassAdmin(@Path("id") id: Int): SuspendResponse

    @POST("admin/classes/suspend_bulk")
    suspend fun suspendBulkClasses(@Body req: BulkSuspendRequest): SimpleResponse
}

// ———————————————— اقساط شهریه (A1) — سه endpoint موجود سرور بدون UI ————————————————
interface InstallmentApi {
    @POST("finance/installments")
    suspend fun createInstallment(@Body req: CreateInstallmentRequest): CreateInstallmentResponse

    @POST("finance/installments/{id}/pay")
    suspend fun payInstallment(
        @Path("id") id: Int,
        @Query("payment_method") paymentMethod: String = "نقدی",
        @Query("branch_id") branchId: Int? = null
    ): PayInstallmentResponse

    @POST("finance/installments/{id}/remind")
    suspend fun remindInstallment(@Path("id") id: Int): RemindInstallmentResponse
}

interface FinanceDashboardApi {
    @GET("finance/student/{student_id}/dashboard")
    suspend fun getFinancialDashboard(@Path("student_id") studentId: Int): FinancialDashboardResponse
}

// ==========================================
// Audit Radar - داشبورد تشخیص تقلب (Admin Only)
// ==========================================
interface AuditApi {
    @GET("audit/suspicious_patterns")
    suspend fun getSuspiciousPatterns(): List<AuditAlert>
}

// ==========================================
// Student 360 Timeline - Unified Activity Feed
// ==========================================
interface TimelineApi {
    @GET("students/{id}/timeline")
    suspend fun getTimeline(@Path("id") id: Int): List<TimelineEvent>
}

// ==========================================
// Smart Auto-Dunning - Human-in-the-Loop (Admin Only)
// ==========================================
interface DunningApi {
    @GET("dunning/drafts")
    suspend fun getDrafts(): List<DunningDraft>

    @POST("dunning/send_batch")
    suspend fun sendBatch(@Body req: DunningSendRequest): DunningSendResponse
}

// ==========================================
// Admin Command Center - Unified Dashboard (Admin Only)
// ==========================================
interface DashboardApi {
    @GET("dashboard/kpis")
    suspend fun getKPIs(): DashboardKPIs
}

// ==========================================
// Export to Excel/CSV — سه خروجی ادمین (routers/exports.py)
// FIX Export: @Streaming برای دیتاست 10k+ (بدون نگه‌داشتن کل فایل در حافظه).
// بدون پارامتر هدر: توکن Bearer به‌صورت سراسری توسط RetrofitClient تزریق می‌شود.
// ==========================================
interface ExportApi {
    @Streaming
    @GET("exports/debtors")
    suspend fun exportDebtors(): ResponseBody

    @Streaming
    @GET("exports/overdue_installments")
    suspend fun exportOverdueInstallments(): ResponseBody

    @Streaming
    @GET("exports/audit_alerts")
    suspend fun exportAuditAlerts(): ResponseBody
}
