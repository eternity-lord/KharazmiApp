package com.example.kharazmiadmin

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.http.GET
import retrofit2.http.Query

/** نمای مدیریتی بدهکاران؛ اعداد و ردیف‌ها از همان منبع /finance/reports/debtors_grouped می‌آیند. */
data class DebtorTeacherSummary(
    val teacher_id: Int? = null,
    val teacher_name: String = "بدون معلم",
    val debt: Long = 0,
    val students_count: Int = 0,
    val courses: List<String> = emptyList()
)

data class DebtorAgeSummary(
    val bucket: String = "",
    val debt: Long = 0,
    val students_count: Int = 0
)

data class DebtorTeacherRow(
    val teacher_id: Int? = null,
    val teacher_name: String = "بدون معلم",
    val course_title: String? = null,
    val debt: Long = 0
)

data class DebtorRow(
    val student_id: Int,
    val student_name: String = "نامشخص",
    val parent_mobile: String? = null,
    val student_mobile: String? = null,
    val contact_mobile: String? = null,
    val debt_teacher: Long = 0,
    val debt_institute: Long = 0,
    val total_debt: Long = 0,
    val active_courses: List<String> = emptyList(),
    val last_payment_date: String? = null,
    val debt_age_days: Int? = null,
    val debt_age_bucket: String? = null,
    val teachers: List<DebtorTeacherRow> = emptyList()
)

data class DebtorsGroupedResponse(
    val total_debt: Long = 0,
    val debtors_count: Int = 0,
    val by_teacher: List<DebtorTeacherSummary> = emptyList(),
    val by_age: List<DebtorAgeSummary> = emptyList(),
    val unassigned_debt: Long = 0,
    val rows: List<DebtorRow> = emptyList()
)

interface DebtorsApi {
    @GET("finance/reports/debtors_grouped")
    suspend fun getGrouped(@Query("search") search: String? = null): DebtorsGroupedResponse
}

class DebtorsActivity : BaseActivity() {
    private lateinit var etSearch: EditText
    private lateinit var btnSearch: MaterialButton
    private lateinit var btnExport: MaterialButton
    private lateinit var btnRefresh: MaterialButton
    private lateinit var tvSummary: TextView
    private lateinit var tvBreakdown: TextView
    private lateinit var tvEmpty: TextView
    private lateinit var rvRows: RecyclerView
    private lateinit var adapter: DebtorsAdapter
    private lateinit var api: DebtorsApi

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_debtors)
        etSearch = findViewById(R.id.etDebtorsSearch)
        btnSearch = findViewById(R.id.btnDebtorsSearch)
        btnExport = findViewById(R.id.btnDebtorsExport)
        btnRefresh = findViewById(R.id.btnDebtorsRefresh)
        tvSummary = findViewById(R.id.tvDebtorsSummary)
        tvBreakdown = findViewById(R.id.tvDebtorsBreakdown)
        tvEmpty = findViewById(R.id.tvDebtorsEmpty)
        rvRows = findViewById(R.id.rvDebtors)
        api = RetrofitClient.getInstance(this).create(DebtorsApi::class.java)
        adapter = DebtorsAdapter(emptyList()) { id ->
            startActivity(Intent(this, StudentProfileActivity::class.java).putExtra("STUDENT_ID", id))
        }
        rvRows.layoutManager = LinearLayoutManager(this)
        rvRows.adapter = adapter
        btnSearch.setOnClickListener { load() }
        btnRefresh.setOnClickListener { etSearch.setText(""); load() }
        btnExport.setOnClickListener { exportAllDebtors() }
        load()
    }

    private fun load() {
        val search = etSearch.text.toString().trim().ifEmpty { null }
        tvEmpty.visibility = View.VISIBLE
        tvEmpty.text = "در حال دریافت گزارش بدهکاران…"
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val result = api.getGrouped(search)
                withContext(Dispatchers.Main) {
                    tvSummary.text = "تعداد بدهکاران: ${result.debtors_count} | کل بدهی: ${result.total_debt} تومان | بدون انتساب معلم: ${result.unassigned_debt} تومان"
                    tvBreakdown.text = result.by_age.joinToString(" | ") { "${it.bucket}: ${it.debt} تومان (${it.students_count})" }
                    adapter.replace(result.rows)
                    tvEmpty.visibility = if (result.rows.isEmpty()) View.VISIBLE else View.GONE
                    if (result.rows.isEmpty()) tvEmpty.text = "برای این جست‌وجو بدهکاری ثبت نشده است"
                }
            } catch (error: Exception) {
                if (error is kotlinx.coroutines.CancellationException) throw error
                withContext(Dispatchers.Main) {
                    tvEmpty.text = "دریافت گزارش بدهکاران ناموفق بود: ${error.message ?: "خطای سرور"}"
                    tvEmpty.visibility = View.VISIBLE
                    Toast.makeText(this@DebtorsActivity, tvEmpty.text, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun exportAllDebtors() {
        val base = RetrofitClient.getInstance(this).baseUrl().toString()
        ReportExporter.exportToExcel(
            context = this,
            endpointUrl = "${base}exports/debtors",
            fileName = "debtors_${System.currentTimeMillis()}.csv",
            onStart = { Toast.makeText(this, "در حال ساخت خروجی بدهکاران…", Toast.LENGTH_SHORT).show() },
            onComplete = { Toast.makeText(this, "خروجی بدهکاران آماده شد", Toast.LENGTH_LONG).show() },
            onError = { Toast.makeText(this, "خروجی بدهکاران ناموفق بود: $it", Toast.LENGTH_LONG).show() },
            mimeType = "text/csv"
        )
    }
}

private class DebtorsAdapter(
    private var rows: List<DebtorRow>,
    private val onStudentClick: (Int) -> Unit
) : RecyclerView.Adapter<DebtorsAdapter.VH>() {
    class VH(val text: TextView) : RecyclerView.ViewHolder(text)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = TextView(parent.context).apply {
            setPadding(20, 18, 20, 18)
            textSize = 15f
            isClickable = true
            setTextColor(android.graphics.Color.WHITE)
        }
        return VH(view)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val row = rows[position]
        val teacher = row.teachers.joinToString("، ") { "${it.teacher_name}: ${it.debt}" }
        holder.text.text = buildString {
            append("${row.student_name} — بدهی کل: ${row.total_debt} تومان\n")
            append("معلم: ${if (teacher.isBlank()) "نامشخص" else teacher}\n")
            append("آموزشگاه: ${row.debt_institute} | آخرین پرداخت: ${row.last_payment_date ?: "بدون پرداخت"} | ")
            append("تماس: ${row.contact_mobile ?: row.parent_mobile ?: row.student_mobile ?: "ثبت نشده"}")
        }
        holder.text.setOnClickListener { onStudentClick(row.student_id) }
    }

    override fun getItemCount(): Int = rows.size
    fun replace(value: List<DebtorRow>) { rows = value; notifyDataSetChanged() }
}
