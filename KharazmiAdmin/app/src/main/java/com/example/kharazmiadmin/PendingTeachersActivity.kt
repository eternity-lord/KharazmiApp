package com.example.kharazmiadmin

import android.graphics.BitmapFactory
import android.os.Bundle
import android.util.Base64
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

// مدل داده معلم
data class TeacherPending(
    val id: Int,
    val first_name: String,
    val last_name: String,
    val mobile: String,
    val profile_image: String?
)

data class ApproveResponse(val message: String)

interface PendingApi {
    @GET("teachers/pending")
    suspend fun getPendingTeachers(): List<TeacherPending>

    @POST("teachers/approve/{id}")
    suspend fun approveTeacher(@Path("id") id: Int): ApproveResponse

    // ❌ متد جدید برای رد کردن (حذف) معلم
    @DELETE("teachers/reject/{id}")
    suspend fun rejectTeacher(@Path("id") id: Int): ApproveResponse
}

class PendingTeachersActivity : BaseActivity() {

    private lateinit var api: PendingApi
    private lateinit var rvPending: RecyclerView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_pending_teachers)

        rvPending = findViewById(R.id.rvPendingTeachers)
        rvPending.layoutManager = LinearLayoutManager(this)

        val retrofit = RetrofitClient.getInstance(this)
        api = retrofit.create(PendingApi::class.java)

        fetchPendingList()
    }

    private fun fetchPendingList() {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val list = api.getPendingTeachers()
                withContext(Dispatchers.Main) {
                    if (list.isEmpty()) {
                        Toast.makeText(this@PendingTeachersActivity, getString(R.string.ptch_empty), Toast.LENGTH_SHORT).show()
                    }
                    // 👇 حالا دو تا تابع به آداپتور پاس میدیم (تایید و رد)
                    rvPending.adapter = PendingAdapter(list,
                        onApproveClick = { teacherId -> approveTeacher(teacherId) },
                        onRejectClick = { teacherId -> rejectTeacher(teacherId) }
                    )
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                android.util.Log.e("PendingTeachersActivity", "fetchPendingList failed", e)
            }
        }
    }

    // تایید معلم
    private fun approveTeacher(teacherId: Int) {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val res = api.approveTeacher(teacherId)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@PendingTeachersActivity, getString(R.string.common_ok_msg, res.message), Toast.LENGTH_LONG).show()
                    
                    // ابطال کش لیست معلمان فعال
                    CacheManager.clearByPrefix(this@PendingTeachersActivity, "person_list_TEACHER")
                    
                    fetchPendingList() // رفرش لیست
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@PendingTeachersActivity, getString(R.string.ptch_op_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    // ❌ رد کردن معلم (حذف درخواست)
    private fun rejectTeacher(teacherId: Int) {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val res = api.rejectTeacher(teacherId)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@PendingTeachersActivity, getString(R.string.common_deleted_msg, res.message), Toast.LENGTH_LONG).show()
                    
                    // ابطال کش لیست معلمان فعال
                    CacheManager.clearByPrefix(this@PendingTeachersActivity, "person_list_TEACHER")
                    
                    fetchPendingList() // رفرش لیست
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@PendingTeachersActivity, getString(R.string.ptch_del_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }
}

// آداپتور آپدیت شده
class PendingAdapter(
    private val list: List<TeacherPending>,
    private val onApproveClick: (Int) -> Unit,
    private val onRejectClick: (Int) -> Unit // ✅ اضافه شده
) : RecyclerView.Adapter<PendingAdapter.VH>() {

    class VH(v: View) : RecyclerView.ViewHolder(v) {
        val name: TextView = v.findViewById(R.id.tvName)
        val mobile: TextView = v.findViewById(R.id.tvMobile)
        val avatar: ImageView = v.findViewById(R.id.imgAvatar)
        val btnApprove: Button = v.findViewById(R.id.btnApprove)
        val btnReject: Button = v.findViewById(R.id.btnReject) // ✅ دکمه قرمز
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val v = LayoutInflater.from(parent.context).inflate(R.layout.item_pending, parent, false)
        return VH(v)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = list[position]
        holder.name.text = "${item.first_name} ${item.last_name}"
        holder.mobile.text = item.mobile

        if (item.profile_image != null) {
            try {
                val imageBytes = Base64.decode(item.profile_image, Base64.DEFAULT)
                val decodedImage = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size)
                holder.avatar.setImageBitmap(decodedImage)
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e; }
        }

        // کلیک روی تایید
        holder.btnApprove.setOnClickListener {
            onApproveClick(item.id)
        }

        // کلیک روی رد کردن
        holder.btnReject.setOnClickListener {
            onRejectClick(item.id)
        }
    }

    override fun getItemCount() = list.size
}
