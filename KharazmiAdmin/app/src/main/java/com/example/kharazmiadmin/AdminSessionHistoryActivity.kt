package com.example.kharazmiadmin

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

// تاریخچهٔ ادمین از endpoint گزارش می‌آید؛ بازگشایی فقط با guard مالی سرور انجام می‌شود.
data class AdminSessionHistoryResponse(val items: List<AdminSessionItem>, val count: Int)
data class AdminSessionItem(
    val id: Int, val course_title: String? = null, val date: String? = null,
    val time: String? = null, val status: String? = null,
    val problem_flags: List<String> = emptyList(), val reopen_allowed: Boolean = false
)

interface AdminSessionHistoryApi {
    @GET("admin/session_history")
    suspend fun getHistory(
        @Query("date_from") dateFrom: String? = null,
        @Query("date_to") dateTo: String? = null,
        @Query("teacher_id") teacherId: Int? = null,
        @Query("flag") flag: String? = null
    ): AdminSessionHistoryResponse

    @retrofit2.http.Streaming
    @GET("admin/session_history")
    suspend fun exportHistory(@Query("flag") flag: String? = null, @Query("export") export: Boolean = true): Response<ResponseBody>

    @POST("admin/session_history/{session_id}/reopen")
    suspend fun reopen(@Path("session_id") sessionId: Int, @Query("reason") reason: String): SimpleResponse
}

class AdminSessionHistoryActivity : BaseActivity() {
    private lateinit var adapter: AdminSessionHistoryAdapter
    private var filter: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_admin_session_history)
        val rv = findViewById<RecyclerView>(R.id.rvAdminSessionHistory)
        rv.layoutManager = LinearLayoutManager(this)
        adapter = AdminSessionHistoryAdapter(emptyList()) { item -> reopenSession(item) }
        rv.adapter = adapter
        findViewById<Button>(R.id.btnExportSessions).setOnClickListener { loadHistory(export = true) }
        findViewById<Button>(R.id.btnFilterSessions).setOnClickListener { loadHistory() }
        loadHistory()
    }

    private fun loadHistory(export: Boolean = false) {
        val flag = findViewById<TextView>(R.id.etSessionFlag).text.toString().trim().ifEmpty { null }
        filter = flag
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val historyApi = RetrofitClient.getInstance(this@AdminSessionHistoryActivity)
                    .create(AdminSessionHistoryApi::class.java)
                if (export) {
                    val file = historyApi.exportHistory(flag = flag)
                    withContext(Dispatchers.Main) {
                        Toast.makeText(this@AdminSessionHistoryActivity,
                            if (file.isSuccessful) "خروجی Excel آماده شد" else "خروجی Excel ناموفق بود",
                            Toast.LENGTH_LONG).show()
                    }
                    return@launch
                }
                val response = historyApi.getHistory(flag = flag)
                withContext(Dispatchers.Main) { adapter.replace(response.items) }
            } catch (error: Exception) {
                if (error is kotlinx.coroutines.CancellationException) throw error
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@AdminSessionHistoryActivity, "دریافت تاریخچه ناموفق بود", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun reopenSession(item: AdminSessionItem) {
        if (!item.reopen_allowed) {
            Toast.makeText(this, "این جلسه اثر مالی دارد و قابل بازگشایی نیست", Toast.LENGTH_LONG).show()
            return
        }
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                RetrofitClient.getInstance(this@AdminSessionHistoryActivity)
                    .create(AdminSessionHistoryApi::class.java).reopen(item.id, "اصلاح حضور و غیاب")
                withContext(Dispatchers.Main) { loadHistory() }
            } catch (error: Exception) {
                if (error is kotlinx.coroutines.CancellationException) throw error
                withContext(Dispatchers.Main) { Toast.makeText(this@AdminSessionHistoryActivity, "بازگشایی انجام نشد", Toast.LENGTH_SHORT).show() }
            }
        }
    }
}

class AdminSessionHistoryAdapter(
    private var items: List<AdminSessionItem>, private val onReopen: (AdminSessionItem) -> Unit
) : RecyclerView.Adapter<AdminSessionHistoryAdapter.VH>() {
    class VH(view: View) : RecyclerView.ViewHolder(view) {
        val title: TextView = view.findViewById(R.id.tvSessionTitle)
        val flags: TextView = view.findViewById(R.id.tvProblemFlags)
        val reopen: Button = view.findViewById(R.id.btnReopenSession)
    }
    override fun onCreateViewHolder(parent: ViewGroup, type: Int): VH = VH(
        LayoutInflater.from(parent.context).inflate(R.layout.item_admin_session_history, parent, false)
    )
    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = items[position]
        holder.title.text = "${item.course_title ?: "کلاس"} | ${item.date ?: "تاریخ نامشخص"} ${item.time ?: ""}"
        holder.flags.text = if (item.problem_flags.isEmpty()) "بدون پرچم مشکل" else item.problem_flags.joinToString("، ")
        holder.reopen.visibility = if (item.reopen_allowed) View.VISIBLE else View.GONE
        holder.reopen.setOnClickListener { onReopen(item) }
    }
    override fun getItemCount() = items.size
    fun replace(value: List<AdminSessionItem>) { items = value; notifyDataSetChanged() }
}
