package com.example.kharazmiadmin

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.RadioButton
import android.widget.RadioGroup
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
import java.util.concurrent.atomic.AtomicBoolean

// ==========================================
// 🎥 صفحه‌ی «کلاس زنده» معلم
// این صفحه روی همان زیرساخت ثبت جلسه سوار است؛ فقط یک لایه‌ی وضعیت زنده اضافه
// می‌کند و در پایان، مسیر موجود (end_live -> submit_session) را صدا می‌زند.
// ==========================================

class LiveClassActivity : BaseActivity() {

    private var courseId: Int = -1
    private var liveSessionId: Int = -1
    private var startedAtTs: Long = System.currentTimeMillis() / 1000
    private var classTitle: String = ""

    private lateinit var api: LiveApi
    private lateinit var apiDetails: InvoiceApi
    private lateinit var rv: RecyclerView
    private lateinit var tvLiveIndicator: TextView
    private lateinit var tvStartedAt: TextView

    private val statusMap = HashMap<Int, String>()   // student_id -> Present/Absent/Late
    private val excusedMap = HashMap<Int, Boolean>() // student_id -> excused
    private var studentList: List<StudentItem> = listOf()

    private val handler = Handler(Looper.getMainLooper())
    private val timerRunnable = object : Runnable {
        override fun run() {
            updateElapsed()
            handler.postDelayed(this, 1000)
        }
    }

    // برای جلوگیری از هم‌زمانی ارسال چند snapshot (جلوگیری از بار اضافه)
    private val syncInFlight = AtomicBoolean(false)
    private val syncPending = AtomicBoolean(false)
    private val syncHandler = Handler(Looper.getMainLooper())
    private val syncRunnable = object : Runnable {
        override fun run() { pushSnapshot() }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_live_class)

        courseId = intent.getIntExtra("TARGET_COURSE_ID", -1)
        classTitle = intent.getStringExtra("TARGET_COURSE_NAME") ?: ""
        liveSessionId = intent.getIntExtra("LIVE_SESSION_ID", -1)
        startedAtTs = intent.getLongExtra("STARTED_AT_TS", System.currentTimeMillis() / 1000)

        tvLiveIndicator = findViewById(R.id.tvLiveIndicator)
        tvStartedAt = findViewById(R.id.tvLiveStartedAt)
        rv = findViewById(R.id.rvLiveStudents)
        rv.layoutManager = LinearLayoutManager(this)

        val retrofit = RetrofitClient.getInstance(this)
        api = retrofit.create(LiveApi::class.java)
        apiDetails = retrofit.create(InvoiceApi::class.java)

        findViewById<MaterialButton>(R.id.btnEndLive).setOnClickListener { promptEndLive() }

        // اگر live_session_id داده نشد، از سرور بازیابی کن
        if (liveSessionId <= 0) {
            resolveCurrentLive()
        } else {
            findViewById<TextView>(R.id.tvLiveTitle).text = getString(R.string.lcls_title, classTitle)
            fetchStudents()
        }

        handler.post(timerRunnable)
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacks(timerRunnable)
        syncHandler.removeCallbacks(syncRunnable)
    }

    private fun resolveCurrentLive() {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val cur = api.getCurrentLive()
                withContext(Dispatchers.Main) {
                    if (cur != null) {
                        courseId = cur.courseId
                        liveSessionId = cur.liveSessionId
                        classTitle = cur.classTitle
                        startedAtTs = cur.startedAtTs ?: startedAtTs
                        findViewById<TextView>(R.id.tvLiveTitle).text = getString(R.string.lcls_title_fallback, classTitle.ifEmpty { cur.courseCode })
                        fetchStudents()
                    } else {
                        Toast.makeText(this@LiveClassActivity, getString(R.string.lcls_none), Toast.LENGTH_SHORT).show()
                        finish()
                    }
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@LiveClassActivity, getString(R.string.lcls_fetch_error), Toast.LENGTH_SHORT).show()
                    finish()
                }
            }
        }
    }

    private fun fetchStudents() {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val response = apiDetails.getClassDetails(courseId)
                studentList = response.students
                // پیش‌فرض: همه حاضر، غیرموجه
                studentList.forEach {
                    statusMap[it.student_id] = "Present"
                    excusedMap[it.student_id] = false
                }
                withContext(Dispatchers.Main) {
                    rv.adapter = LiveStudentAdapter(
                        studentList,
                        statusMap,
                        excusedMap,
                        onChanged = { scheduleSync() }
                    )
                    pushSnapshot()
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@LiveClassActivity, getString(R.string.lcls_list_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun updateElapsed() {
        val now = System.currentTimeMillis() / 1000
        val elapsedSec = (now - startedAtTs).coerceAtLeast(0)
        val mins = elapsedSec / 60
        tvLiveIndicator.text = getString(R.string.lcls_live_row, mins)
        tvStartedAt.text = getString(R.string.lcls_started, elapsedToHm(startedAtTs))
    }

    private fun elapsedToHm(ts: Long): String {
        val cal = java.util.Calendar.getInstance()
        cal.timeInMillis = ts * 1000
        return String.format(java.util.Locale.US, "%02d:%02d", cal.get(java.util.Calendar.HOUR_OF_DAY), cal.get(java.util.Calendar.MINUTE))
    }

    // همگام‌سازی پیشینه با سرور (Optimistic UI: محلی فوری، سرور با تاخیر)
    private fun scheduleSync() {
        syncHandler.removeCallbacks(syncRunnable)
        syncHandler.postDelayed(syncRunnable, 800)
    }

    private fun pushSnapshot() {
        if (liveSessionId <= 0) return
        if (syncInFlight.get()) {
            syncPending.set(true)
            return
        }
        // ساخت snapshot روی همان ترد فراخوان (Main) تا HashMap امن بماند
        val payloadItems = LinkedHashMap<String, LiveStatusEntry>()
        statusMap.forEach { (key, status) ->
            payloadItems[key.toString()] = LiveStatusEntry(status = status, excused = excusedMap[key] ?: false)
        }
        val payload = LiveStatusPayload(items = payloadItems)
        syncInFlight.set(true)
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                api.saveLiveStatus(liveSessionId, payload)
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                // شکست هم‌گام‌سازی نباید UI را قطع کند؛ صف دوباره تلاش می‌کند
            } finally {
                syncInFlight.set(false)
                if (syncPending.getAndSet(false)) {
                    withContext(Dispatchers.Main) { scheduleSync() }
                }
            }
        }
    }

    private fun promptEndLive() {
        val dialog = AlertDialog.Builder(this)
            .setTitle(getString(R.string.lcls_end_title))
            .setMessage(getString(R.string.lcls_end_msg))
            .setPositiveButton(getString(R.string.common_yes)) { _, _ -> endLive() }
            .setNegativeButton(getString(R.string.common_no), null)
            .create()
        dialog.show()
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setTextColor(android.graphics.Color.parseColor("#4CAF50"))
        dialog.getButton(AlertDialog.BUTTON_NEGATIVE).setTextColor(android.graphics.Color.parseColor("#F44336"))
    }

    private fun endLive() {
        // آخرین snapshot را هم ارسال کن
        pushSnapshot()
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val res = api.endLive(liveSessionId, LiveEndPayload())
                CacheManager.clearByPrefix(this@LiveClassActivity, "today_summary_teacher_")
                withContext(Dispatchers.Main) {
                    // FIX (گروه۱/آیتم۱): «جلسهٔ این تاریخ قبلاً ثبت شده» دیگر ۴۰۹ نیست؛ سرور کلاس
                    // زنده را بسته و پیام گویا فرستاده ⇒ همان پیام را نشان می‌دهیم، نه «سهم معلم: ۰»
                    // (که پیش‌تر معلم را گمراه می‌کرد) و نه خطای خام.
                    if (res.duplicateDate == true) {
                        Toast.makeText(
                            this@LiveClassActivity,
                            getString(R.string.lcls_duplicate_msg, res.message),
                            Toast.LENGTH_LONG
                        ).show()
                        finish()
                        return@withContext
                    }
                    val teacherShare = res.details?.teacher_share ?: 0
                    val instShare = res.details?.institute_share ?: 0
                    Toast.makeText(
                        this@LiveClassActivity,
                        getString(R.string.lcls_done_msg, String.format("%,d", teacherShare), String.format("%,d", instShare)),
                        Toast.LENGTH_LONG
                    ).show()
                    finish()
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@LiveClassActivity, getString(R.string.lcls_end_error, e.message), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }
}

// آداپتور لیست لحظه‌ای دانش‌آموزان
class LiveStudentAdapter(
    private val list: List<StudentItem>,
    private val statusMap: HashMap<Int, String>,
    private val excusedMap: HashMap<Int, Boolean>,
    private val onChanged: () -> Unit
) : RecyclerView.Adapter<LiveStudentAdapter.VH>() {

    class VH(v: View) : RecyclerView.ViewHolder(v) {
        val name: TextView = v.findViewById(R.id.tvLiveStName)
        val rg: RadioGroup = v.findViewById(R.id.rgLiveStatus)
        val rgExcused: RadioGroup = v.findViewById(R.id.rgLiveExcused)
        val rbUnexcused: RadioButton = v.findViewById(R.id.rbLiveUnexcused)
        val rbExcused: RadioButton = v.findViewById(R.id.rbLiveExcused)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val v = LayoutInflater.from(parent.context).inflate(R.layout.item_live_class_student, parent, false)
        return VH(v)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = list[position]
        holder.name.text = item.student_name

        holder.name.setOnClickListener {
            val intent = android.content.Intent(holder.itemView.context, StudentProfileActivity::class.java)
            intent.putExtra("STUDENT_ID", item.student_id)
            holder.itemView.context.startActivity(intent)
        }

        holder.rg.setOnCheckedChangeListener(null)
        holder.rgExcused.setOnCheckedChangeListener(null)

        when (statusMap[item.student_id]) {
            "Present" -> { holder.rg.check(R.id.rbLivePresent); holder.rgExcused.visibility = View.GONE }
            "Absent" -> {
                holder.rg.check(R.id.rbLiveAbsent)
                holder.rgExcused.visibility = View.VISIBLE
                if (excusedMap[item.student_id] == true) holder.rgExcused.check(R.id.rbLiveExcused) else holder.rgExcused.check(R.id.rbLiveUnexcused)
            }
            "Late" -> { holder.rg.check(R.id.rbLiveLate); holder.rgExcused.visibility = View.GONE }
        }

        holder.rg.setOnCheckedChangeListener { _, checkedId ->
            val status = when (checkedId) {
                R.id.rbLivePresent -> "Present"
                R.id.rbLiveAbsent -> "Absent"
                else -> "Late"
            }
            statusMap[item.student_id] = status
            if (status == "Absent") {
                holder.rgExcused.visibility = View.VISIBLE
                excusedMap[item.student_id] = holder.rbExcused.isChecked
            } else {
                holder.rgExcused.visibility = View.GONE
                excusedMap[item.student_id] = false
            }
            onChanged()
        }

        holder.rgExcused.setOnCheckedChangeListener { _, checkedId ->
            excusedMap[item.student_id] = checkedId == R.id.rbLiveExcused
            onChanged()
        }
    }

    override fun getItemCount() = list.size
}
