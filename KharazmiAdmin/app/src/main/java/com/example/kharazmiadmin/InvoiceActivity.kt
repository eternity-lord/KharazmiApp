package com.example.kharazmiadmin

import android.content.Intent
import android.content.Context
import android.os.Bundle
import android.print.PrintAttributes
import android.print.PrintManager
import android.webkit.WebView
import android.graphics.pdf.PdfDocument
import android.graphics.Paint
import android.graphics.Color
import android.os.Environment
import java.io.File
import java.io.FileOutputStream
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.textfield.TextInputEditText
import kotlin.math.abs
import kotlinx.coroutines.*
import java.util.UUID // FIX (audit-v2/idempotency): تولید کلید retry
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.HttpException


// Print Receipt Request Model
data class PrintReceiptRequest(val transaction_id: Int)

// Print Receipt Response Model
data class PrintReceiptResponse(
    val status: String,
    val message: String,
    val print_job_id: String? = null,
    val receipt_data: Map<String, Any>? = null
)

// PDF Receipt Response Model
data class PdfReceiptResponse(
    val status: String,
    val message: String,
    val pdf_filename: String? = null,
    val receipt_data: Map<String, Any>? = null
)

// Remittance Print API Interface
interface RemittancePrintApi {
    @POST("/finance/receipt/print")
    suspend fun printReceipt(@Body req: PrintReceiptRequest): PrintReceiptResponse

    @POST("/finance/receipt/pdf")
    suspend fun generatePdfReceipt(@Body req: PrintReceiptRequest): PdfReceiptResponse
}

// FIX H16: جزئیات رسیدِ سرور-محور برای چاپ مجدد (به‌جای اعتماد به Intent extras).
data class ReceiptDetailsResponse(
    val transaction_id: Int,
    val remittance_number: Any? = null,
    val student_name: String? = null,
    val student_national_code: String? = null,
    val amount: Long? = null,
    val payment_method: String? = null,
    val tracking_code: String? = null,
    val date: String? = null,
    val description: String? = null,
    val target_wallet: String? = null,
    val type: String? = null,
    val is_reversed: Boolean? = null,
    val course_name: String? = null
)

interface ReceiptDetailsApi {
    @GET("/finance/receipt/{transaction_id}")
    suspend fun getReceiptDetails(@Path("transaction_id") id: Long): ReceiptDetailsResponse
}

class InvoiceActivity : BaseActivity() {

    // UI Components
    private lateinit var etSearch: TextInputEditText
    private lateinit var rvResults: RecyclerView
    private lateinit var cardInfo: View
    private lateinit var cardForm: View
    private lateinit var tvStName: TextView
    private lateinit var tvStClass: TextView
    private lateinit var tvUnpaid: TextView
    private lateinit var tvDebt: TextView
    private lateinit var tvDebtTeacher: TextView
    private lateinit var tvDebtInstitute: TextView
    private lateinit var etAmount: TextInputEditText
    private lateinit var etAmountInstitute: TextInputEditText
    private lateinit var tilAmount1: View
    private lateinit var tilAmount2: View
    private lateinit var etDesc: TextInputEditText
    private lateinit var rgPayment: RadioGroup
    private lateinit var layoutWallet: LinearLayout
    private lateinit var rgWallet: RadioGroup
    private lateinit var btnSubmit: Button
    private lateinit var tvDate: TextView
    private var pendingPaymentKey: String? = null // FIX (audit-v2/idempotency): کلید پرداختِ درراه — تا موفقیت زنده، بعد بازنشسته
    private var pendingPaymentSig: String? = null // FIX (audit-v2/idempotency): امضای فرمِ همان پرداخت — تغییر فرم یعنی پرداخت تازه و کلید تازه

    // Logic Variables
    private lateinit var api: NewInvoiceApi
    private var searchJob: Job? = null
    private var selectedStudentId: Int = -1
    private var isAdmin: Boolean = false
    private var currentPersianDate: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_invoice)

        isAdmin = intent.getBooleanExtra(EXTRA_IS_ADMIN, false)

        initViews()
        setupApi()
        setupSearch()
        setupFormLogic()
        applyPrefill(intent)

        if (intent.getStringExtra("MODE") == "REPRINT") {
            // FIX H16: فقط شناسه از Intent؛ بقیه تازه از سرور (ضد-جعل + ضد-stale). IS_MODIFIED فقط مهر نمایشی است.
            val id = intent.getStringExtra("RECEIPT_ID") ?: ""
            val isModified = intent.getBooleanExtra("IS_MODIFIED", false)
            loadAndShowReceipt(id, getString(R.string.invoice_reprint_title), isModified)
        }
    }

    private fun initViews() {
        etSearch = findViewById(R.id.etSearch)
        rvResults = findViewById(R.id.rvSearchResults)
        cardInfo = findViewById(R.id.cardStudentInfo)
        cardForm = findViewById(R.id.cardPaymentForm)
        tvStName = findViewById(R.id.tvStName)
        tvStClass = findViewById(R.id.tvStClass)
        tvUnpaid = findViewById(R.id.tvUnpaidSessions)
        tvDebt = findViewById(R.id.tvTotalDebt)
        tvDebtTeacher = findViewById(R.id.tvDebtTeacher)
        tvDebtInstitute = findViewById(R.id.tvDebtInstitute)
        etAmount = findViewById(R.id.etAmount)
        etAmountInstitute = findViewById(R.id.etAmountInstitute)
        tilAmount1 = findViewById(R.id.tilAmount1)
        tilAmount2 = findViewById(R.id.tilAmount2)
        etDesc = findViewById(R.id.etDesc)
        rgPayment = findViewById(R.id.rgPaymentMethod)
        layoutWallet = findViewById(R.id.layoutWalletSelector)
        rgWallet = findViewById(R.id.rgTargetWallet)
        btnSubmit = findViewById(R.id.btnSubmit)
        tvDate = findViewById(R.id.tvDate)

        rvResults.layoutManager = LinearLayoutManager(this)

        currentPersianDate = getSimplePersianDate()
        tvDate.text = getString(R.string.invoice_date, currentPersianDate)

        if (isAdmin) {
            layoutWallet.visibility = View.VISIBLE
            rgWallet.check(R.id.rbWalletInstitute)
            setupWalletBothLogic()
        } else {
            layoutWallet.visibility = View.GONE
        }
    }

    private fun setupWalletBothLogic() {
        rgWallet.setOnCheckedChangeListener { _, checkedId ->
            if (checkedId == R.id.rbWalletBoth) {
                tilAmount2.visibility = View.VISIBLE
                // تغییر hint برای حالت هر دو
                (tilAmount1 as? com.google.android.material.textfield.TextInputLayout)?.hint = getString(R.string.invoice_hint_teacher)
                (tilAmount2 as? com.google.android.material.textfield.TextInputLayout)?.hint = getString(R.string.invoice_hint_institute)
            } else {
                tilAmount2.visibility = View.GONE
                (tilAmount1 as? com.google.android.material.textfield.TextInputLayout)?.hint = getString(R.string.invoice_hint_amount)
            }
        }
    }

    private fun setupApi() {
        val retrofit = RetrofitClient.getInstance(this)
        api = retrofit.create(NewInvoiceApi::class.java)
    }

    private fun setupSearch() {
        etSearch.addTextChangedListener(object : TextWatcher {
            override fun afterTextChanged(s: Editable?) {
                searchJob?.cancel()
                if (s.isNullOrEmpty()) {
                    rvResults.visibility = View.GONE
                    return
                }

                // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

                searchJob = lifecycleScope.launch(Dispatchers.IO) {
                    delay(500)
                    try {
                        val results = api.searchAdvanced(s.toString())
                        withContext(Dispatchers.Main) {
                            if (results.isNotEmpty()) {
                                rvResults.visibility = View.VISIBLE
                                rvResults.adapter = SearchAdapter(results) { item ->
                                    onItemSelected(item)
                                }
                            } else {
                                rvResults.visibility = View.GONE
                            }
                        }
                    } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                        android.util.Log.e("InvoiceActivity", "afterTextChanged failed", e)
                    }
                }
            }
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
        })
    }

    private fun onItemSelected(item: AdvancedSearchItem) {
        rvResults.visibility = View.GONE
        etSearch.setText("")

        // شروع انتخاب جدید: enrollment قبلی باطل می‌شود تا به پرداخت اشتباه وصل نشود
        selectedEnrollmentId = null
        if (item.type == "student") {
            fetchStudentClasses(item.id, item.title)
        } else {
            showClassStudentsDialog(item.title, item.students_in_class, item.id)
        }
    }

    private fun fetchStudentClasses(studentId: Int, studentName: String) {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val fullProfile = api.getFullStudentProfile(studentId)
                withContext(Dispatchers.Main) {
                    if (fullProfile.classes.isEmpty()) {
                        Toast.makeText(this@InvoiceActivity, getString(R.string.invoice_no_enrollment), Toast.LENGTH_SHORT).show()
                        return@withContext
                    }

                    val classNames = fullProfile.classes.toTypedArray()
                    AlertDialog.Builder(this@InvoiceActivity)
                        .setTitle(getString(R.string.invoice_pick_class, studentName))
                        .setItems(classNames) { _, which ->
                            val selectedClassStr = classNames[which]
                            // استخراج کد کلاس از داخل پرانتز
                            val courseCode = selectedClassStr.substringAfter("کد: ").substringBefore(")")
                            loadStudentClassStatus(studentId, studentName, selectedClassStr, courseCode)
                        }
                        .show()
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                android.util.Log.e("InvoiceActivity", "fetchStudentClasses failed", e)
            }
        }
    }

    private var selectedCourseId: Int = -1
    private var selectedEnrollmentId: Int? = null

    private fun loadStudentClassStatus(studentId: Int, studentName: String, className: String, courseCode: String) {
        selectedEnrollmentId = null // تا resolve جدید، پرداخت عمومی است
        selectedStudentId = studentId
        cardInfo.visibility = View.VISIBLE
        cardForm.visibility = View.VISIBLE

        tvStName.text = studentName
        tvStClass.text = className

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val status = api.getStudentClassStatus(studentId, null, courseCode)
                selectedCourseId = status.course_id ?: -1
                selectedEnrollmentId = status.enrollment_id

                withContext(Dispatchers.Main) {
                    val formattedTotal = String.format("%,d", status.total_amount)
                    val formattedPaidTeacher = String.format("%,d", status.paid_to_teacher)
                    val formattedPaidInstitute = String.format("%,d", status.paid_to_institute)

                    val signTeacher = if (status.due_to_teacher >= 0) "+" else "-"
                    val signInstitute = if (status.due_to_institute >= 0) "+" else "-"

                    val formattedDueTeacher = String.format("%,d", abs(status.due_to_teacher))
                    val formattedDueInstitute = String.format("%,d", abs(status.due_to_institute))

                    tvDebt.text = getString(R.string.invoice_total, formattedTotal)
                    tvUnpaid.text = getString(R.string.invoice_paid_teacher, formattedPaidTeacher)
                    tvStClass.text = getString(R.string.invoice_paid_institute, className, formattedPaidInstitute)

                    tvDebtTeacher.text = getString(R.string.invoice_due_teacher, signTeacher, formattedDueTeacher)
                    tvDebtInstitute.text = getString(R.string.invoice_due_institute, signInstitute, formattedDueInstitute)

                    // انتخاب مقدار پیش‌فرض روی بدهی
                    val defaultPay = if (status.due_to_teacher > 0) status.due_to_teacher else if (status.due_to_institute > 0) status.due_to_institute else 0L
                    etAmount.setText(if (defaultPay > 0) defaultPay.toString() else "")
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                android.util.Log.e("InvoiceActivity", "loadStudentClassStatus failed", e)
            }
        }
    }

    // لینک دقیق پرداخت به ثبت‌نام: enrollment فعال (شاگرد، کلاس) را از سرور می‌گیرد؛ در هر خطایی null می‌ماند (شارژ عمومی)
    private fun resolveEnrollmentIdAsync(studentId: Int, courseId: Int) {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val status = api.getStudentClassStatus(studentId, courseId, null)
                withContext(Dispatchers.Main) {
                    // فقط اگر هنوز همان شاگرد انتخاب است (جلوگیری از race با انتخاب جدید)
                    if (selectedStudentId == studentId) selectedEnrollmentId = status.enrollment_id
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e
                android.util.Log.e("InvoiceActivity", "resolveEnrollmentIdAsync failed", e)
            }
        }
    }

    private fun showClassStudentsDialog(className: String, students: List<SimpleStudentItem>?, courseId: Int) {
        if (students.isNullOrEmpty()) {
            Toast.makeText(this, getString(R.string.invoice_class_empty), Toast.LENGTH_SHORT).show()
            return
        }

        val names = students.map { student ->
            val total = student.totalDebt
            val teacherDebt = student.debtTeacher
            val instituteDebt = student.debtInstitute
            getString(R.string.invoice_student_row, student.name, String.format("%,d", total), String.format("%,d", teacherDebt), String.format("%,d", instituteDebt))
        }.toTypedArray()

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.invoice_pick_student, className))
            .setItems(names) { _, which ->
                val selected = students[which]
                fillStudentData(
                    selected.id,
                    selected.name,
                    className,
                    selected.totalDebt,
                    0,
                    selected.debtTeacher,
                    selected.debtInstitute,
                    courseId
                )
            }
            .show()
    }

    private fun fillStudentData(id: Int, name: String, className: String, debt: Long, unpaid: Int, debtTeacherVal: Long = 0, debtInstituteVal: Long = 0, courseId: Int = -1) {
        selectedEnrollmentId = null // تا resolve جدید، پرداخت عمومی است
        selectedStudentId = id
        cardInfo.visibility = View.VISIBLE
        cardForm.visibility = View.VISIBLE

        tvStName.text = name
        tvStClass.text = className
        tvDebt.text = getString(R.string.invoice_debt_total, String.format("%,d", debt))
        tvDebtTeacher.visibility = View.VISIBLE
        tvDebtTeacher.text = getString(R.string.invoice_debt_teacher, String.format("%,d", debtTeacherVal))
        tvDebtInstitute.visibility = View.VISIBLE
        tvDebtInstitute.text = getString(R.string.invoice_debt_institute, String.format("%,d", debtInstituteVal))
        tvUnpaid.text = getString(R.string.invoice_unpaid, unpaid)

        etAmount.setText(if (debt > 0) debt.toString() else "")
        val defaultDesc = if (unpaid > 0) getString(R.string.invoice_desc_settle, unpaid) else getString(R.string.invoice_desc_tuition)
        etDesc.setText(defaultDesc)
        // اگر کلاس مشخص است، enrollment دقیق را برای لینک پرداخت resolve می‌کنیم (fail-soft)
        if (courseId != -1) resolveEnrollmentIdAsync(id, courseId)
    }

    private fun applyPrefill(intent: Intent) {
        val prefillStudentId = intent.getIntExtra(EXTRA_PREFILL_STUDENT_ID, -1)
        if (prefillStudentId != -1) {
            val name = intent.getStringExtra(EXTRA_PREFILL_STUDENT_NAME) ?: ""
            val className = intent.getStringExtra(EXTRA_PREFILL_CLASS_NAME) ?: getString(R.string.common_unknown_class)
            val debt = intent.getLongExtra(EXTRA_PREFILL_DEBT, 0L)
            val debtTeacherVal = intent.getLongExtra(EXTRA_PREFILL_DEBT_TEACHER, 0L)
            val debtInstituteVal = intent.getLongExtra(EXTRA_PREFILL_DEBT_INSTITUTE, 0L)
            val unpaid = intent.getIntExtra(EXTRA_PREFILL_UNPAID_SESSIONS, 0)
            fillStudentData(prefillStudentId, name, className, debt, unpaid, debtTeacherVal, debtInstituteVal)
        }

        intent.getStringExtra(EXTRA_PREFILL_SEARCH_NAME)?.takeIf { it.isNotBlank() }?.let { query ->
            etSearch.post {
                etSearch.setText(query)
                etSearch.setSelection(query.length)
            }
        }
    }

    private fun setupFormLogic() {
        btnSubmit.setOnClickListener {
            val amountStr = etAmount.text.toString()
            if (selectedStudentId == -1 || amountStr.isEmpty()) {
                Toast.makeText(this, getString(R.string.invoice_amount_empty), Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // ✅ باگ 1 فیکس: هندل صریح rbCheque (عدم سقوط به else)
            val payMethod = when(rgPayment.checkedRadioButtonId) {
                R.id.rbCard -> "کارتخوان"
                R.id.rbCash -> "نقدی"
                R.id.rbCheque -> "کارت به کارت"
                else -> {
                    // fallback برای حالت‌های ناشناخته - لاگ و پیش‌فرض به کارت به کارت
                    android.util.Log.w("InvoiceActivity", "Unknown payMethod id ${rgPayment.checkedRadioButtonId}, fallback to کارت به کارت")
                    "کارت به کارت"
                }
            }

            // ✅ باگ 2 فیکس: هندل صریح rbWalletBoth -> targetWallet = "both"
            var targetWallet = "teacher"
            var amountTeacher: Long? = null
            var amountInstitute: Long? = null

            if (isAdmin) {
                targetWallet = when(rgWallet.checkedRadioButtonId) {
                    R.id.rbWalletInstitute -> "institute"
                    R.id.rbWalletTeacher -> "teacher"
                    R.id.rbWalletBoth -> "both"
                    else -> "teacher"
                }
            }

            // FIX: Bug 22 - reject malformed/negative/overflowing amounts before confirmation or network IO.
            val amount = InputValidation.nonNegativeAmount(amountStr)
            if (amount == null) {
                etAmount.error = getString(R.string.invoice_amount_invalid)
                return@setOnClickListener
            }
            val desc = etDesc.text.toString()

            // اگر both انتخاب شده، سهم آموزشگاه را هم بخوان
            if (targetWallet == "both") {
                val instituteStr = etAmountInstitute.text.toString()
                if (instituteStr.isEmpty()) {
                    Toast.makeText(this, getString(R.string.invoice_institute_missing), Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
                // FIX: Bug 22 - each explicit share is nonnegative; an empty/invalid share is not silently zero.
                amountInstitute = InputValidation.nonNegativeAmount(instituteStr)
                if (amountInstitute == null) {
                    etAmountInstitute.error = getString(R.string.invoice_institute_invalid)
                    return@setOnClickListener
                }
                amountTeacher = amount
            }

            // FIX: Bug 22 - the payment total, rather than every individual share, must be positive.
            val totalForDisplay = InputValidation.paymentTotal(amount, if (targetWallet == "both") amountInstitute ?: 0 else 0)
            if (totalForDisplay == null) {
                etAmount.error = getString(R.string.invoice_total_invalid)
                return@setOnClickListener
            }
            val walletDisplay = when(targetWallet) {
                "teacher" -> getString(R.string.invoice_wallet_teacher)
                "institute" -> getString(R.string.invoice_wallet_institute)
                "both" -> getString(R.string.invoice_wallet_both, String.format("%,d", amountTeacher ?: 0), String.format("%,d", amountInstitute ?: 0), String.format("%,d", totalForDisplay))
                else -> targetWallet
            }

            val confirmationMessage = """
                |${getString(R.string.invoice_confirm_amount, String.format("%,d", totalForDisplay), tvStName.text)}
                |
                |${getString(R.string.invoice_confirm_wallet, walletDisplay)}
                |${getString(R.string.invoice_confirm_paymethod, payMethod)}
            """.trimMargin()

            AlertDialog.Builder(this)
                .setTitle(getString(R.string.invoice_confirm_title))
                .setMessage(confirmationMessage)
                .setPositiveButton(getString(R.string.invoice_confirm_yes)) { _, _ ->
                    // FIX (audit-v2/idempotency): همان کلید برای همه‌ی retryها (نه تازه)؛ ولی اگر کاربر بعد از
                    // خطا فرم را عوض کرد (پرداخت تازه)، امضا عوض می‌شود و کلید تازه ساخته می‌شود — وگرنه replay
                    // اشتباهِ رسید قبلی یا گیرکردن روی 422 رخ می‌داد. چرخش صفحه کلید را می‌اندازد (رفتار قبلی).
                    val formSig = "$selectedStudentId|$amount|$targetWallet|$desc|$payMethod|$amountTeacher|$amountInstitute|$selectedEnrollmentId|$currentPersianDate"
                    val idemKey = if (pendingPaymentKey != null && pendingPaymentSig == formSig) pendingPaymentKey!! else UUID.randomUUID().toString().also { pendingPaymentKey = it; pendingPaymentSig = formSig }
                    sendData(FinanceSubmitData(
                        student_id = selectedStudentId,
                        amount = amount,
                        target_wallet = targetWallet,
                        description = desc,
                        payment_method = payMethod,
                        date = currentPersianDate,
                        amount_institute = amountInstitute,
                        amount_teacher = amountTeacher,
                        enrollment_id = selectedEnrollmentId,
                        idempotency_key = idemKey
                    ))
                }
                .setNegativeButton(getString(R.string.common_cancel), null)
                .show()
        }
    }

    private fun sendData(data: FinanceSubmitData) {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        // FIX: Show loading on the existing button, without changing the request.
        (btnSubmit as? GoldButton)?.setLoading(true)
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val res = api.submitPayment(data)
                withContext(Dispatchers.Main) {
                    // FIX: Restore the button on both success and failure.
                    (btnSubmit as? GoldButton)?.setLoading(false)
                    // FIX (audit-v2/idempotency): موفقیت (تازه یا replay) → کلید بازنشسته؛ پرداخت بعدی کلید تازه می‌گیرد. خطا کلید را نگه می‌دارد تا retry همان را بفرستد.
                    pendingPaymentKey = null
                    pendingPaymentSig = null
                    if (res.duplicate) Toast.makeText(this@InvoiceActivity, getString(R.string.invoice_duplicate), Toast.LENGTH_LONG).show()
                    // ابطال کش تراز و پروفایل دانش‌آموز به همراه لیست کلاس‌ها
                    CacheManager.clear(this@InvoiceActivity, "student_full_profile_${data.student_id}")
                    CacheManager.clearByPrefix(this@InvoiceActivity, "class_students_full")
                    CacheManager.clearByPrefix(this@InvoiceActivity, "today_summary_admin_")
                    
                    // بازخورد لمسی برای ثبت نهایی تراکنش موفقیت‌آمیز
                    window.decorView.performHapticFeedback(android.view.HapticFeedbackConstants.VIRTUAL_KEY)

                    loadAndShowReceipt(res.receipt_id.toString(), res.message)  // FIX H16: مسیر واحد سرور-محور (res مبلغ ندارد)
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    // FIX: Restore the button on both success and failure.
                    (btnSubmit as? GoldButton)?.setLoading(false)
                    // FIX (F-D4): پیام فارسی مشخص به‌جای e.message خام (الگوی LoginActivity).
                    val friendly = when {
                        e is HttpException && e.code() == 429 -> getString(R.string.invoice_err_too_many)
                        e is HttpException && e.code() >= 500 -> getString(R.string.invoice_err_server)
                        e is java.io.IOException -> getString(R.string.invoice_err_network)
                        else -> getString(R.string.invoice_submit_error, e.message)
                    }
                    Toast.makeText(this@InvoiceActivity, friendly, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    // FIX H16: loader واحد رسید — تنها مسیر ساخت دیالوگ چاپ (post-submit و REPRINT هر دو).
    // جزئیات از GET /finance/receipt/{id} می‌آید و در ویوها ست می‌شود؛ دیالوگ مودال است پس بین ست و نمایش، کاربر نمی‌تواند فیلد را لمس کند.
    private fun loadAndShowReceipt(receiptId: String, message: String, isModified: Boolean = false) {
        val txnId = receiptId.toLongOrNull()
        if (txnId == null || txnId <= 0) {
            Toast.makeText(this, getString(R.string.invoice_receipt_invalid), Toast.LENGTH_LONG).show()
            return
        }
        val retrofit = RetrofitClient.getInstance(this)
        val receiptApi = retrofit.create(ReceiptDetailsApi::class.java)
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val d = receiptApi.getReceiptDetails(txnId)
                withContext(Dispatchers.Main) {
                    tvStName.text = d.student_name ?: "-"
                    tvStClass.text = d.course_name ?: "-"
                    etAmount.setText((d.amount ?: 0).toString())
                    etDesc.setText(d.description ?: "-")
                    tvDate.text = d.date ?: "-"
                    showRemittanceSuccessDialog(receiptId, message, isModified)
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e
                withContext(Dispatchers.Main) {
                    val msg = if (e is HttpException && e.code() == 404)
                        getString(R.string.invoice_receipt_missing)
                    else
                        getString(R.string.invoice_receipt_error, e.message)
                    Toast.makeText(this@InvoiceActivity, msg, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun showRemittanceSuccessDialog(receiptId: String, message: String, isModified: Boolean = false) {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_remittance_success, null)

        val imgSuccessIcon = dialogView.findViewById<ImageView>(R.id.imgSuccessIcon)
        if (imgSuccessIcon != null) {
            imgSuccessIcon.alpha = 0f
            imgSuccessIcon.scaleX = 0f
            imgSuccessIcon.scaleY = 0f
            imgSuccessIcon.animate()
                .alpha(1f)
                .scaleX(1f)
                .scaleY(1f)
                .setDuration(AnimationConstants.ANIM_TRANSITION)
                .setInterpolator(android.view.animation.OvershootInterpolator())
                .start()
        }

        val dialog = AlertDialog.Builder(this)
            .setView(dialogView)
            .setCancelable(false)
            .create()

        val tvMessage = dialogView.findViewById<TextView>(R.id.tvSuccessMessage)
        tvMessage.text = getString(R.string.invoice_dialog_msg, message, receiptId)

        val btnPrint = dialogView.findViewById<Button>(R.id.btnPrintRemittance)
        btnPrint.setOnClickListener {
            val amountVal = etAmount.text.toString().toLongOrNull() ?: 0
            printReceiptClientSide(
                studentName = tvStName.text.toString(),
                className = tvStClass.text.toString(),
                amount = amountVal,
                date = tvDate.text.toString(),
                desc = etDesc.text.toString(),
                receiptId = receiptId,
                isModified = isModified
            )
        }

        val btnSavePdf = dialogView.findViewById<Button>(R.id.btnSaveAsPdf)
        btnSavePdf.setOnClickListener {
            val amountVal = etAmount.text.toString().toLongOrNull() ?: 0
            generatePdfClientSide(
                studentName = tvStName.text.toString(),
                className = tvStClass.text.toString(),
                amount = amountVal,
                date = tvDate.text.toString(),
                desc = etDesc.text.toString(),
                receiptId = receiptId,
                isModified = isModified
            )
        }

        val btnRegisterAgain = dialogView.findViewById<Button>(R.id.btnRegisterAgain)
        btnRegisterAgain.setOnClickListener {
            dialog.dismiss()
            cardInfo.visibility = View.GONE
            cardForm.visibility = View.GONE
            etSearch.setText("")
            selectedStudentId = -1
            selectedCourseId = -1
            selectedEnrollmentId = null
            etAmount.setText("")
            etDesc.setText("")
            etSearch.requestFocus()
        }

        val btnClose = dialogView.findViewById<Button>(R.id.btnClose)
        btnClose.setOnClickListener {
            dialog.dismiss()
            if (intent.getStringExtra("MODE") == "REPRINT") {
                finish()
            } else {
                cardInfo.visibility = View.GONE
                cardForm.visibility = View.GONE
                etSearch.setText("")
                selectedStudentId = -1
                selectedEnrollmentId = null
                etAmount.setText("")
                etDesc.setText("")
            }
        }

        dialog.show()
    }

    private fun printReceiptClientSide(studentName: String, className: String, amount: Long, date: String, desc: String, receiptId: String, isModified: Boolean = false) {
        val retrofit = RetrofitClient.getInstance(this)
        val settingsApi = retrofit.create(InstituteSettingsApi::class.java)

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.Main) {
            try {
                val settings = withContext(Dispatchers.IO) { settingsApi.getSettings() }
                
                val instName = settings.name
                val instAddress = settings.address
                val instPhone = settings.phone
                val instFooter = settings.footer_text ?: getString(R.string.invoice_thanks_payment)

                val webView = WebView(this@InvoiceActivity)
                val htmlContent = """
                    <html>
                    <head>
                        <style>
                            body { width: 80mm; font-family: Tahoma, sans-serif; direction: rtl; padding: 10px; margin: 0; font-size: 11px; }
                            .header { text-align: center; border-bottom: 1px dashed #333; padding-bottom: 8px; margin-bottom: 15px; }
                            .title { font-size: 15px; font-weight: bold; }
                            .row { margin-bottom: 5px; font-size: 11px; }
                            .label { font-weight: bold; }
                            .footer { margin-top: 15px; text-align: center; font-size: 9px; color: #555; border-top: 1px dashed #333; padding-top: 6px; }
                            .box { padding: 5px; }
                            .stamp { color: #D32F2F; font-size: 16px; font-weight: bold; border: 2px solid #D32F2F; padding: 4px; display: inline-block; margin-top: 6px; }
                        </style>
                    </head>
                    <body>
                        <div class="header">
                            <div class="title">$instName</div>
                            <div style="font-size: 9px; margin-top: 4px;">${getString(R.string.invoice_html_address, instAddress)}</div>
                            <div style="font-size: 9px; margin-top: 2px;">${getString(R.string.invoice_html_phone, instPhone)}</div>
                            <div style="font-size: 11px; font-weight: bold; margin-top: 8px;">${getString(R.string.invoice_html_title)}</div>
                            ${if (isModified) getString(R.string.invoice_html_stamp) else ""}
                        </div>

                        <div class="box">
                            <div class="row"><span class="label">${getString(R.string.invoice_lbl_student)}</span> $studentName</div>
                            <div class="row"><span class="label">${getString(R.string.invoice_lbl_class)}</span> $className</div>
                            <div class="row"><span class="label">${getString(R.string.invoice_lbl_amount)}</span> ${String.format("%,d", amount)} ${getString(R.string.attendance_toman)}</div>
                            <div class="row"><span class="label">${getString(R.string.invoice_lbl_date)}</span> $date</div>
                            <div class="row"><span class="label">${getString(R.string.invoice_lbl_desc)}</span> $desc</div>
                            <div class="row"><span class="label">${getString(R.string.invoice_lbl_receipt)}</span> $receiptId</div>
                        </div>

                        <div class="footer">
                            $instFooter
                        </div>
                    </body>
                    </html>
                """.trimIndent()

                webView.loadDataWithBaseURL(null, htmlContent, "text/html", "UTF-8", null)

                val printManager = getSystemService(Context.PRINT_SERVICE) as PrintManager
                val printAdapter = webView.createPrintDocumentAdapter("Receipt_$receiptId")

                val printAttributes = PrintAttributes.Builder()
                    .setMediaSize(PrintAttributes.MediaSize.ISO_A5)
                    .build()

                printManager.print("Kharazmi_Receipt_$receiptId", printAdapter, printAttributes)
                
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                android.util.Log.e("InvoiceActivity", "printReceiptClientSide failed", e)
            }
        }
    }

    private fun generatePdfClientSide(studentName: String, className: String, amount: Long, date: String, desc: String, receiptId: String, isModified: Boolean = false) {
        val retrofit = RetrofitClient.getInstance(this)
        val settingsApi = retrofit.create(InstituteSettingsApi::class.java)

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.Main) {
            try {
                val settings = withContext(Dispatchers.IO) { settingsApi.getSettings() }
                
                val instName = settings.name
                val instAddress = settings.address
                val instPhone = settings.phone
                val instFooter = settings.footer_text ?: getString(R.string.common_thanks)
                
                val pdfDocument = PdfDocument()
                // A7 size (280x420 pt) ideal for small receipt/thermal printers
                val pageInfo = PdfDocument.PageInfo.Builder(280, 420, 1).create()
                val page = pdfDocument.startPage(pageInfo)
                val canvas = page.canvas
                val paint = Paint()

                canvas.drawColor(Color.WHITE)

                paint.color = Color.BLACK
                paint.textSize = 14f
                paint.textAlign = Paint.Align.CENTER
                canvas.drawText(instName, 280f / 2, 30f, paint)

                paint.textSize = 9f
                canvas.drawText(getString(R.string.invoice_pdf_address, instAddress), 280f / 2, 48f, paint)
                canvas.drawText(getString(R.string.invoice_pdf_phone, instPhone), 280f / 2, 62f, paint)

                if (isModified) {
                    paint.color = Color.RED
                    paint.textSize = 12f
                    canvas.drawText(getString(R.string.invoice_pdf_modified), 280f / 2, 78f, paint)
                    paint.color = Color.BLACK
                }

                canvas.drawLine(10f, 85f, 270f, 85f, paint)

                paint.textSize = 11f
                paint.textAlign = Paint.Align.RIGHT
                val startX = 260f
                var startY = 110f
                val lineHeight = 24f

                canvas.drawText(getString(R.string.invoice_pdf_student, studentName), startX, startY, paint)
                startY += lineHeight
                canvas.drawText(getString(R.string.invoice_pdf_class, className), startX, startY, paint)
                startY += lineHeight
                canvas.drawText(getString(R.string.invoice_pdf_amount, String.format("%,d", amount)), startX, startY, paint)
                startY += lineHeight
                canvas.drawText(getString(R.string.invoice_pdf_date, date), startX, startY, paint)
                startY += lineHeight
                canvas.drawText(getString(R.string.invoice_pdf_desc, desc), startX, startY, paint)
                startY += lineHeight
                canvas.drawText(getString(R.string.invoice_pdf_receipt, receiptId), startX, startY, paint)

                canvas.drawLine(10f, 320f, 270f, 320f, paint)

                paint.textSize = 9f
                paint.textAlign = Paint.Align.CENTER
                canvas.drawText(instFooter, 280f / 2, 340f, paint)

                pdfDocument.finishPage(page)

                val fileName = "Receipt_$receiptId.pdf"
                val file = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), fileName)

                try {
                    pdfDocument.writeTo(FileOutputStream(file))
                    Toast.makeText(this@InvoiceActivity, getString(R.string.invoice_pdf_saved, fileName), Toast.LENGTH_LONG).show()
                } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                    Toast.makeText(this@InvoiceActivity, getString(R.string.invoice_pdf_error, e.message), Toast.LENGTH_LONG).show()
                } finally {
                    pdfDocument.close()
                }
                
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                android.util.Log.e("InvoiceActivity", "generatePdfClientSide failed", e)
            }
        }
    }

    private fun getSimplePersianDate(): String {
        // FIX H3-B2: real Gregorian→Jalali conversion via JalaliUtils (was year-621 approximation).
        return JalaliUtils.todayJalaliString()
    }

    companion object {
        const val EXTRA_PREFILL_STUDENT_ID = "EXTRA_PREFILL_STUDENT_ID"
        const val EXTRA_PREFILL_STUDENT_NAME = "EXTRA_PREFILL_STUDENT_NAME"
        const val EXTRA_PREFILL_CLASS_NAME = "EXTRA_PREFILL_CLASS_NAME"
        const val EXTRA_PREFILL_DEBT = "EXTRA_PREFILL_DEBT"
        const val EXTRA_PREFILL_DEBT_TEACHER = "EXTRA_PREFILL_DEBT_TEACHER"
        const val EXTRA_PREFILL_DEBT_INSTITUTE = "EXTRA_PREFILL_DEBT_INSTITUTE"
        const val EXTRA_PREFILL_UNPAID_SESSIONS = "EXTRA_PREFILL_UNPAID_SESSIONS"
        const val EXTRA_PREFILL_SEARCH_NAME = "EXTRA_PREFILL_SEARCH_NAME"
        const val EXTRA_IS_ADMIN = "IS_ADMIN"
    }
}

class SearchAdapter(
    private val list: List<AdvancedSearchItem>,
    private val onClick: (AdvancedSearchItem) -> Unit
) : RecyclerView.Adapter<SearchAdapter.VH>() {

    class VH(v: View) : RecyclerView.ViewHolder(v) {
        val title: TextView = v.findViewById(android.R.id.text1)
        val subtitle: TextView = v.findViewById(android.R.id.text2)
        init {
            subtitle.textSize = 12f
            subtitle.setTextColor(android.graphics.Color.GRAY)
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val v = LayoutInflater.from(parent.context).inflate(android.R.layout.simple_list_item_2, parent, false)
        return VH(v)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = list[position]
        val icon = if (item.type == "class") getString(R.string.invoice_icon_class) else getString(R.string.invoice_icon_person)
        holder.title.text = "$icon ${item.title}"

        // نمایش اطلاعات اضافی
        val extraInfo = if (item.total_debt != null && item.total_debt > 0)
            getString(R.string.invoice_extra_debt, String.format("%,d", item.total_debt))
        else
            item.info

        holder.subtitle.text = "${item.subtitle} | $extraInfo"
        holder.itemView.setOnClickListener { onClick(item) }
    }

    override fun getItemCount() = list.size
}
