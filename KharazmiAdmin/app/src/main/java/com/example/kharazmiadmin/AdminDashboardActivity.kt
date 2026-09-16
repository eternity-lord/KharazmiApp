package com.example.kharazmiadmin

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.google.android.material.button.MaterialButton
import com.google.android.material.card.MaterialCardView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.HttpException

class AdminDashboardActivity : BaseActivity() {

    private lateinit var swipeDashboard: SwipeRefreshLayout
    private lateinit var tvTitle: TextView
    private lateinit var progress: ProgressBar
    private lateinit var tvEmpty: TextView

    // KPI views
    private lateinit var tvKpiRevenueValue: TextView
    private lateinit var tvKpiRevenueSub: TextView
    private lateinit var tvKpiOverdueAmount: TextView
    private lateinit var tvKpiOverdueSub: TextView
    private lateinit var tvKpiStudentsValue: TextView
    private lateinit var tvKpiStudentsSub: TextView
    private lateinit var tvKpiAlertsValue: TextView
    private lateinit var tvKpiAlertsSub: TextView

    // Quick actions
    private lateinit var btnDunning: MaterialButton
    private lateinit var btnAudit: MaterialButton
    private lateinit var btnDebtors: MaterialButton
    private lateinit var btnRefresh: MaterialButton
    private lateinit var btnBack: MaterialButton

    // Critical list
    private lateinit var rvCritical: RecyclerView
    private lateinit var tvCriticalEmpty: TextView

    private lateinit var dashboardApi: DashboardApi
    private lateinit var dunningApi: DunningApi

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_admin_dashboard)

        initViews()
        setupApis()
        setupListeners()
        loadDashboard()
    }

    private fun initViews() {
        swipeDashboard = findViewById(R.id.swipeDashboard)
        tvTitle = findViewById(R.id.tvDashboardTitle)
        progress = findViewById(R.id.progressDashboard)
        tvEmpty = findViewById(R.id.tvDashboardEmpty)

        tvKpiRevenueValue = findViewById(R.id.tvKpiRevenueValue)
        tvKpiRevenueSub = findViewById(R.id.tvKpiRevenueSub)
        tvKpiOverdueAmount = findViewById(R.id.tvKpiOverdueAmount)
        tvKpiOverdueSub = findViewById(R.id.tvKpiOverdueSub)
        tvKpiStudentsValue = findViewById(R.id.tvKpiStudentsValue)
        tvKpiStudentsSub = findViewById(R.id.tvKpiStudentsSub)
        tvKpiAlertsValue = findViewById(R.id.tvKpiAlertsValue)
        tvKpiAlertsSub = findViewById(R.id.tvKpiAlertsSub)

        btnDunning = findViewById(R.id.btnDashboardDunning)
        btnAudit = findViewById(R.id.btnDashboardAudit)
        btnDebtors = findViewById(R.id.btnDashboardDebtors)
        btnRefresh = findViewById(R.id.btnDashboardRefresh)
        btnBack = findViewById(R.id.btnDashboardBack)

        rvCritical = findViewById(R.id.rvDashboardCritical)
        tvCriticalEmpty = findViewById(R.id.tvDashboardCriticalEmpty)

        tvTitle.text = getString(R.string.dashboard_title)
        rvCritical.layoutManager = LinearLayoutManager(this)
        rvCritical.isNestedScrollingEnabled = false

        // SwipeRefresh colors
        swipeDashboard.setColorSchemeColors(Color.parseColor("#D4A94C"))
        swipeDashboard.setProgressBackgroundColorSchemeColor(Color.parseColor("#171A21"))
    }

    private fun setupApis() {
        val retrofit = RetrofitClient.getInstance(this)
        dashboardApi = retrofit.create(DashboardApi::class.java)
        dunningApi = retrofit.create(DunningApi::class.java)
    }

    private fun setupListeners() {
        btnRefresh.setOnClickListener { loadDashboard() }
        btnBack.setOnClickListener { finish() }

        swipeDashboard.setOnRefreshListener { loadDashboard() }

        btnDunning.setOnClickListener {
            startActivity(Intent(this, DunningActivity::class.java))
        }
        btnAudit.setOnClickListener {
            startActivity(Intent(this, AuditDashboardActivity::class.java))
        }
        btnDebtors.setOnClickListener {
            Toast.makeText(this, getString(R.string.dashboard_debtors_coming_soon), Toast.LENGTH_LONG).show()
            // Optionally open ReportActivity with debtors tab if exists
            // startActivity(Intent(this, ReportActivity::class.java))
        }

        // KPI cards click to navigate for quick access
        findViewById<View>(R.id.cardKpiRevenue)?.setOnClickListener {
            Toast.makeText(this, getString(R.string.dashboard_today_revenue), Toast.LENGTH_SHORT).show()
        }
        findViewById<View>(R.id.cardKpiOverdue)?.setOnClickListener {
            startActivity(Intent(this, DunningActivity::class.java))
        }
        findViewById<View>(R.id.cardKpiStudents)?.setOnClickListener {
            startActivity(Intent(this, PersonListActivity::class.java).apply { putExtra("MODE", "STUDENT") })
        }
        findViewById<View>(R.id.cardKpiAlerts)?.setOnClickListener {
            startActivity(Intent(this, AuditDashboardActivity::class.java))
        }
    }

    private fun setLoading(isLoading: Boolean) {
        if (isLoading) {
            progress.visibility = View.VISIBLE
            tvEmpty.visibility = View.VISIBLE
            tvEmpty.text = getString(R.string.dashboard_loading)
        } else {
            progress.visibility = View.GONE
            if (!swipeDashboard.isRefreshing) {
                tvEmpty.visibility = View.GONE
            }
        }
        // Disable buttons while loading to avoid spam
        btnRefresh.isEnabled = !isLoading
        btnDunning.isEnabled = !isLoading
        btnAudit.isEnabled = !isLoading
    }

    private fun loadDashboard() {
        setLoading(true)
        tvCriticalEmpty.visibility = View.GONE

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                // Parallel requests for 2 data sources (KPI + Dunning drafts) — spec <500ms
                val (kpis, drafts) = coroutineScope {
                    val kpiDeferred = async { dashboardApi.getKPIs() }
                    val draftsDeferred = async { dunningApi.getDrafts() }
                    Pair(kpiDeferred.await(), draftsDeferred.await())
                }

                withContext(Dispatchers.Main) {
                    setLoading(false)
                    swipeDashboard.isRefreshing = false
                    tvEmpty.visibility = View.GONE

                    renderKPIs(kpis)

                    // Filter critical top 5
                    val critical = drafts.filter { it.category == "critical" }.take(5)
                    renderCritical(critical)
                }
            } catch (e: Exception) {
                if (e is kotlinx.coroutines.CancellationException) throw e
                withContext(Dispatchers.Main) {
                    setLoading(false)
                    swipeDashboard.isRefreshing = false
                    val msg = when (e) {
                        is HttpException -> when (e.code()) {
                            403 -> "⛔ دسترسی فقط برای ادمین"
                            401 -> "توکن منقضی شده — دوباره وارد شوید"
                            else -> getString(R.string.dashboard_error, "خطای سرور ${e.code()}")
                        }
                        else -> getString(R.string.dashboard_error, e.message ?: "خطا در دریافت")
                    }
                    tvEmpty.text = msg
                    tvEmpty.visibility = View.VISIBLE
                    tvCriticalEmpty.text = msg
                    tvCriticalEmpty.visibility = View.VISIBLE
                    Toast.makeText(this@AdminDashboardActivity, msg, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun renderKPIs(kpis: DashboardKPIs) {
        tvKpiRevenueValue.text = formatAmount(kpis.todayRevenue)
        tvKpiRevenueSub.text = getString(R.string.dashboard_today_revenue_sub)

        tvKpiOverdueAmount.text = formatAmount(kpis.totalOverdueAmount)
        // overdue card shows count + total
        val overdueSub = getString(R.string.dashboard_overdue_sub, kpis.overdueInstallmentsCount, formatNumber(kpis.totalOverdueAmount))
        // Add dunning pending as secondary if different
        val dunningInfo = if (kpis.dunningPendingCount != kpis.overdueInstallmentsCount) {
            "\n${getString(R.string.dashboard_dunning_pending)}: ${kpis.dunningPendingCount}"
        } else ""
        tvKpiOverdueSub.text = overdueSub + dunningInfo

        tvKpiStudentsValue.text = formatNumber(kpis.activeStudentsCount.toLong())
        tvKpiStudentsSub.text = getString(R.string.dashboard_students_sub)

        tvKpiAlertsValue.text = kpis.suspiciousAlertsCount.toString()
        // Show dunning pending as sub if needed
        tvKpiAlertsSub.text = if (kpis.dunningPendingCount > 0) {
            "${getString(R.string.dashboard_alerts_sub)} • ${getString(R.string.dashboard_dunning_pending)}: ${kpis.dunningPendingCount}"
        } else {
            getString(R.string.dashboard_alerts_sub)
        }
    }

    private fun renderCritical(list: List<DunningDraft>) {
        if (list.isEmpty()) {
            tvCriticalEmpty.text = getString(R.string.dashboard_critical_empty)
            tvCriticalEmpty.visibility = View.VISIBLE
            rvCritical.visibility = View.GONE
        } else {
            tvCriticalEmpty.visibility = View.GONE
            rvCritical.visibility = View.VISIBLE
            rvCritical.adapter = CriticalAdapter(list)
        }
    }

    private fun formatAmount(amount: Long): String {
        return try {
            String.format("%,d تومان", amount)
        } catch (_: Exception) {
            "$amount تومان"
        }
    }

    private fun formatNumber(n: Long): String {
        return try {
            String.format("%,d", n)
        } catch (_: Exception) {
            n.toString()
        }
    }

    inner class CriticalAdapter(private val items: List<DunningDraft>) :
        RecyclerView.Adapter<CriticalAdapter.VH>() {

        inner class VH(view: View) : RecyclerView.ViewHolder(view) {
            val card: MaterialCardView = view.findViewById(R.id.cardCritical)
            val tvStudentName: TextView = view.findViewById(R.id.tvCriticalStudentName)
            val tvAmount: TextView = view.findViewById(R.id.tvCriticalAmount)
            val tvCategory: TextView = view.findViewById(R.id.tvCriticalCategory)
            val tvDueDate: TextView = view.findViewById(R.id.tvCriticalDueDate)
            val tvParentMobile: TextView = view.findViewById(R.id.tvCriticalParentMobile)
            val tvSmsPreview: TextView = view.findViewById(R.id.tvCriticalSmsPreview)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
            val v = LayoutInflater.from(parent.context).inflate(R.layout.item_dashboard_critical, parent, false)
            return VH(v)
        }

        override fun getItemCount(): Int = items.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val item = items[position]
            holder.tvStudentName.text = item.studentName
            holder.tvAmount.text = formatAmount(item.amount)
            holder.tvDueDate.text = "سررسید: ${item.dueDate}"
            holder.tvParentMobile.text = "📱 ${item.parentMobile}"
            holder.tvSmsPreview.text = item.suggestedMessage

            // Category badge — critical is red, but we may get only critical here
            val label = getString(R.string.dunning_filter_critical)
            holder.tvCategory.text = "🔴 $label"
            holder.tvCategory.setBackgroundColor(Color.parseColor("#F44336"))
            holder.tvCategory.setTextColor(Color.WHITE)
            holder.card.strokeColor = Color.parseColor("#D32F2F")

            holder.card.setOnClickListener {
                // Quick open DunningActivity filtered? Just open DunningActivity
                startActivity(Intent(this@AdminDashboardActivity, DunningActivity::class.java))
            }
        }
    }
}
