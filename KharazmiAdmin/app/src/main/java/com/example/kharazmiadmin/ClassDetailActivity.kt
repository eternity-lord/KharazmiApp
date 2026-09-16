package com.example.kharazmiadmin

import android.widget.Toast

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.TextView
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.tabs.TabLayout
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.POST
import retrofit2.http.Query
import retrofit2.http.DELETE
import retrofit2.http.PUT
import retrofit2.http.Body
import androidx.appcompat.app.AlertDialog

// مدل‌های داده منطبق با سرور
data class FullClassReport(
    val info: ClassReportInfo,
    val students: List<ClassStudentData>,
    val sessions: List<ClassSessionHistory>
)
data class ClassReportInfo(
    val title: String, val code: String, val teacher_name: String,
    val session_count: Int, val total_students: Int,
    val total_revenue: Long, val total_debt: Long
)
data class ClassStudentData(val name: String, val mobile: String, val paid: Long, val debt: Long)
data class ClassSessionHistory(val date: String, val present_count: Int, val absent_count: Int)

// مدل‌های جدید برای تاریخچه حضور و غیاب دانش‌آموز
data class StudentAttendanceHistoryRequest(val student_id: Int, val course_id: Int)
data class StudentAttendanceHistoryResponse(
    val student_name: String,
    val course_title: String,
    val course_code: String,
    val total_sessions: Int,
    val present_count: Int,
    val absent_count: Int,
    val attendance_rate: Double,
    val attendance_history: List<AttendanceHistoryItem>
)
data class AttendanceHistoryItem(
    val session_id: Int,
    val date: String,
    val status: String,
    val session_cost: Long,
    val attendee_count: Int
)

// مدل برای لیست کامل دانش‌آموزان کلاس
data class ClassStudentsFullResponse(
    val course_info: CourseDetailInfo,
    val students: List<StudentFullItem>
)
data class CourseDetailInfo(
    val id: Int,
    val title: String,
    val code: String,
    val teacher_id: Int,
    val is_suspended: Boolean
)
data class StudentFullItem(
    val student_id: Int,
    val student_name: String,
    val national_code: String,
    val mobile: String,
    val total_tuition: Long,
    val paid: Long,
    val debt: Long,
    val debt_teacher: Long,
    val debt_institute: Long,
    val wallet_teacher: Long? = 0,
    val wallet_institute: Long? = 0,
    val student_code: Int? = null,
    val present_count: Int,
    val absent_count: Int,
    val total_sessions: Int,
    val attendance_rate: Double,
    val is_suspended: Boolean,
    val enrollment_id: Int,
    val discount_type: String? = "none",
    val discount_value: Int? = 0,
    val discount_amount: Long? = 0
)

// اینترفیس API
interface ClassDetailApi {
    @GET("classes/{id}/full_report")
    suspend fun getClassReport(@Path("id") id: Int): FullClassReport

    @GET("classes/{id}/students_full")
    suspend fun getClassStudentsFull(@Path("id") id: Int): ClassStudentsFullResponse

    @POST("attendance/student_history")
    suspend fun getStudentAttendanceHistory(@Body req: StudentAttendanceHistoryRequest): StudentAttendanceHistoryResponse
}

data class DeleteClassRequest(val forgive_session_charges: Boolean)

interface ClassDetailActionsApi {
    @DELETE("classes/{course_id}")
    suspend fun deleteClass(
        @Path("course_id") courseId: Int,
        @Query("forgive_session_charges") forgive: Boolean
    ): SimpleResponse

    @POST("classes/{course_id}/request_delete")
    suspend fun requestDeleteClass(
        @Path("course_id") courseId: Int,
        @Body req: DeleteClassRequest
    ): SimpleResponse

    @POST("classes/{course_id}/suspend")
    suspend fun suspendClass(@Path("course_id") courseId: Int): SuspendResponse

    @PUT("classes/update_info/{course_id}")
    suspend fun updateClassInfo(@Path("course_id") courseId: Int, @Body data: ClassUpdateInfo): SimpleResponse
}

data class ClassUpdateInfo(val title: String, val grade_level: String? = null)

class ClassDetailActivity : BaseActivity() {

    private var classId: Int = -1
    private var reportData: FullClassReport? = null
    var studentsFullData: ClassStudentsFullResponse? = null
    private lateinit var tvContent: TextView
    private lateinit var rvStudents: RecyclerView
    private lateinit var studentAdapter: ClassStudentAdapter
    private lateinit var tabLayout: TabLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_class_detail)

        classId = intent.getIntExtra("CLASS_ID", -1)
        tvContent = findViewById(R.id.tvClassContent)

        // Setup RecyclerView for students
        rvStudents = findViewById(R.id.rvStudents)
        rvStudents.layoutManager = LinearLayoutManager(this)
        studentAdapter = ClassStudentAdapter(emptyList()) { studentId, studentName ->
            // Open student attendance history
            openStudentAttendanceHistory(studentId, studentName)
        }
        rvStudents.adapter = studentAdapter

        // Hide RecyclerView initially, show TextView
        rvStudents.visibility = View.GONE
        tvContent.visibility = View.VISIBLE

        // ۱) دکمه ثبت حضور و غیاب
        findViewById<Button>(R.id.btnGoToAttendance).setOnClickListener {
            if (reportData != null) {
                val intent = Intent(this, AttendanceActivity::class.java)
                intent.putExtra("TARGET_COURSE_ID", classId)
                intent.putExtra("TARGET_COURSE_NAME", reportData!!.info.title)
                startActivity(intent)
            }
        }

        // ۲) دکمه ثبت‌نام و ویرایش تعداد دانش‌آموزان
        findViewById<Button>(R.id.btnClassSetupAction).setOnClickListener {
            if (reportData != null) {
                val intent = Intent(this, ClassSetupActivity::class.java)
                intent.putExtra("CLASS_ID", classId)
                intent.putExtra("CLASS_NAME", reportData!!.info.title)
                startActivity(intent)
            }
        }

        // ۳) دکمه اصلاح عنوان کلاس (فقط عنوان؛ پایه دست نمی‌خورد — رجوع به FIX grade-289)
        findViewById<Button>(R.id.btnEditClassInfoAction).setOnClickListener {
            showEditClassInfoDialog()
        }

        // ۴) دکمه تعلیق کلاس
        findViewById<Button>(R.id.btnSuspendAction).setOnClickListener {
            suspendClass()
        }

        // ۵) دکمه حذف کلاس (با اعمال قفل مالی انحصاری)
        findViewById<Button>(R.id.btnDeleteClassAction).setOnClickListener {
            showDeleteClassDialog()
        }

        // تنظیم تب‌ها
        tabLayout = findViewById<TabLayout>(R.id.tabLayoutClass)
        tabLayout.addOnTabSelectedListener(object : TabLayout.OnTabSelectedListener {
            override fun onTabSelected(tab: TabLayout.Tab?) {
                updateUI(tab?.position ?: 0)
            }
            override fun onTabUnselected(tab: TabLayout.Tab?) {}
            override fun onTabReselected(tab: TabLayout.Tab?) {}
        })

        // دکمه خروجی اکسل کلاس
        findViewById<Button>(R.id.btnClassExportExcel).setOnClickListener {
            ReportExporter.exportToExcel(
                context = this,
                endpointUrl = "classes/${classId}/students_full/excel",
                fileName = "class_students_${classId}.xlsx",
                onStart = {
                    Toast.makeText(this, getString(R.string.cdetail_excel_downloading), Toast.LENGTH_SHORT).show()
                },
                onComplete = {
                    Toast.makeText(this, getString(R.string.cdetail_excel_done), Toast.LENGTH_SHORT).show()
                },
                onError = { errorMsg ->
                    Toast.makeText(this, getString(R.string.cdetail_excel_error, errorMsg), Toast.LENGTH_LONG).show()
                }
            )
        }

        // دکمه چاپ PDF لیست کلاس
        findViewById<Button>(R.id.btnClassExportPdf).setOnClickListener {
            val data = studentsFullData
            if (data == null || data.students.isEmpty()) {
                Toast.makeText(this, getString(R.string.cdetail_students_not_loaded), Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val headers = listOf(getString(R.string.common_id), getString(R.string.cdetail_th_student), getString(R.string.cdetail_th_tuition), getString(R.string.cdetail_th_paid), getString(R.string.cdetail_th_debt), getString(R.string.cdetail_th_attendance))
            val rows = data.students.map { student ->
                listOf(
                    student.student_id.toString(),
                    student.student_name,
                    String.format("%,d", student.total_tuition),
                    String.format("%,d", student.paid),
                    String.format("%,d", student.debt_teacher + student.debt_institute),
                    "${String.format("%.1f", student.attendance_rate)}%"
                )
            }

            ReportExporter.printPdfReport(
                context = this,
                title = getString(R.string.cdetail_excel_title, reportData?.info?.title ?: ""),
                headers = headers,
                rows = rows
            )
        }

        fetchData()
        fetchStudentsFullData()
    }

    private fun showEditClassInfoDialog() {
        val view = LayoutInflater.from(this).inflate(R.layout.dialog_ip_input, null)
        val etInput = view.findViewById<android.widget.EditText>(R.id.etIpInput)
        etInput.hint = getString(R.string.cdetail_edit_hint)
        etInput.setText(reportData?.info?.title ?: "")

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.cdetail_edit_title))
            .setView(view)
            .setPositiveButton(getString(R.string.cdetail_edit_save)) { _, _ ->
                val newTitle = etInput.text.toString().trim()
                if (newTitle.isNotEmpty()) {
                    updateClassInfoOnServer(newTitle)
                }
            }
            .setNegativeButton(getString(R.string.common_cancel), null)
            .show()
    }

    private fun updateClassInfoOnServer(newTitle: String) {
        val retrofit = RetrofitClient.getInstance(this)
        val api = retrofit.create(ClassDetailActionsApi::class.java)

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                // FIX (grade-289): پایه هاردکد «دوازدهم» هر ویرایش عنوان را به خرابی grade_level
                // تبدیل می‌کرد. دیالوگ فقط عنوان می‌گیرد پس grade_level را اصلاً نمی‌فرستیم (null)؛
                // سرور None را «دست نزن» می‌فهمد. (Gson پیش‌فرض null را از JSON حذف می‌کند.)
                val response = api.updateClassInfo(classId, ClassUpdateInfo(newTitle))
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ClassDetailActivity, getString(R.string.common_ok_msg, response.message), Toast.LENGTH_SHORT).show()
                    fetchData() // Refresh details
                    fetchStudentsFullData()
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ClassDetailActivity, getString(R.string.cdetail_edit_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun suspendClass() {
        val retrofit = RetrofitClient.getInstance(this)
        val api = retrofit.create(ClassDetailActionsApi::class.java)

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val response = api.suspendClass(classId)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ClassDetailActivity, getString(R.string.common_ok_msg, response.message), Toast.LENGTH_SHORT).show()
                    fetchData() // Refresh
                    fetchStudentsFullData()
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ClassDetailActivity, getString(R.string.cdetail_suspend_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun showDeleteClassDialog() {
        val prefs = getSharedPreferences("UserCreds", Context.MODE_PRIVATE)
        val subRole = prefs.getString("USER_SUB_ROLE", "admin") ?: "admin"
        val checkBox = CheckBox(this).apply {
            text = getString(R.string.cdetail_forgive_check)
            isChecked = true
        }
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 24, 48, 0)
            addView(checkBox)
        }
        val msg = if (subRole == "admin") {
            getString(R.string.cdetail_del_admin)
        } else {
            getString(R.string.cdetail_del_request)
        }
        val dialog = AlertDialog.Builder(this)
            .setTitle(getString(R.string.cdetail_del_title))
            .setMessage(msg)
            .setView(container)
            .setPositiveButton(getString(R.string.common_delete_yes)) { _, _ ->
                performDeleteClass(subRole, checkBox.isChecked)
            }
            .setNegativeButton(getString(R.string.action_cancel), null)
            .create()

        dialog.show()
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setTextColor(android.graphics.Color.parseColor("#4CAF50"))
        dialog.getButton(AlertDialog.BUTTON_NEGATIVE).setTextColor(android.graphics.Color.parseColor("#F44336"))
    }

    private fun performDeleteClass(subRole: String, forgive: Boolean) {
        val retrofit = RetrofitClient.getInstance(this)
        val api = retrofit.create(ClassDetailActionsApi::class.java)

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val message = if (subRole == "admin") {
                    api.deleteClass(classId, forgive).message
                } else {
                    api.requestDeleteClass(classId, DeleteClassRequest(forgive)).message
                }
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ClassDetailActivity, getString(R.string.common_ok_msg, message), Toast.LENGTH_LONG).show()
                    
                    // ابطال کش مربوط به کلاس
                    CacheManager.clear(this@ClassDetailActivity, "class_report_$classId")
                    CacheManager.clear(this@ClassDetailActivity, "class_students_full_$classId")
                    CacheManager.clearByPrefix(this@ClassDetailActivity, "classes_list")
                    
                    finish() // Close page after deletion
                }
            } catch (e: retrofit2.HttpException) {
                val errorBody = e.response()?.errorBody()?.string()
                val message = if (!errorBody.isNullOrEmpty()) {
                    try {
                        val json = com.google.gson.JsonParser().parse(errorBody).asJsonObject
                        json.get("detail").getAsString()
                    } catch (parseEx: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (parseEx is kotlinx.coroutines.CancellationException) throw parseEx;
                        getString(R.string.cdetail_del_error)
                    }
                } else {
                    getString(R.string.cdetail_del_error)
                }
                withContext(Dispatchers.Main) {
                    // دیالوگ مقتدرانه با جزئیات مبالغ بدهی تفکیک شده
                    AlertDialog.Builder(this@ClassDetailActivity)
                        .setTitle(getString(R.string.cdetail_del_money_title))
                        .setMessage(message)
                        .setPositiveButton(getString(R.string.common_understood), null)
                        .show()
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ClassDetailActivity, getString(R.string.cdetail_net_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun fetchData() {
        val retrofit = RetrofitClient.getInstance(this)
        val api = retrofit.create(ClassDetailApi::class.java)

        val cacheKey = "class_report_" + classId
        val type = object : com.google.gson.reflect.TypeToken<FullClassReport>() {}.type

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.Main) {
            CachedApiCall.execute(
                context = this@ClassDetailActivity,
                cacheKey = cacheKey,
                type = type,
                networkCall = { api.getClassReport(classId) },
                onSuccess = { data, isOffline, timestamp ->
                    reportData = data
                    findViewById<TextView>(R.id.tvPageTitle).text = getString(R.string.cdetail_page_title, data.info.title, data.info.code)
                    updateUI(0) // نمایش تب اول
                    if (isOffline) {
                        CachedApiCall.showOfflineBanner(this@ClassDetailActivity, timestamp)
                    } else {
                        CachedApiCall.hideOfflineBanner(this@ClassDetailActivity)
                    }
                },
                onFailure = {
                    tvContent.text = getString(R.string.common_offline_empty)
                }
            )
        }
    }

    private fun updateUI(tabIndex: Int) {
        val scrollView = findViewById<View>(R.id.scrollViewContent)
        val tabContainer = findViewById<View>(R.id.llStudentTabContainer)

        when (tabIndex) {
            0 -> { // اطلاعات کلی
                if (reportData == null) return
                val data = reportData!!

                scrollView.visibility = View.VISIBLE
                tabContainer.visibility = View.GONE

                val sb = StringBuilder()
                sb.append(getString(R.string.cdetail_info_name, data.info.title))
                sb.append(getString(R.string.cdetail_info_code, data.info.code))
                sb.append(getString(R.string.cdetail_info_teacher, data.info.teacher_name))
                sb.append(getString(R.string.cdetail_info_sessions, data.info.session_count))
                sb.append(getString(R.string.cdetail_info_students, data.info.total_students))
                sb.append(getString(R.string.cdetail_info_revenue, String.format("%,d", data.info.total_revenue)))
                sb.append(getString(R.string.cdetail_info_debt, String.format("%,d", data.info.total_debt)))

                // پایش محاسباتی تفکیک مالی سهم مربی و آموزشگاه (به درخواست کارفرما)
                studentsFullData?.let { fullData ->
                    val totalDebtTeacher = fullData.students.sumOf { it.debt_teacher }
                    val totalDebtInstitute = fullData.students.sumOf { it.debt_institute }
                    
                    val totalPaidTeacher = fullData.students.sumOf { if ((it.wallet_teacher ?: 0L) > 0) it.wallet_teacher ?: 0L else 0L }
                    val totalPaidInstitute = fullData.students.sumOf { if ((it.wallet_institute ?: 0L) > 0) it.wallet_institute ?: 0L else 0L }
                    
                    sb.append("\n===========================\n")
                    sb.append(getString(R.string.cdetail_fin_teacher_title))
                    sb.append(getString(R.string.cdetail_fin_teacher_debt, String.format("%,d", totalDebtTeacher)))
                    sb.append(getString(R.string.cdetail_fin_teacher_paid, String.format("%,d", totalPaidTeacher)))
                    sb.append(getString(R.string.cdetail_fin_inst_title))
                    sb.append(getString(R.string.cdetail_fin_inst_debt, String.format("%,d", totalDebtInstitute)))
                    sb.append(getString(R.string.cdetail_fin_inst_paid, String.format("%,d", totalPaidInstitute)))
                }

                // نمایش وضعیت تعلیق کلاس
                studentsFullData?.let {
                    if (it.course_info.is_suspended) {
                        sb.append(getString(R.string.cdetail_suspended))
                    }
                }

                tvContent.text = sb.toString()
            }
            1 -> { // لیست دانش‌آموزان
                scrollView.visibility = View.GONE
                tabContainer.visibility = View.VISIBLE

                // Update students list with full data including attendance
                if (studentsFullData != null) {
                    updateStudentsListWithFullData()
                } else {
                    fetchStudentsFullData()
                }
            }
            2 -> { // تاریخچه جلسات
                if (reportData == null) return
                val data = reportData!!

                scrollView.visibility = View.VISIBLE
                tabContainer.visibility = View.GONE

                val sb = StringBuilder()
                sb.append(getString(R.string.cdetail_hist_title))
                if (data.sessions.isEmpty()) sb.append(getString(R.string.cdetail_hist_empty))

                data.sessions.forEachIndexed { index, sess ->
                    sb.append(getString(R.string.cdetail_hist_row, index + 1, sess.date))
                    sb.append(getString(R.string.cdetail_hist_present, sess.present_count))
                    sb.append(getString(R.string.cdetail_hist_absent, sess.absent_count))
                    sb.append("---------------------------\n")
                }
                tvContent.text = sb.toString()
            }
        }
    }

    private fun openStudentProfile(studentId: Int, studentName: String) {
        // Open student profile directly with student ID
        val intent = Intent(this, StudentProfileActivity::class.java)
        intent.putExtra("STUDENT_ID", studentId)
        startActivity(intent)
    }

    private fun openStudentAttendanceHistory(studentId: Int, studentName: String) {
        // Show student attendance history in a dialog
        showStudentAttendanceHistoryDialog(studentId, studentName)
    }

    private fun fetchStudentsWithIds() {
        val retrofit = RetrofitClient.getInstance(this)
        val api = retrofit.create(InvoiceApi::class.java)

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val response = api.getClassDetails(classId)
                withContext(Dispatchers.Main) {
                    studentAdapter.updateList(response.students)
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ClassDetailActivity, getString(R.string.cdetail_students_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun fetchStudentsFullData() {
        val retrofit = RetrofitClient.getInstance(this)
        val api = retrofit.create(ClassDetailApi::class.java)

        val cacheKey = "class_students_full_" + classId
        val type = object : com.google.gson.reflect.TypeToken<ClassStudentsFullResponse>() {}.type

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.Main) {
            CachedApiCall.execute(
                context = this@ClassDetailActivity,
                cacheKey = cacheKey,
                type = type,
                networkCall = { api.getClassStudentsFull(classId) },
                onSuccess = { response, isOffline, timestamp ->
                    studentsFullData = response
                    if (tabLayout.selectedTabPosition == 1) {
                        updateStudentsListWithFullData()
                    }
                    if (isOffline) {
                        CachedApiCall.showOfflineBanner(this@ClassDetailActivity, timestamp)
                    } else {
                        CachedApiCall.hideOfflineBanner(this@ClassDetailActivity)
                    }
                },
                onFailure = {
                    Toast.makeText(this@ClassDetailActivity, getString(R.string.common_offline_empty), Toast.LENGTH_SHORT).show()
                }
            )
        }
    }

    private fun updateStudentsListWithFullData() {
        studentsFullData?.let { data ->
            // Convert StudentFullItem to StudentItem for the adapter
            val studentItems = data.students.map { student ->
                StudentItem(
                    student_id = student.student_id,
                    student_name = student.student_name,
                    debt = student.debt,
                    enrollment_id = student.enrollment_id
                )
            }
            if (studentItems.isEmpty()) {
                Toast.makeText(this@ClassDetailActivity, getString(R.string.cdetail_students_empty), Toast.LENGTH_LONG).show()
            }
            studentAdapter.updateList(studentItems)
        }
    }

    private fun showStudentAttendanceHistoryDialog(studentId: Int, studentName: String) {
        val retrofit = RetrofitClient.getInstance(this)
        val api = retrofit.create(ClassDetailApi::class.java)

        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val response = api.getStudentAttendanceHistory(
                    StudentAttendanceHistoryRequest(student_id = studentId, course_id = classId)
                )

                withContext(Dispatchers.Main) {
                    val dialog = androidx.appcompat.app.AlertDialog.Builder(this@ClassDetailActivity)
                        .setTitle(getString(R.string.cdetail_att_title, studentName))
                        .setMessage(buildAttendanceHistoryMessage(response))
                        .setPositiveButton(getString(R.string.btn_dismiss), null)
                        .setNeutralButton(getString(R.string.cdetail_grade_btn)) { _, _ ->
                            val intent = Intent(this@ClassDetailActivity, SubmitGradeActivity::class.java).apply {
                                putExtra("STUDENT_ID", studentId)
                                putExtra("COURSE_ID", classId)
                                putExtra("STUDENT_NAME", studentName)
                            }
                            startActivity(intent)
                        }
                        .create()
                    dialog.show()
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ClassDetailActivity, getString(R.string.cdetail_att_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun buildAttendanceHistoryMessage(response: StudentAttendanceHistoryResponse): String {
        val sb = StringBuilder()
        sb.append(getString(R.string.cdetail_att_student, response.student_name))
        sb.append(getString(R.string.cdetail_att_class, response.course_title, response.course_code))
        sb.append(getString(R.string.cdetail_att_stats))
        sb.append(getString(R.string.cdetail_att_total, response.total_sessions))
        sb.append(getString(R.string.cdetail_att_present, response.present_count))
        sb.append(getString(R.string.cdetail_att_absent, response.absent_count))
        sb.append(getString(R.string.cdetail_att_rate, String.format("%.1f", response.attendance_rate)))

        sb.append(getString(R.string.cdetail_att_hist))
        if (response.attendance_history.isEmpty()) {
            sb.append(getString(R.string.cdetail_att_no_session))
        } else {
            response.attendance_history.forEachIndexed { index, session ->
                val statusIcon = if (session.status == "حاضر") getString(R.string.cdetail_st_present) else getString(R.string.cdetail_st_absent)
                sb.append("${index + 1}. ${session.date}: $statusIcon ${session.status}\n")
                sb.append(getString(R.string.cdetail_sess_cost, String.format("%,d", session.session_cost)))
                sb.append(getString(R.string.cdetail_sess_attendees, session.attendee_count))
                sb.append("   ---\n")
            }
        }

        return sb.toString()
    }
}

// Adapter for class students with clickable names
class ClassStudentAdapter(
    private var students: List<StudentItem>,
    private val onStudentClick: (Int, String) -> Unit
) : RecyclerView.Adapter<ClassStudentAdapter.StudentViewHolder>() {

    fun updateList(newList: List<StudentItem>) {
        students = newList
        notifyDataSetChanged()
    }

    class StudentViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvStudentName: TextView = view.findViewById(R.id.tvStudentName)
        val tvStudentMobile: TextView = view.findViewById(R.id.tvStudentMobile)
        val tvStudentPaid: TextView = view.findViewById(R.id.tvStudentPaid)
        val tvStudentDebt: TextView = view.findViewById(R.id.tvStudentDebt)
        val tvStudentStatus: TextView = view.findViewById(R.id.tvStudentStatus)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): StudentViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_class_student, parent, false)
        return StudentViewHolder(view)
    }

    override fun onBindViewHolder(holder: StudentViewHolder, position: Int) {
        val student = students[position]

        // Try to get full student data if available
        val activity = holder.itemView.context as? ClassDetailActivity
        val fullStudent = activity?.studentsFullData?.students?.find { it.student_id == student.student_id }

        if (fullStudent != null) {
            val dType = fullStudent.discount_type ?: "none"
            val dVal = fullStudent.discount_value ?: 0
            val codeStr = if (fullStudent.student_code != null) getString(R.string.cdetail_code_row, fullStudent.student_code) else ""

            if (dType != "none" && dVal > 0) {
                val dValDisp = if (dType == "percentage") "$dVal%" else getString(R.string.common_toman_format, dVal)
                holder.tvStudentName.text = getString(R.string.cdetail_student_row, student.student_name, codeStr, dValDisp)
            } else {
                holder.tvStudentName.text = "${student.student_name}$codeStr"
            }

            // Show attendance information
            holder.tvStudentMobile.text = getString(R.string.common_mobile_row, fullStudent.mobile)

            // Show attendance rate
            holder.tvStudentPaid.text = getString(R.string.cdetail_att_pct, String.format("%.1f", fullStudent.attendance_rate))
            holder.tvStudentPaid.visibility = View.VISIBLE

            // Show detailed debt information
            val totalDebt = fullStudent.debt_teacher + fullStudent.debt_institute
            if (totalDebt > 0) {
                val breakdown = getString(R.string.cdetail_debt_break, String.format("%,d", fullStudent.debt_teacher), String.format("%,d", fullStudent.debt_institute))
                holder.tvStudentDebt.text = getString(R.string.cdetail_debt_total, String.format("%,d", totalDebt), breakdown)
                holder.tvStudentStatus.text = getString(R.string.cdetail_unsettled)
                holder.tvStudentStatus.setTextColor(android.graphics.Color.parseColor("#D32F2F")) // Red
            } else {
                holder.tvStudentDebt.text = getString(R.string.cdetail_no_debt)
                holder.tvStudentStatus.text = getString(R.string.cdetail_settled)
                holder.tvStudentStatus.setTextColor(android.graphics.Color.parseColor("#388E3C")) // Green
            }

            // Show suspension status if applicable
            if (fullStudent.is_suspended) {
                holder.tvStudentStatus.text = getString(R.string.cdetail_susp)
                holder.tvStudentStatus.setTextColor(android.graphics.Color.parseColor("#FF9800")) // Orange
            }
        } else {
            // Fallback to basic info
            holder.tvStudentMobile.text = getString(R.string.cdetail_sid_row, student.student_id)

            // Show debt information
            if (student.debt > 0) {
                holder.tvStudentDebt.text = getString(R.string.cdetail_debt_row, String.format("%,d", student.debt))
                holder.tvStudentStatus.text = getString(R.string.cdetail_unsettled)
                holder.tvStudentStatus.setTextColor(android.graphics.Color.parseColor("#D32F2F")) // Red
            } else {
                holder.tvStudentDebt.text = getString(R.string.cdetail_no_debt)
                holder.tvStudentStatus.text = getString(R.string.cdetail_settled)
                holder.tvStudentStatus.setTextColor(android.graphics.Color.parseColor("#388E3C")) // Green
            }

            // Hide paid info
            holder.tvStudentPaid.visibility = View.GONE
        }

        // Make the whole item clickable
        holder.itemView.setOnClickListener {
            onStudentClick(student.student_id, student.student_name)
        }

        // Make student name specifically clickable
        holder.tvStudentName.setOnClickListener {
            onStudentClick(student.student_id, student.student_name)
        }
    }

    override fun getItemCount() = students.size
}
