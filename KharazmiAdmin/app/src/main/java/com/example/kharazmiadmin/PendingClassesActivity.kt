package com.example.kharazmiadmin

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

// API
interface AdminClassApi {
    @GET("admin/pending_classes")
    suspend fun getPendingClasses(): List<PendingClassItem>

    // این متد شاید توی صفحه جزئیات استفاده بشه، ولی اینجا هم میمونه
    @POST("admin/approve_class/{id}")
    suspend fun approveClass(@Path("id") id: Int): SimpleResponse

    // ❌ متد جدید برای رد کردن (حذف) کلاس
    @DELETE("admin/reject_class/{id}")
    suspend fun rejectClass(@Path("id") id: Int): SimpleResponse
}

class PendingClassesActivity : BaseActivity() {

    private lateinit var rv: RecyclerView
    private lateinit var api: AdminClassApi

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_pending_classes)

        rv = findViewById(R.id.rvPendingClasses)
        rv.layoutManager = LinearLayoutManager(this)

        val retrofit = RetrofitClient.getInstance(this)
        api = retrofit.create(AdminClassApi::class.java)
    }

    override fun onResume() {
        super.onResume()
        fetchPending() // رفرش لیست هر بار که به صفحه برمیگردیم
    }

    private fun fetchPending() {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val list = api.getPendingClasses()
                withContext(Dispatchers.Main) {
                    if (list.isEmpty()) {
                        Toast.makeText(this@PendingClassesActivity, getString(R.string.pcls_empty), Toast.LENGTH_SHORT).show()
                    }
                    rv.adapter = PendingClassAdapter(list) { id ->
                        showRejectDialog(id)
                    }
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@PendingClassesActivity, getString(R.string.common_list_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    // دیالوگ تایید حذف
    private fun showRejectDialog(id: Int) {
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.pcls_reject_title))
            .setMessage(getString(R.string.pcls_reject_msg))
            .setPositiveButton(getString(R.string.common_delete_yes)) { _, _ ->
                rejectClass(id)
            }
            .setNegativeButton(getString(R.string.action_cancel), null)
            .show()
    }

    // ❌ اتصال به سرور برای حذف کلاس
    private fun rejectClass(id: Int) {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val res = api.rejectClass(id)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@PendingClassesActivity, getString(R.string.common_deleted_msg, res.message), Toast.LENGTH_LONG).show()
                    fetchPending() // رفرش لیست
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@PendingClassesActivity, getString(R.string.pcls_op_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }
}

// آداپتور لیست
class PendingClassAdapter(
    private val list: List<PendingClassItem>,
    private val onRejectClick: (Int) -> Unit // فقط اکشن حذف رو پاس میدیم، تایید میره توی صفحه جزئیات
) : RecyclerView.Adapter<PendingClassAdapter.VH>() {

    class VH(v: View) : RecyclerView.ViewHolder(v) {
        val title: TextView = v.findViewById(R.id.tvTitle)
        val code: TextView = v.findViewById(R.id.tvCode)
        val teacher: TextView = v.findViewById(R.id.tvTeacher)
        val price: TextView = v.findViewById(R.id.tvPrice)
        val schedule: TextView = v.findViewById(R.id.tvSchedule)

        val btnApprove: MaterialButton = v.findViewById(R.id.btnApproveClass) // دکمه سبز
        val btnReject: MaterialButton = v.findViewById(R.id.btnRejectClass)   // دکمه قرمز
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val v = LayoutInflater.from(parent.context).inflate(R.layout.item_pending_class, parent, false)
        return VH(v)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = list[position]
        holder.title.text = item.title
        holder.code.text = holder.itemView.context.getString(R.string.pcls_code_row, item.id) // یا item.code
        holder.teacher.text = holder.itemView.context.getString(R.string.pcls_teacher_row, item.teacher_name)
        holder.price.text = holder.itemView.context.getString(R.string.pcls_price_row, String.format("%,d", item.teacher_price))
        holder.schedule.text = holder.itemView.context.getString(R.string.pcls_sched_row, item.days, item.time)

        // ✅ کلیک روی دکمه تایید (سبز) -> رفتن به صفحه جزئیات
        holder.btnApprove.setOnClickListener {
            val intent = Intent(holder.itemView.context, PendingClassDetailActivity::class.java)
            intent.putExtra("COURSE_ID", item.id)
            intent.putExtra("TEACHER_PRICE", item.teacher_price)
            intent.putExtra("INSTITUTE_SHARE", item.base_institute_share) // FIX (audit-v2/blind-approve-2b): ارسال سهم واقعی به صفحه جزئیات
            intent.putExtra("TITLE", item.title)
            holder.itemView.context.startActivity(intent)
        }

        // ❌ کلیک روی دکمه رد کردن (قرمز) -> حذف مستقیم
        holder.btnReject.setOnClickListener {
            onRejectClick(item.id)
        }
    }

    override fun getItemCount() = list.size
}
