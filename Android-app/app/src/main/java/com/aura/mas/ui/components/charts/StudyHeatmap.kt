package com.aura.mas.ui.components.charts

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.FlashOn
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aura.mas.data.model.StudyHeatmapData
import java.time.LocalDate
import java.time.format.DateTimeFormatter


@Composable
fun StudyHeatmap(
    data: List<StudyHeatmapData>,
    modifier: Modifier = Modifier
) {
    val today = LocalDate.now()
    // Show full year: 365 days
    val startDate = today.minusDays(364)

    val dataMap = remember(data) { data.associate { it.date to it } }
    val maxMinutes = remember(data) { data.maxOfOrNull { it.minutes }?.coerceAtLeast(1) ?: 1 }

    // Build weeks (Monday-indexed columns)
    val weeks = remember(startDate, today) {
        val result = mutableListOf<List<LocalDate?>>()
        var current = startDate
        val firstOffset = current.dayOfWeek.value - 1 // 0=Mon offset
        var week = MutableList<LocalDate?>(firstOffset) { null }

        while (!current.isAfter(today)) {
            week.add(current)
            if (week.size == 7) {
                result.add(week.toList())
                week = mutableListOf()
            }
            current = current.plusDays(1)
        }
        while (week.size in 1..6) week.add(null)
        if (week.isNotEmpty()) result.add(week.toList())
        result
    }

    // Month labels: group consecutive weeks by month
    val monthLabels = remember(weeks) {
        val labels = mutableListOf<Pair<String, Int>>()
        var lastMonth = -1
        var span = 0
        for (week in weeks) {
            val firstDay = week.firstOrNull { it != null }
            val month = firstDay?.monthValue ?: 0
            if (month != lastMonth && month > 0) {
                if (span > 0) labels.add(lastMonth.toString() to span)
                lastMonth = month
                span = 1
            } else {
                span++
            }
        }
        if (span > 0) labels.add(lastMonth.toString() to span)
        labels.map { (m, s) ->
            val name = when (m.toIntOrNull()) {
                1 -> "1月"; 2 -> "2月"; 3 -> "3月"; 4 -> "4月"
                5 -> "5月"; 6 -> "6月"; 7 -> "7月"; 8 -> "8月"
                9 -> "9月"; 10 -> "10月"; 11 -> "11月"; 12 -> "12月"
                else -> ""
            }
            name to s
        }
    }

    // Streak stats
    val currentStreak = remember(dataMap, today) { calcCurrentStreak(dataMap, today) }
    val longestStreak = remember(dataMap) { calcLongestStreak(dataMap) }
    val totalActiveDays = remember(data) { data.count { it.minutes > 0 } }

    // Colors
    val levelColors = listOf(
        Color(0xFFebedf0), Color(0xFF9be9a8), Color(0xFF40c463),
        Color(0xFF30a14e), Color(0xFF216e39)
    )

    // Scroll state - auto scroll to end (current date = rightmost)
    val scrollState = rememberScrollState()
    LaunchedEffect(weeks.size) {
        if (weeks.isNotEmpty()) {
            scrollState.scrollTo(scrollState.maxValue)
        }
    }

    Column(modifier = modifier) {
        // ── Stats Row ─────────────────────────────────────────
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            StatBadge(Icons.Default.FlashOn, "连续 $currentStreak 天")
            StatBadge(Icons.Default.Star, "最长 $longestStreak 天")
            StatBadge(Icons.Default.DateRange, "活跃 $totalActiveDays 天")
        }

        Spacer(Modifier.height(12.dp))

        // ── Scrollable Grid ─────────────────────────────────────
        Row {
            // Fixed day labels column (not scrolled)
            Column(Modifier.width(20.dp).padding(top = 20.dp)) {
                val dayLabels = listOf("一", "", "三", "", "五", "", "")
                dayLabels.forEachIndexed { i, label ->
                    Box(Modifier.height(14.dp), contentAlignment = Alignment.CenterStart) {
                        if (label.isNotEmpty()) {
                            Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 9.sp)
                        }
                    }
                    if (i < 6) Spacer(Modifier.height(3.dp))
                }
            }

            // Scrollable month labels + cells
            Column(modifier = Modifier.horizontalScroll(scrollState)) {
                // Month labels row
                Row {
                    monthLabels.forEach { (label, span) ->
                        val width = (span * 17 - 3).coerceAtLeast(14).dp
                        Text(
                            label,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.width(width),
                            fontSize = 9.sp
                        )
                    }
                }

                Spacer(Modifier.height(4.dp))

                // Cell columns (one per week)
                Row {
                    weeks.forEach { week ->
                        Column {
                            week.forEachIndexed { dayIdx, date ->
                                val dayData = date?.let { dataMap[it.format(DateTimeFormatter.ISO_LOCAL_DATE)] }
                                val level = computeLevel(dayData, maxMinutes)
                                val bg = if (date != null) levelColors[level] else Color.Transparent

                                Box(
                                    Modifier.size(14.dp)
                                        .clip(RoundedCornerShape(2.dp))
                                        .background(bg)
                                )
                                if (dayIdx < 6) Spacer(Modifier.height(3.dp))
                            }
                        }
                        Spacer(Modifier.width(3.dp))
                    }
                }
            }
        }

        Spacer(Modifier.height(8.dp))

        // ── Legend ─────────────────────────────────────────────
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.CenterVertically) {
            Text("少", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 9.sp)
            Spacer(Modifier.width(4.dp))
            levelColors.forEach { c ->
                Box(Modifier.size(12.dp).clip(RoundedCornerShape(2.dp)).background(c))
                Spacer(Modifier.width(2.dp))
            }
            Spacer(Modifier.width(4.dp))
            Text("多", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 9.sp)
        }
    }
}

@Composable
private fun StatBadge(icon: androidx.compose.ui.graphics.vector.ImageVector, text: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, null, modifier = Modifier.size(14.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.width(4.dp))
        Text(text, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

private fun computeLevel(dayData: StudyHeatmapData?, maxMinutes: Int): Int {
    if (dayData == null || dayData.minutes <= 0) return 0
    if (dayData.level in 1..4) return dayData.level
    return when {
        dayData.minutes >= maxMinutes * 0.75 -> 4
        dayData.minutes >= maxMinutes * 0.5 -> 3
        dayData.minutes >= maxMinutes * 0.25 -> 2
        else -> 1
    }
}

private fun calcCurrentStreak(dataMap: Map<String, StudyHeatmapData>, today: LocalDate): Int {
    var streak = 0
    var d = today
    while (true) {
        val entry = dataMap[d.format(DateTimeFormatter.ISO_LOCAL_DATE)]
        if (entry != null && entry.minutes > 0) { streak++; d = d.minusDays(1) }
        else break
    }
    return streak
}

private fun calcLongestStreak(dataMap: Map<String, StudyHeatmapData>): Int {
    val sorted = dataMap.keys.sorted()
    var longest = 0; var current = 0; var prev: LocalDate? = null
    for (key in sorted) {
        val d = LocalDate.parse(key)
        val entry = dataMap[key]
        if (entry != null && entry.minutes > 0) {
            current = if (prev != null && d.minusDays(1) == prev) current + 1 else 1
            if (current > longest) longest = current
            prev = d
        }
    }
    return longest
}
