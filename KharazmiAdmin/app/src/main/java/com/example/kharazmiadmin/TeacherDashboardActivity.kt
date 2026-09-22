package com.example.kharazmiadmin

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.card.MaterialCardView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.http.GET
import retrofit2.http.Path

// 1. Updated Data Model
data class TeacherClassItem(
    val id: Int,
    val title: String? = "",
    val code: String? = "",
    val grade_level: String? = "",
    val is_admin_approved: Boolean = false,
    val is_suspended: Boolean = false,
    val students_preview: List<String>? = null, // New field added
    val bg_color: String? = "#FFFFFF"
)

interface TeacherPanelApi {
    @GET("teachers/{id}/classes")
    suspend fun getMyClasses(@Path("id") id: Int): List<TeacherClassItem>

    @GET("teachers/{id}/incomplete_classes")
    suspend fun getTeacherIncompleteClasses(@Path("id") id: Int): List<TeacherClassItem>
}

interface TeacherMeApi {
    @GET("auth/me")
    suspend fun getMe(): MeResponse
}

class TeacherDashboardActivity : BaseActivity() {

    private var teacherId: Int = -1
    private lateinit var api: TeacherPanelApi
    private lateinit var rv: RecyclerView
    private var todaySummaryLoading = false
    // FIX (گروه۳/آیتم۱۲): پرچم نقش برای آداپتر بنر کلاس‌ها — همان USER_SUB_ROLE موجود.
    private var isAdminUser = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_teacher_dashboard)

        teacherId = intent.getIntExtra("TEACHER_ID", -1)
        val teacherName = intent.getStringExtra("TEACHER_NAME") ?: getString(R.string.tdash_colleague)

        findViewById<TextView>(R.id.tvWelcome).text = getString(R.string.tdash_welcome, teacherName)
        fetchPermissionsAndSyncUI()

        // 🎥 کلاس زنده
        setupLiveCard()

        // خروج
        findViewById<ImageView>(R.id.btnLogout).setOnClickListener { finish() }

        // رفرش دستی
        findViewById<ImageView>(R.id.btnRefresh).setOnClickListener {
            fetchClasses()
            fetchTeacherTodaySummary(forceRefresh = true)
            Toast.makeText(this, getString(R.string.tdash_updated), Toast.LENGTH_SHORT).show()
        }

        // 1. دکمه ثبت نام دانش‌آموز
        findViewById<MaterialCardView>(R.id.cardRegisterStudent).setOnClickListener {
            startActivity(Intent(this, StudentRegisterActivity::class.java))
        }

        // 2. دکمه ثبت کلاس جدید
        findViewById<MaterialCardView>(R.id.cardRegisterClass).setOnClickListener {
            val intent = Intent(this, AddClassActivity::class.java)
            intent.putExtra("AUTO_TEACHER_ID", teacherId)
            intent.putExtra("AUTO_TEACHER_NAME", teacherName)
            startActivity(intent)
        }

        // 3. دکمه حضور و غیاب عمومی
        findViewById<MaterialCardView>(R.id.cardAttendance).setOnClickListener {
            val options = arrayOf(getString(R.string.tdash_opt_new), getString(R.string.tdash_opt_edit))
            AlertDialog.Builder(this)
                .setTitle(getString(R.string.tdash_att_title))
                .setItems(options) { _, which ->
                    when (which) {
                        0 -> Toast.makeText(this, getString(R.string.tdash_pick_class), Toast.LENGTH_LONG).show()
                        1 -> showEditSessionDialog()
                    }
                }
                .show()
        }

        // ============================================================
        // 4. دکمه ثبت حواله / شهریه (لینک به InvoiceActivity)
        // FIX (گروه۳/آیتم۱۱): این صفحه پنل **معلم** است (LoginActivity فقط با
        // `response.role == "teacher"` اینجا می‌آید و EditStudentActivity.returnToDashboard
        // هم فقط برای `userRole == "teacher"`) و ثبت حواله/وصول پول کار ادمین/منشی است ⇒
        // کارت برای غیر ادمین پنهان می‌شود و listener هم فقط در شاخهٔ ادمین ثبت می‌گردد
        // (دکمهٔ پنهانِ کلیک‌پذیر = راه فرار). همان چک نقش موجود پروژه:
        // `UserCreds` → `USER_SUB_ROLE` (مثل ClassDetailActivity:334) — الگوی جدید نساختیم.
        // ============================================================
        val credsPrefs = getSharedPreferences("UserCreds", Context.MODE_PRIVATE)
        val subRole = credsPrefs.getString("USER_SUB_ROLE", "admin") ?: "admin"
        isAdminUser = subRole == "admin"
        val cardFastInvoice = findViewById<MaterialCardView>(R.id.cardFastInvoice)
        if (subRole != "admin") {
            cardFastInvoice.visibility = android.view.View.GONE
        } else {
            cardFastInvoice.setOnClickListener {
                val intent = Intent(this, InvoiceActivity::class.java)
                startActivity(intent)
            }
        }
        // ============================================================

        // 5. دکمه کلاس‌های ناقص
        findViewById<MaterialCardView>(R.id.cardIncompleteClasses).setOnClickListener {
            showIncompleteClassesDialog()
        }

        // 6. دکمه گزارشات مالی مربی
        findViewById<MaterialCardView>(R.id.cardReports).setOnClickListener {
            val intent = Intent(this, ReportActivity::class.java)
            startActivity(intent)
        }

        // تنظیم لیست
        rv = findViewById(R.id.rvMyClasses)
        rv.layoutManager = LinearLayoutManager(this)

        val retrofit = RetrofitClient.getInstance(this)
        api = retrofit.create(TeacherPanelApi::class.java)

        fetchClasses()
    }

    override fun onResume() {
        super.onResume()
        if (teacherId != -1) {
            fetchClasses()
        }
        setupLiveCard()
        fetchTeacherTodaySummary()
    }

    private fun fetchTeacherTodaySummary(forceRefresh: Boolean = false) {
        if (teacherId == -1 || todaySummaryLoading) return
        todaySummaryLoading = true

        val todayApi = RetrofitClient.getInstance(this).create(TodaySummaryApi::class.java)
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val summary = TodaySummaryShortCache.getOrFetch(
                    context = this@TeacherDashboardActivity,
                    key = "today_summary_teacher_$teacherId",
                    modelClass = TeacherTodaySummary::class.java,
                    forceRefresh = forceRefresh
                ) {
                    todayApi.getTeacherTodaySummary(teacherId)
                }
                withContext(Dispatchers.Main) {
                    renderTeacherTodaySummary(summary)
                }
            } catch (ignoredError: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (ignoredError is kotlinx.coroutines.CancellationException) throw ignoredError;
                // کش منقضی‌شده‌ی داده‌های زنده عمداً نمایش داده نمی‌شود.
            } finally {
                withContext(Dispatchers.Main) {
                    todaySummaryLoading = false
                }
            }
        }
    }

    private fun renderTeacherTodaySummary(summary: TeacherTodaySummary) {
        findViewById<TextView>(R.id.tvTeacherWeekSessions).text =
            summary.weekSummary.sessionsTaught.toString()
        findViewById<TextView>(R.id.tvTeacherWeekUnsettled).text =
            String.format(java.util.Locale.US, "%,d", summary.weekSummary.unsettledAmount)

        val statusCard = findViewById<MaterialCardView>(R.id.cardTeacherTodayStatus)
        val statusText = findViewById<TextView>(R.id.tvTeacherTodayStatus)
        val actionButton = findViewById<com.google.android.material.button.MaterialButton>(R.id.btnTeacherTodayAction)
        val live = summary.liveClass
        val next = summary.nextClass

        when {
            live != null -> {
                statusCard.visibility = android.view.View.VISIBLE
                statusCard.setCardBackgroundColor(
                    androidx.core.content.ContextCompat.getColor(this, R.color.gaj_error_light)
                )
                statusCard.strokeColor =
                    androidx.core.content.ContextCompat.getColor(this, R.color.gaj_error)
                statusText.setTextColor(
                    androidx.core.content.ContextCompat.getColor(this, R.color.gaj_error)
                )
                statusText.text = getString(R.string.tdash_live_now, live.className, live.elapsedMinutes)
                actionButton.visibility = android.view.View.VISIBLE
                actionButton.text = getString(R.string.tdash_go_attendance)
                actionButton.setOnClickListener { openTodayLiveClass(live) }
            }

            next != null && next.minutesUntil <= 120 -> {
                statusCard.visibility = android.view.View.VISIBLE
                statusCard.setCardBackgroundColor(
                    androidx.core.content.ContextCompat.getColor(this, R.color.gaj_warning_light)
                )
                statusCard.strokeColor =
                    androidx.core.content.ContextCompat.getColor(this, R.color.gaj_warning)
                statusText.setTextColor(
                    androidx.core.content.ContextCompat.getColor(this, R.color.gaj_warning)
                )
                statusText.text = getString(R.string.tdash_next, next.className, next.scheduledTime)
                actionButton.visibility = android.view.View.VISIBLE
                actionButton.text = getString(R.string.tdash_start_class)
                actionButton.setOnClickListener { startUpcomingLiveClass(next) }
            }

            else -> {
                statusCard.visibility = android.view.View.GONE
                actionButton.setOnClickListener(null)
            }
        }
    }

    private fun openTodayLiveClass(live: TeacherTodayLiveClass) {
        val intent = Intent(this, LiveClassActivity::class.java)
        intent.putExtra("TARGET_COURSE_ID", live.courseId)
        intent.putExtra("TARGET_COURSE_NAME", live.className)
        intent.putExtra("LIVE_SESSION_ID", live.liveSessionId)
        intent.putExtra("STARTED_AT_TS", live.startedAtTs ?: System.currentTimeMillis() / 1000)
        startActivity(intent)
    }

    private fun startUpcomingLiveClass(next: TeacherTodayNextClass) {
        val liveApi = RetrofitClient.getInstance(this).create(LiveApi::class.java)
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val response = liveApi.startLive(next.courseId)
                CacheManager.clear(this@TeacherDashboardActivity, "today_summary_teacher_$teacherId")
                withContext(Dispatchers.Main) {
                    val intent = Intent(this@TeacherDashboardActivity, LiveClassActivity::class.java)
                    intent.putExtra("TARGET_COURSE_ID", next.courseId)
                    intent.putExtra("TARGET_COURSE_NAME", next.className)
                    intent.putExtra("LIVE_SESSION_ID", response.liveSessionId)
                    intent.putExtra(
                        "STARTED_AT_TS",
                        response.startedAtTs ?: System.currentTimeMillis() / 1000
                    )
                    startActivity(intent)
                }
            } catch (ignoredError: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (ignoredError is kotlinx.coroutines.CancellationException) throw ignoredError;
                withContext(Dispatchers.Main) {
                    Toast.makeText(
                        this@TeacherDashboardActivity,
                        getString(R.string.tdash_start_failed),
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
    }

    // 🎥 کارت «کلاس زنده» معلم: شروع/رزومه جلسه
    private fun setupLiveCard() {
        val liveApi = RetrofitClient.getInstance(this).create(LiveApi::class.java)
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            val cur = try { liveApi.getCurrentLive() } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e; null }
            withContext(Dispatchers.Main) {
                val tvTitle = findViewById<TextView>(R.id.tvLiveButtonTitle)
                val tvSub = findViewById<TextView>(R.id.tvLiveButtonSub)
                val card = findViewById<MaterialCardView>(R.id.cardStartLive)

                card.setOnClickListener {
                    if (cur != null) {
                        openLiveClass(cur)
                    } else {
                        chooseClassToStart(liveApi)
                    }
                }

                if (cur != null) {
                    tvTitle.text = getString(R.string.tdash_banner_live, cur.classTitle.ifEmpty { getString(R.string.tdash_class_fallback) })
                    tvSub.text = getString(R.string.tdash_banner_back)
                } else {
                    tvTitle.text = getString(R.string.tdash_banner_start)
                    tvSub.text = getString(R.string.tdash_banner_sub)
                }
            }
        }
    }

    private fun openLiveClass(cur: LiveCurrentResponse) {
        val intent = Intent(this, LiveClassActivity::class.java)
        intent.putExtra("TARGET_COURSE_ID", cur.courseId)
        intent.putExtra("TARGET_COURSE_NAME", cur.classTitle)
        intent.putExtra("LIVE_SESSION_ID", cur.liveSessionId)
        intent.putExtra("STARTED_AT_TS", cur.startedAtTs ?: System.currentTimeMillis() / 1000)
        startActivity(intent)
    }

    private fun chooseClassToStart(liveApi: LiveApi) {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val classes = api.getMyClasses(teacherId)
                val eligible = classes.filter { it.is_admin_approved && !it.is_suspended }
                withContext(Dispatchers.Main) {
                    if (eligible.isEmpty()) {
                        Toast.makeText(this@TeacherDashboardActivity, getString(R.string.tdash_no_class), Toast.LENGTH_LONG).show()
                        return@withContext
                    }
                    val names = eligible.map { "${it.title} (${it.code})" }.toTypedArray()
                    AlertDialog.Builder(this@TeacherDashboardActivity)
                        .setTitle(getString(R.string.tdash_pick_live))
                        .setItems(names) { _, which ->
                            val selected = eligible[which]
                            startLive(liveApi, selected)
                        }
                        .show()
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@TeacherDashboardActivity, getString(R.string.tdash_class_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun startLive(liveApi: LiveApi, cls: TeacherClassItem) {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val res = liveApi.startLive(cls.id)
                CacheManager.clear(this@TeacherDashboardActivity, "today_summary_teacher_$teacherId")
                withContext(Dispatchers.Main) {
                    val intent = Intent(this@TeacherDashboardActivity, LiveClassActivity::class.java)
                    intent.putExtra("TARGET_COURSE_ID", cls.id)
                    intent.putExtra("TARGET_COURSE_NAME", cls.title ?: "")
                    intent.putExtra("LIVE_SESSION_ID", res.liveSessionId)
                    intent.putExtra("STARTED_AT_TS", res.startedAtTs ?: System.currentTimeMillis() / 1000)
                    startActivity(intent)
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                // اگر کلاس از قبل زنده بود، به سمت جلسه‌ی موجود برویم
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@TeacherDashboardActivity, getString(R.string.tdash_already_live), Toast.LENGTH_SHORT).show()
                }
                try {
                    val cur = liveApi.getCurrentLive()
                    if (cur != null) {
                        CacheManager.clear(this@TeacherDashboardActivity, "today_summary_teacher_$teacherId")
                        withContext(Dispatchers.Main) { openLiveClass(cur) }
                    }
                } catch (e2: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e2 is kotlinx.coroutines.CancellationException) throw e2; }
            }
        }
    }

    private fun showIncompleteClassesDialog() {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val list = api.getTeacherIncompleteClasses(teacherId)
                withContext(Dispatchers.Main) {
                    if (list.isEmpty()) {
                        Toast.makeText(this@TeacherDashboardActivity, getString(R.string.tdash_no_partial), Toast.LENGTH_SHORT).show()
                        return@withContext
                    }

                    val names = list.map { "${it.title} (${it.code})" }.toTypedArray()
                    AlertDialog.Builder(this@TeacherDashboardActivity)
                        .setTitle(getString(R.string.tdash_partial_title))
                        .setItems(names) { _, which ->
                            val selected = list[which]
                            val intent = Intent(this@TeacherDashboardActivity, ClassSetupActivity::class.java)
                            intent.putExtra("CLASS_ID", selected.id)
                            intent.putExtra("CLASS_NAME", selected.title)
                            startActivity(intent)
                        }
                        .setPositiveButton(getString(R.string.btn_dismiss), null)
                        .show()
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@TeacherDashboardActivity, getString(R.string.tdash_partial_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun showEditSessionDialog() {
        val view = LayoutInflater.from(this).inflate(R.layout.dialog_ip_input, null)
        val etInput = view.findViewById<android.widget.EditText>(R.id.etIpInput)
        etInput.hint = getString(R.string.main_session_code_hint)
        etInput.inputType = android.text.InputType.TYPE_CLASS_NUMBER

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.main_edit_session_title))
            .setView(view)
            .setPositiveButton(getString(R.string.main_edit_session_go)) { _, _ ->
                val codeStr = etInput.text.toString().trim()
                val code = codeStr.toIntOrNull()
                if (code != null) {
                    val intent = Intent(this, AttendanceActivity::class.java).apply {
                        putExtra("MODE", "EDIT_SESSION")
                        putExtra("TARGET_SESSION_CODE", code)
                    }
                    startActivity(intent)
                } else {
                    Toast.makeText(this, getString(R.string.main_session_invalid), Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton(getString(R.string.common_cancel), null)
            .show()
    }

    private fun fetchClasses() {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val list = api.getMyClasses(teacherId)
                withContext(Dispatchers.Main) {
                    if (list.isEmpty()) {
                        // لیست خالی
                    }
                    rv.adapter = TeacherClassAdapter(list, isAdminUser = isAdminUser) { selectedClass ->
                        if (selectedClass.is_suspended) {
                            Toast.makeText(this@TeacherDashboardActivity, getString(R.string.common_class_activate), Toast.LENGTH_LONG).show()
                        } else if (selectedClass.is_admin_approved) {
                            val intent = Intent(this@TeacherDashboardActivity, ClassDetailActivity::class.java)
                            intent.putExtra("CLASS_ID", selectedClass.id)
                            intent.putExtra("CLASS_NAME", selectedClass.title)
                            intent.putExtra("IS_SUSPENDED", selectedClass.is_suspended)
                            startActivity(intent)
                        } else {
                            val intent = Intent(this@TeacherDashboardActivity, ClassSetupActivity::class.java)
                            intent.putExtra("CLASS_ID", selectedClass.id)
                            intent.putExtra("CLASS_NAME", selectedClass.title)
                            intent.putExtra("IS_SUSPENDED", selectedClass.is_suspended)
                            startActivity(intent)
                        }
                    }
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                android.util.Log.e("TeacherDashboardActivity", "fetchClasses failed", e)
            }
        }
    }

    private fun fetchPermissionsAndSyncUI() {
        val retrofit = RetrofitClient.getInstance(this)
        val apiMe = retrofit.create(TeacherMeApi::class.java)
        
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val me = apiMe.getMe()
                val prefs = getSharedPreferences("UserCreds", Context.MODE_PRIVATE)
                prefs.edit().putStringSet("USER_PERMISSIONS", me.permissions.toSet()).apply()
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                android.util.Log.e("TeacherDashboardActivity", "fetchPermissionsAndSyncUI failed", e)
            }
        }
    }
}

// 2. Updated Adapter Logic
class TeacherClassAdapter(
    private val list: List<TeacherClassItem>,
    // FIX (گروه۳/آیتم۱۲): پرچم نقش از Activity می‌آید تا دکمه‌های مدیریتیِ بنر کلاس
    // برای معلم پنهان شود (layout مشترک با ClassManagementActivity دست‌نخورده می‌ماند).
    // نکته: عمداً **قبل از** onClick آمده تا lambda انتهاییِ محل ساخت همان onClick بماند.
    private val isAdminUser: Boolean = false,
    private val onClick: (TeacherClassItem) -> Unit
) : RecyclerView.Adapter<TeacherClassAdapter.VH>() {

    class VH(v: android.view.View) : RecyclerView.ViewHolder(v) {
        val title: TextView = v.findViewById(R.id.tvClassTitle)
        val code: TextView = v.findViewById(R.id.tvClassCode)
        val sub: TextView = v.findViewById(R.id.tvTeacherName)
        val llStudentPreview: LinearLayout = v.findViewById(R.id.ll_student_preview) // Added View Binding
        // FIX (گروه۳/آیتم۱۲): این دو در layout پیش‌فرض نمایان‌اند و آداپتر معلم قبلاً
        // هرگز به آن‌ها دست نمی‌زد ⇒ دو دکمهٔ نمایانِ بی‌عملکرد در پنل معلم.
        val btnSuspend: android.view.View = v.findViewById(R.id.btnSuspend)
        val btnRegisterInvoice: android.view.View = v.findViewById(R.id.btnRegisterInvoice)
    }

    override fun onCreateViewHolder(parent: android.view.ViewGroup, viewType: Int): VH {
        val v = android.view.LayoutInflater.from(parent.context).inflate(R.layout.item_class_row, parent, false)
        return VH(v)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = list[position]
        holder.title.text = item.title
        holder.code.text = holder.itemView.context.getString(R.string.tdash_code_row, item.code)

        // اعمال رنگ پس‌زمینه کارت کلاس بر اساس bg_color ثبت شده
        if (!item.bg_color.isNullOrEmpty()) {
            try {
                (holder.itemView as? com.google.android.material.card.MaterialCardView)?.setCardBackgroundColor(
                    android.graphics.Color.parseColor(item.bg_color)
                )
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                // رنگ نامعتبر رد می‌شود
            }
        }

        if (item.is_suspended) {
            holder.sub.text = holder.itemView.context.getString(R.string.tdash_suspended)
            holder.sub.setTextColor(android.graphics.Color.parseColor("#D32F2F"))
            holder.itemView.alpha = 0.5f
        } else if (item.is_admin_approved) {
            holder.sub.text = holder.itemView.context.getString(R.string.tdash_active)
            holder.sub.setTextColor(android.graphics.Color.parseColor("#388E3C"))
            holder.itemView.alpha = 1.0f
        } else {
            holder.sub.text = holder.itemView.context.getString(R.string.tdash_pending)
            holder.sub.setTextColor(android.graphics.Color.parseColor("#F57C00"))
            holder.itemView.alpha = 1.0f
        }

        // FIX (گروه۳/آیتم۱۲): تعلیق و ثبت حواله از اختیارات ادمین/منشی‌اند؛ در پنل معلم
        // پنهان می‌شوند (listener هم سمت ادمینِ ClassManagementActivity می‌ماند).
        holder.btnSuspend.visibility =
            if (isAdminUser) android.view.View.VISIBLE else android.view.View.GONE
        holder.btnRegisterInvoice.visibility =
            if (isAdminUser) android.view.View.VISIBLE else android.view.View.GONE

        // --- Student Preview Logic ---
        holder.llStudentPreview.removeAllViews()

        if (!item.students_preview.isNullOrEmpty()) {
            item.students_preview.forEach { name ->
                val tv = TextView(holder.itemView.context)
                tv.text = holder.itemView.context.getString(R.string.common_bullet_row, name)
                tv.textSize = 12f
                tv.setTextColor(android.graphics.Color.parseColor("#555555")) // Gray color
                tv.setPadding(0, 4, 0, 4)
                holder.llStudentPreview.addView(tv)
            }
        } else {
            val tv = TextView(holder.itemView.context)
            tv.text = holder.itemView.context.getString(R.string.tdash_no_students)
            tv.textSize = 10f
            tv.setTextColor(android.graphics.Color.GRAY)
            holder.llStudentPreview.addView(tv)
        }
        // -----------------------------

        holder.itemView.setOnClickListener { onClick(item) }
    }

    override fun getItemCount() = list.size
}
