package com.example.kharazmiadmin

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
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
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

// API Models for Notification Center
data class NotificationItem(
    val id: Int,
    val type: String,
    val title: String,
    val body: String,
    val is_read: Boolean,
    val created_at: String
)

interface NotificationCenterApi {
    @GET("notifications")
    suspend fun getNotifications(): List<NotificationItem>

    @POST("notifications/{id}/read")
    suspend fun markRead(@Path("id") id: Int): SimpleResponse

    @POST("notifications/read_all")
    suspend fun markAllRead(): SimpleResponse
}

class NotificationCenterActivity : BaseActivity() {

    private lateinit var rv: RecyclerView
    private lateinit var btnMarkAll: MaterialButton
    private lateinit var btnFilter: MaterialButton

    private lateinit var api: NotificationCenterApi
    private var allNotifications: List<NotificationItem> = emptyList()
    private var activeFilterType: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_notification_list)

        initViews()
        setupApi()
        setupListeners()
        loadNotifications()
    }

    private fun initViews() {
        rv = findViewById(R.id.rvNotifications)
        btnMarkAll = findViewById(R.id.btnMarkAllRead)
        btnFilter = findViewById(R.id.btnFilterNotifs)

        rv.layoutManager = LinearLayoutManager(this)
    }

    private fun setupApi() {
        val retrofit = RetrofitClient.getInstance(this)
        api = retrofit.create(NotificationCenterApi::class.java)
    }

    private fun setupListeners() {
        btnMarkAll.setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle(getString(R.string.notif_readall_title))
                .setMessage(getString(R.string.notif_readall_msg))
                .setPositiveButton(getString(R.string.common_yes)) { _, _ ->
                    markAllAsRead()
                }
                .setNegativeButton(getString(R.string.common_cancel), null)
                .show()
        }

        btnFilter.setOnClickListener {
            showFilterDialog()
        }
    }

    private fun loadNotifications() {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val list = api.getNotifications()
                withContext(Dispatchers.Main) {
                    allNotifications = list
                    applyFilterAndBind()
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@NotificationCenterActivity, getString(R.string.notif_list_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun applyFilterAndBind() {
        val filtered = if (activeFilterType == null) {
            allNotifications
        } else {
            allNotifications.filter { it.type.lowercase() == activeFilterType?.lowercase() }
        }
        rv.adapter = NotificationAdapter(filtered) { notif ->
            showNotificationDetailDialog(notif)
        }
    }

    private fun markAllAsRead() {
        // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                api.markAllRead()
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@NotificationCenterActivity, getString(R.string.notif_all_read), Toast.LENGTH_SHORT).show()
                    loadNotifications() // Reload
                }
            } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e;
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@NotificationCenterActivity, getString(R.string.notif_status_error), Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun showNotificationDetailDialog(item: NotificationItem) {
        // Mark as read immediately on open
        if (!item.is_read) {
            // FIX: Bug 19 - cancel screen work when this Activity is destroyed.
            lifecycleScope.launch(Dispatchers.IO) {
                try {
                    api.markRead(item.id)
                    withContext(Dispatchers.Main) {
                        loadNotifications() // Reload list silently
                    }
                } catch (e: Exception) {
                // FIX: Bug 19 - cancellation is not a network/UI error.
                if (e is kotlinx.coroutines.CancellationException) throw e; android.util.Log.e("NotificationCenterActivity", "showNotificationDetailDialog failed", e) }
            }
        }

        // Show Details Dialog
        AlertDialog.Builder(this)
            .setTitle(item.title)
            .setMessage("${item.created_at}\n\n${item.body}")
            .setPositiveButton(getString(R.string.common_understood), null)
            .show()
    }

    private fun showFilterDialog() {
        val types = arrayOf(getString(R.string.notif_f_all), getString(R.string.notif_f_att), getString(R.string.notif_f_money), getString(R.string.notif_f_sys))
        val typeCodes = arrayOf(null, "attendance", "installment", "system")

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.notif_filter_title))
            .setItems(types) { _, which ->
                activeFilterType = typeCodes[which]
                btnFilter.text = if (activeFilterType == null) getString(R.string.notif_filter_btn) else getString(R.string.notif_filter_on, types[which])
                applyFilterAndBind()
            }
            .show()
    }
}

class NotificationAdapter(
    private val list: List<NotificationItem>,
    private val onClick: (NotificationItem) -> Unit
) : RecyclerView.Adapter<NotificationAdapter.VH>() {

    class VH(v: View) : RecyclerView.ViewHolder(v) {
        val title: TextView = v.findViewById(R.id.tvNotifTitle)
        val date: TextView = v.findViewById(R.id.tvNotifDate)
        val body: TextView = v.findViewById(R.id.tvNotifBody)
        val unread: View = v.findViewById(R.id.vUnreadIndicator)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val v = LayoutInflater.from(parent.context).inflate(R.layout.item_notification, parent, false)
        return VH(v)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = list[position]
        holder.title.text = item.title
        holder.date.text = item.created_at
        holder.body.text = item.body

        // کنترل دیداری نشانگر اعلان‌های خوانده نشده
        if (item.is_read) {
            holder.unread.visibility = View.GONE
        } else {
            holder.unread.visibility = View.VISIBLE
        }

        holder.itemView.setOnClickListener { onClick(item) }
    }

    override fun getItemCount() = list.size
}
