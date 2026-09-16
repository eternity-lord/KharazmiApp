package com.example.kharazmiadmin

import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.card.MaterialCardView

class TimelineAdapter(
    private var items: List<TimelineEvent>
) : RecyclerView.Adapter<TimelineAdapter.VH>() {

    inner class VH(view: View) : RecyclerView.ViewHolder(view) {
        val tvIcon: TextView = view.findViewById(R.id.tvTimelineIcon)
        val cardIcon: MaterialCardView = view.findViewById(R.id.cardTimelineIcon)
        val tvTitle: TextView = view.findViewById(R.id.tvTimelineTitle)
        val tvSubtitle: TextView = view.findViewById(R.id.tvTimelineSubtitle)
        val tvDate: TextView = view.findViewById(R.id.tvTimelineDate)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val v = LayoutInflater.from(parent.context).inflate(R.layout.item_timeline_event, parent, false)
        return VH(v)
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val ev = items[position]
        holder.tvTitle.text = ev.title
        holder.tvSubtitle.text = ev.subtitle
        holder.tvDate.text = ev.timestamp

        // Icon & color based on type
        val color = try {
            Color.parseColor(ev.colorHex)
        } catch (_: Exception) {
            when (ev.type) {
                "payment" -> Color.parseColor("#4CAF50")
                "absence" -> Color.parseColor("#F44336")
                "grade" -> Color.parseColor("#2196F3")
                "installment" -> Color.parseColor("#FF9800")
                else -> Color.parseColor("#757575")
            }
        }
        holder.cardIcon.setCardBackgroundColor(color)

        val iconText = when (ev.type) {
            "payment" -> "💰"
            "absence" -> "❌"
            "grade" -> "📝"
            "installment" -> if (ev.colorHex == "#4CAF50") "✅" else if (ev.colorHex == "#F44336") "🔴" else "⏳"
            else -> when (ev.iconName) {
                "ic_payment" -> "💰"
                "ic_absent" -> "❌"
                "ic_grade" -> "📝"
                "ic_installment" -> "💳"
                "ic_paid" -> "✅"
                "ic_overdue" -> "🔴"
                else -> "📌"
            }
        }
        holder.tvIcon.text = iconText
        holder.tvTitle.setTextColor(color)
    }

    fun update(newList: List<TimelineEvent>) {
        items = newList
        notifyDataSetChanged()
    }
}
