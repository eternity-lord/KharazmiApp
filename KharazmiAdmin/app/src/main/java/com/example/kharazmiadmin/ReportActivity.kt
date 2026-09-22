package com.example.kharazmiadmin

import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.print.PrintAttributes
import android.print.PrintManager
import android.view.View
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.*
import androidx.lifecycle.lifecycleScope
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.http.GET
import retrofit2.http.Query

// مدل‌های داده برای رتروفیت جدید گزارش‌گیری متمرکز
data class FinancialSummaryResponse(
    val user_type: String,
    val year: Int,
    val month: Int,
    val monthly: FinancialMetrics,
    val yearly: FinancialMetrics,
    // O-10: پرداخت‌های بی‌تاریخ در جمع‌های ماه/سال نمی‌آیند؛ این دو فیلد آن‌ها را آشکار می‌کنند.
    // nullable با پیش‌فرض تا اپ با پاسخ سرورِ قدیمی هم نشکند.
    val undated_count: Int? = null,
    val undated_amount: Long? = null
)

data class FinancialMetrics(
    val total: Long,
    val collected: Long,
    val uncollected: Long
)

data class PaymentTimelineItem(
    val transaction_id: Int? = null, val date: String? = null,
    val amount: Long? = null, val target_wallet: String? = null,
    val payment_link: String? = null
)

data class NextInstallmentItem(
    val id: Int? = null, val amount: Long? = null, val due_date: String? = null,
    val remaining_amount: Long? = null, val payment_link: String? = null
)

data class StudentStatementResponse(
    val student_id: Int,
    val student_name: String,
    val student_code: String,
    val total_paid_institute: Long,
    val total_debt_institute: Long,
    val teacher_name: String? = null,
    val payment_timeline: List<PaymentTimelineItem> = emptyList(),
    val next_installment: NextInstallmentItem? = null,
    val payment_link: String? = null,
    val institute_card_number: String,
    val institute_name: String,
    val address: String,
    val phone: String,
    val footer_text: String
)

data class SearchStudentItem(
    val type: String,
    val id: Int,
    val title: String,
    val subtitle: String,
    val info: String,
    val student_id: Int? = null
)

data class TeacherItem(
    val id: Int,
    // FIX(null-data): نام legacy ممکن است null باشد — null‌پذیر تا فیلتر گزارش (لیست مربیان)
    // با یک رکورد ناقص نشکند؛ فال‌بک در محل نمایش.
    val first_name: String? = null,
    val last_name: String? = null
)

interface ReportNewApi {
    @GET("teachers/list")
    suspend fun getTeachersList(): List<TeacherItem>

    @GET("reports/financial_summary")
    suspend fun getFinancialSummary(
        @Query("user_type") userType: String,
        @Query("teacher_id") teacherId: Int?,
        @Query("year") year: Int?,
        @Query("month") month: Int?
    ): FinancialSummaryResponse

    @GET("finance/search_advanced")
    suspend fun searchAdvanced(
        @Query("query") query: String
    ): List<SearchStudentItem>

    @GET("reports/student_statement")
    suspend fun getStudentStatement(
        @Query("student_id") studentId: Int
    ): StudentStatementResponse
}

class ReportActivity : BaseActivity() {

    private lateinit var api: ReportNewApi
    
    // فیلترها و کامپوننت‌های محدوده
    private lateinit var rgReportScope: RadioGroup
    private lateinit var rbScopeInstitute: RadioButton
    private lateinit var rbScopeTeacher: RadioButton
    private lateinit var tilTeacherFilter: TextInputLayout
    private lateinit var acTeacherFilter: AutoCompleteTextView
    private lateinit var acYearFilter: AutoCompleteTextView
    private lateinit var acMonthFilter: AutoCompleteTextView
    private lateinit var btnFetchFinancialSummary: Button
    // O-10: خط هشدار پول بی‌تاریخ (nullable: اگر چیدمان قدیمی بود، اپ نباید بشکند)
    private var tvUndatedWarning: TextView? = null

    // مقادیر خروجی آمار مالی
    private lateinit var tvMonthlyTitle: TextView
    private lateinit var tvMonthlyTotal: TextView
    private lateinit var tvMonthlyCollected: TextView
    private lateinit var tvMonthlyUncollected: TextView
    
    private lateinit var cardYearlySummary: View
    private lateinit var tvYearlyTitle: TextView
    private lateinit var tvYearlyTotal: TextView
    private lateinit var tvYearlyCollected: TextView
    private lateinit var tvYearlyUncollected: TextView

    // بخش صورت‌حساب دانش‌آموز
    private lateinit var etStudentSearchName: TextInputEditText
    private lateinit var btnSearchStudentStatement: Button
    private lateinit var llStatementResult: View
    private lateinit var tvStatementStudentName: TextView
    private lateinit var tvStatementStudentCode: TextView
    private lateinit var tvStatementPaid: TextView
    private lateinit var tvStatementDebt: TextView
    private lateinit var tvStatementTeacher: TextView
    private lateinit var tvStatementNextDue: TextView
    private lateinit var tvStatementTimeline: TextView
    private lateinit var btnStatementPay: Button
    private lateinit var btnPrintStatement: Button

    // حالت‌ها و متغیرهای کمکی
    private var teachersList: List<TeacherItem> = emptyList()
    private var selectedTeacherId: Int? = null
    private var currentUserRole: String = ""
    private var currentStudentIdForPrint: Int? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_report)

        // ۱. انتساب ویوها
        rgReportScope = findViewById(R.id.rgReportScope)
        rbScopeInstitute = findViewById(R.id.rbScopeInstitute)
        rbScopeTeacher = findViewById(R.id.rbScopeTeacher)
        tilTeacherFilter = findViewById(R.id.tilTeacherFilter)
        acTeacherFilter = findViewById(R.id.acTeacherFilter)
        acYearFilter = findViewById(R.id.acYearFilter)
        acMonthFilter = findViewById(R.id.acMonthFilter)
        btnFetchFinancialSummary = findViewById(R.id.btnFetchFinancialSummary)
        tvUndatedWarning = findViewById(R.id.tvUndatedWarning)

        tvMonthlyTitle = findViewById(R.id.tvMonthlyTitle)
        tvMonthlyTotal = findViewById(R.id.tvMonthlyTotal)
        tvMonthlyCollected = findViewById(R.id.tvMonthlyCollected)
        tvMonthlyUncollected = findViewById(R.id.tvMonthlyUncollected)

        cardYearlySummary = findViewById(R.id.cardYearlySummary)
        tvYearlyTitle = findViewById(R.id.tvYearlyTitle)
        tvYearlyTotal = findViewById(R.id.tvYearlyTotal)
        tvYearlyCollected = findViewById(R.id.tvYearlyCollected)
        tvYearlyUncollected = findViewById(R.id.tvYearlyUncollected)

        etStudentSearchName = findViewById(R.id.etStudentSearchName)
        btnSearchStudentStatement = findViewById(R.id.btnSearchStudentStatement)
        llStatementResult = findViewById(R.id.llStatementResult)
        tvStatementStudentName = findViewById(R.id.tvStatementStudentName)
        tvStatementStudentCode = findViewById(R.id.tvStatementStudentCode)
        tvStatementPaid = findViewById(R.id.tvStatementPaid)
        tvStatementDebt = findViewById(R.id.tvStatementDebt)
        tvStatementTeacher = findViewById(R.id.tvStatementTeacher)
        tvStatementNextDue = findViewById(R.id.tvStatementNextDue)
        tvStatementTimeline = findViewById(R.id.rvPaymentTimeline)
        btnStatementPay = findViewById(R.id.btnStatementPay)
        btnPrintStatement = findViewById(R.id.btnPrintStatement)
        
        ButtonAnimator.applyPillScaleAnimation(btnFetchFinancialSummary)
        ButtonAnimator.applyPillScaleAnimation(btnSearchStudentStatement)
        ButtonAnimator.applyPillScaleAnimation(btnPrintStatement)

        // ۲. دریافت اطلاعات ورود و امنیت مربی
        val credsPrefs = getSharedPreferences("UserCreds", Context.MODE_PRIVATE)
        currentUserRole = credsPrefs.getString("USER_ROLE", "") ?: ""

        val retrofit = RetrofitClient.getInstance(this)
        api = retrofit.create(ReportNewApi::class.java)

        // ۳. پر کردن گزینه‌های سال و ماه شمسی
        setupDateDropdowns()

        // ۴. بررسی دسترسی‌ها
        if (currentUserRole == "teacher") {
            // مخفی‌سازی کامل بخش انتخاب آموزشگاه/معلم برای مربی لاگین شده
            findViewById<View>(R.id.cardReportTypeSelector).visibility = View.GONE
            tilTeacherFilter.visibility = View.GONE
            rbScopeTeacher.isChecked = true
            // لود اطلاعات خودش به صورت مستقیم
            fetchReport("teacher")
        } else {
            // مدیر یا منشی
            fetchTeachersList()
            rgReportScope.setOnCheckedChangeListener { _, checkedId ->
                if (checkedId == R.id.rbScopeTeacher) {
                    tilTeacherFilter.visibility = View.VISIBLE
                    cardYearlySummary.visibility = View.VISIBLE
                } else {
                    tilTeacherFilter.visibility = View.GONE
                    cardYearlySummary.visibility = View.GONE
                }
            }
        }

        // ۵. دکمه دریافت گزارش آمار مالی
        btnFetchFinancialSummary.setOnClickListener {
            val scope = if (rbScopeTeacher.isChecked) "teacher" else "institute"
            fetchReport(scope)
        }

        // ۶. دکمه جستجوی صورت‌حساب دانش‌آموز
        btnSearchStudentStatement.setOnClickListener {
            performStudentSearch()
        }

        // ۷. دکمه پرینت و چاپ رسمی صورت‌حساب
        btnPrintStatement.setOnClickListener {
            currentStudentIdForPrint?.let { studentId ->
                printStatementDirect(studentId)
            } ?: Toast.makeText(this, getString(R.string.rpt_no_student), Toast.LENGTH_SHORT).show()
        }
        btnStatementPay.setOnClickListener {
            val url = getString(R.string.rpt_payment_link_fallback)
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        }
    }

    private fun setupDateDropdowns() {
        // سال‌های شمسی انتخابی
        val years = arrayOf("1404", "1405", "1406", "1407")
        val yearAdapter = ArrayAdapter(this, android.R.layout.simple_dropdown_item_1line, years)
        acYearFilter.setAdapter(yearAdapter)

        // ماه‌های شمسی انتخابی
        val months = arrayOf("01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12")
        val monthAdapter = ArrayAdapter(this, android.R.layout.simple_dropdown_item_1line, months)
        acMonthFilter.setAdapter(monthAdapter)

        // محاسبه حدودی سال و ماه فعلی شمسی جهت نمایش اولیه
        val calendar = java.util.Calendar.getInstance()
        val gy = calendar.get(java.util.Calendar.YEAR)
        val gm = calendar.get(java.util.Calendar.MONTH) + 1
        val gd = calendar.get(java.util.Calendar.DAY_OF_MONTH)

        var jy = gy - 621
        if (gm < 3 || (gm == 3 && gd < 21)) {
            jy = gy - 622
        }
        val jm = when (gm) {
            1 -> 10
            2 -> 11
            3 -> if (gd < 21) 12 else 1
            4 -> if (gd < 21) 1 else 2
            5 -> if (gd < 21) 2 else 3
            6 -> if (gd < 21) 3 else 4
            7 -> if (gd < 21) 4 else 5
            8 -> if (gd < 21) 5 else 6
            9 -> if (gd < 21) 6 else 7
            10 -> if (gd < 21) 7 else 8
            11 -> if (gd < 21) 8 else 9
            12 -> if (gd < 21) 9 else 10
            else -> 1
        }

        acYearFilter.setText(jy.toString(), false)
        acMonthFilter.setText(String.format(java.util.Locale.US, "%02d", jm), false)
    }

    private fun fetchTeachersList() {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val list = api.getTeachersList()
                teachersList = list
                withContext(Dispatchers.Main) {
                    // FIX(null-data): نام ناقص/خالی نباید «null» یا ردیف خالی در فیلتر معلم بدهد.
                    val fallbackName = getString(R.string.common_person_unknown)
                    val teacherNames = list.map {
                        "${it.first_name ?: ""} ${it.last_name ?: ""}".trim().ifEmpty { fallbackName } + " (${it.id})"
                    }
                    val teacherAdapter = ArrayAdapter(this@ReportActivity, android.R.layout.simple_dropdown_item_1line, teacherNames)
                    acTeacherFilter.setAdapter(teacherAdapter)

                    acTeacherFilter.setOnItemClickListener { _, _, position, _ ->
                        selectedTeacherId = list[position].id
                    }
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ReportActivity, getString(R.string.rpt_tutors_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun fetchReport(scope: String) {
        val yearStr = acYearFilter.text.toString().trim()
        val monthStr = acMonthFilter.text.toString().trim()

        val yearVal = yearStr.toIntOrNull()
        val monthVal = monthStr.toIntOrNull()

        if (scope == "teacher" && currentUserRole != "teacher" && selectedTeacherId == null) {
            Toast.makeText(this, getString(R.string.rpt_pick_tutor), Toast.LENGTH_SHORT).show()
            return
        }

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val summary = api.getFinancialSummary(
                    userType = scope,
                    teacherId = if (currentUserRole == "teacher") null else selectedTeacherId,
                    year = yearVal,
                    month = monthVal
                )

                withContext(Dispatchers.Main) {
                    tvMonthlyTitle.text = getString(R.string.rpt_monthly_title, yearStr, monthStr)
                    tvMonthlyTotal.text = getString(R.string.common_toman_format, summary.monthly.total)
                    tvMonthlyCollected.text = getString(R.string.common_toman_format, summary.monthly.collected)
                    tvMonthlyUncollected.text = getString(R.string.common_toman_format, summary.monthly.uncollected)

                    // O-10: هشدار «پول بی‌تاریخ» — مبلغی که در جمع‌های ماه/سالِ بالا نیست.
                    val undatedAmount = summary.undated_amount ?: 0L
                    val undatedCount = summary.undated_count ?: 0
                    tvUndatedWarning?.let { warning ->
                        if (undatedAmount > 0) {
                            warning.text = getString(
                                R.string.rpt_undated_warning,
                                String.format("%,d", undatedCount),
                                String.format("%,d", undatedAmount)
                            )
                            warning.visibility = View.VISIBLE
                        } else {
                            warning.visibility = View.GONE
                        }
                    }

                    if (scope == "teacher") {
                        cardYearlySummary.visibility = View.VISIBLE
                        tvYearlyTitle.text = getString(R.string.rpt_yearly_title, yearStr)
                        tvYearlyTotal.text = getString(R.string.common_toman_format, summary.yearly.total)
                        tvYearlyCollected.text = getString(R.string.common_toman_format, summary.yearly.collected)
                        tvYearlyUncollected.text = getString(R.string.common_toman_format, summary.yearly.uncollected)
                    } else {
                        cardYearlySummary.visibility = View.GONE
                    }
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ReportActivity, getString(R.string.rpt_calc_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun performStudentSearch() {
        val query = etStudentSearchName.text.toString().trim()
        if (query.isEmpty()) {
            Toast.makeText(this, getString(R.string.rpt_enter_name), Toast.LENGTH_SHORT).show()
            return
        }

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                // جستجوی چندمنظوره دانش‌آموزان
                val results = api.searchAdvanced(query)
                val studentsOnly = results.filter { it.type == "student" }

                withContext(Dispatchers.Main) {
                    if (studentsOnly.isEmpty()) {
                        Toast.makeText(this@ReportActivity, getString(R.string.rpt_student_nf), Toast.LENGTH_LONG).show()
                        llStatementResult.visibility = View.GONE
                    } else if (studentsOnly.size == 1) {
                        val stId = studentsOnly[0].student_id ?: studentsOnly[0].id
                        fetchStudentStatement(stId)
                    } else {
                        // انتخاب از میان لیست چندتایی
                        showMultipleStudentsDialog(studentsOnly)
                    }
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ReportActivity, getString(R.string.rpt_search_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun showMultipleStudentsDialog(list: List<SearchStudentItem>) {
        val names = list.map { "${it.title} - ${it.subtitle}" }.toTypedArray()
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.rpt_pick_title))
            .setItems(names) { _, which ->
                val selected = list[which]
                val stId = selected.student_id ?: selected.id
                fetchStudentStatement(stId)
            }
            .setNegativeButton(getString(R.string.common_cancel), null)
            .show()
    }

    private fun fetchStudentStatement(studentId: Int) {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val stmt = api.getStudentStatement(studentId)
                withContext(Dispatchers.Main) {
                    currentStudentIdForPrint = studentId
                    llStatementResult.visibility = View.VISIBLE
                    tvStatementStudentName.text = getString(R.string.rpt_stmt_name, stmt.student_name)
                    tvStatementStudentCode.text = getString(R.string.rpt_stmt_code, stmt.student_code)
                    tvStatementStudentName.setOnClickListener {
                        startActivity(Intent(this@ReportActivity, StudentProfileActivity::class.java).apply {
                            putExtra("STUDENT_ID", studentId)
                        })
                    }
                    tvStatementPaid.text = getString(R.string.common_toman_format, stmt.total_paid_institute)
                    tvStatementDebt.text = getString(R.string.common_toman_format, stmt.total_debt_institute)
                    tvStatementTeacher.text = "معلم بدهکار: ${stmt.teacher_name ?: "بدون معلم"}"
                    tvStatementNextDue.text = stmt.next_installment?.let {
                        "قسط بعدی: ${it.due_date ?: "نامشخص"} | ${it.remaining_amount ?: it.amount ?: 0} تومان"
                    } ?: "قسط بازی ندارد"
                    tvStatementTimeline.text = stmt.payment_timeline.joinToString("\n") {
                        "${it.date ?: "تاریخ نامشخص"} — ${it.amount ?: 0} تومان"
                    }.ifEmpty { "تاریخچه پرداختی وجود ندارد" }
                    btnStatementPay.visibility = if (stmt.next_installment != null) View.VISIBLE else View.GONE
                    btnStatementPay.setOnClickListener {
                        val link = stmt.next_installment?.payment_link ?: stmt.payment_link
                        if (!link.isNullOrBlank()) startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(link)))
                    }
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ReportActivity, getString(R.string.rpt_stmt_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun printStatementDirect(studentId: Int) {
        Toast.makeText(this, getString(R.string.rpt_rendering), Toast.LENGTH_SHORT).show()
        
        val webView = WebView(this)
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) {
                val printManager = getSystemService(Context.PRINT_SERVICE) as PrintManager
                val printAdapter = webView.createPrintDocumentAdapter("Kharazmi_Student_Statement")
                val jobName = getString(R.string.rpt_job_name)
                printManager.print(jobName, printAdapter, PrintAttributes.Builder().build())
            }
        }

        val token = SecureLoginStore.getToken(this)  // FIX M22: توکن از حافظه‌ی رمزشده.
        val headers = HashMap<String, String>()
        if (token.isNotEmpty()) {
            headers["Authorization"] = "Bearer $token"
        }

        val retrofit = RetrofitClient.getInstance(this)
        val baseUrl = retrofit.baseUrl().toString()
        val url = "${baseUrl}reports/student_statement/print?student_id=$studentId"

        webView.loadUrl(url, headers)
    }
}
