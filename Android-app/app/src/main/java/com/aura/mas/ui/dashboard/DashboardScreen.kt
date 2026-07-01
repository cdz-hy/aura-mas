package com.aura.mas.ui.dashboard

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.aura.mas.data.model.*
import com.aura.mas.ui.common.*
import com.aura.mas.ui.components.SvgIcon
import com.aura.mas.ui.components.charts.StudyHeatmap
import com.aura.mas.ui.theme.*

@Composable
fun DashboardScreen(
    onPlanClick: (Long) -> Unit,
    onViewAllPlans: () -> Unit,
    viewModel: DashboardViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val user by viewModel.currentUser.collectAsState()

    if (uiState.isLoading) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        // Greeting
        item {
            GreetingHeader(
                greeting = uiState.greeting,
                aiGreeting = uiState.aiGreeting,
                avatarUrl = user?.avatarUrl,
                nickname = user?.nickname ?: "U"
            )
        }

        // Error
        if (uiState.error != null) {
            item { ErrorBanner(uiState.error!!) { viewModel.loadDashboard() } }
        }

        // Stat cards - 2x2 grid
        item {
            Spacer(Modifier.height(20.dp))
            Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                StatCard(Icons.Default.MenuBook, "学习计划", "${uiState.totalPlans}", Blue50, Blue500, Modifier.weight(1f))
                StatCard(Icons.Default.CheckCircle, "已完成", "${uiState.completedPlans}", Emerald50, Emerald500, Modifier.weight(1f))
            }
        }
        item {
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                StatCard(Icons.Default.Description, "学习资源", "${uiState.totalResources}", MaterialTheme.colorScheme.tertiaryContainer, MaterialTheme.colorScheme.tertiary, Modifier.weight(1f))
                StatCard(Icons.Default.Schedule, "学习时长", formatStudyHours(uiState.totalStudyHours), MaterialTheme.colorScheme.secondaryContainer, MaterialTheme.colorScheme.secondary, Modifier.weight(1f))
            }
        }

        // Weekly study
        if (uiState.weeklyMinutes.isNotEmpty()) {
            item {
                Spacer(Modifier.height(20.dp))
                WeeklyStudyCard(uiState.weeklyMinutes)
            }
        }

        // Heatmap
        item {
            Spacer(Modifier.height(20.dp))
            HeatmapCard(uiState.heatmapData)
        }

        // Recent activity
        if (uiState.recentActivity.isNotEmpty()) {
            item {
                Spacer(Modifier.height(20.dp))
                RecentActivityCard(uiState.recentActivity)
            }
        }

        // Recent plans - only show 3
        item {
            Spacer(Modifier.height(20.dp))
            SectionHeader("最近计划", "查看全部", onViewAllPlans)
        }
        if (uiState.recentPlans.isEmpty()) {
            item { EmptyState(Icons.Outlined.MenuBook, "暂无学习计划", "创建你的第一个学习计划吧") }
        } else {
            items(uiState.recentPlans.take(3), key = { it.id }) { plan ->
                PlanCard(plan, { onPlanClick(plan.id) }, Modifier.padding(horizontal = 20.dp, vertical = 4.dp))
            }
        }
    }
}

// ── Greeting ──────────────────────────────────────────────────

@Composable
private fun GreetingHeader(greeting: String, aiGreeting: String, avatarUrl: String?, nickname: String) {
    Box(
        Modifier.fillMaxWidth()
            .background(Brush.verticalGradient(listOf(
                MaterialTheme.colorScheme.primary,
                MaterialTheme.colorScheme.primary.copy(alpha = 0.6f),
                Color.Transparent
            )))
            .padding(start = 20.dp, end = 20.dp, top = 48.dp, bottom = 28.dp)
    ) {
        Row(Modifier.fillMaxWidth(), Arrangement.SpaceBetween, Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(greeting, style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.onPrimary)
                Spacer(Modifier.height(6.dp))
                if (aiGreeting.isNotBlank()) {
                    TypewriterText(aiGreeting, MaterialTheme.typography.bodyMedium, MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.85f))
                } else {
                    Text("继续你的学习之旅", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.85f))
                }
            }
            Spacer(Modifier.width(16.dp))
            UserAvatar(avatarUrl, nickname, 48)
        }
    }
}

// ── Typewriter ────────────────────────────────────────────────

@Composable
private fun TypewriterText(text: String, style: androidx.compose.ui.text.TextStyle, color: Color) {
    var displayed by remember(text) { mutableStateOf("") }
    var cursorVisible by remember { mutableStateOf(true) }

    LaunchedEffect(text) {
        displayed = ""
        text.forEachIndexed { i, _ ->
            displayed = text.substring(0, i + 1)
            kotlinx.coroutines.delay(50)
        }
    }
    LaunchedEffect(Unit) {
        while (true) { kotlinx.coroutines.delay(530); cursorVisible = !cursorVisible }
    }

    Row {
        Text(displayed, style = style, color = color)
        if (displayed.length < text.length) {
            Text("|", style = style, color = color.copy(alpha = if (cursorVisible) 1f else 0f))
        }
    }
}

// ── Weekly Study ──────────────────────────────────────────────

@Composable
private fun WeeklyStudyCard(data: List<WeeklyMinute>) {
    Card(
        Modifier.fillMaxWidth().padding(horizontal = 20.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(1.dp)
    ) {
        Column(Modifier.padding(16.dp)) {
            Text("本周学习", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(16.dp))

            val maxVal = data.maxOfOrNull { it.minutes }?.coerceAtLeast(1) ?: 1

            data.forEach { day ->
                Row(Modifier.fillMaxWidth().padding(vertical = 5.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(day.label.ifEmpty { "-" }, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.width(28.dp))
                    Spacer(Modifier.width(8.dp))
                    Box(Modifier.weight(1f).height(12.dp)) {
                        Box(Modifier.fillMaxSize().clip(RoundedCornerShape(6.dp)).background(MaterialTheme.colorScheme.surfaceVariant))
                        val fraction = (day.minutes.toFloat() / maxVal).coerceIn(0f, 1f)
                        if (fraction > 0f) {
                            Box(Modifier.fillMaxHeight().fillMaxWidth(fraction).clip(RoundedCornerShape(6.dp)).background(Brush.horizontalGradient(listOf(Sage300, Sage500))))
                        }
                    }
                    Spacer(Modifier.width(8.dp))
                    Text(formatMinutesShort(day.minutes), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.width(40.dp))
                }
            }
        }
    }
}

// ── Heatmap ───────────────────────────────────────────────────

@Composable
private fun HeatmapCard(data: List<StudyHeatmapData>) {
    Card(
        Modifier.fillMaxWidth().padding(horizontal = 20.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(1.dp)
    ) {
        Column(Modifier.padding(16.dp)) {
            Text("学习热力图", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(12.dp))
            StudyHeatmap(data = data, modifier = Modifier.fillMaxWidth())
        }
    }
}

// ── Recent Activity ───────────────────────────────────────────

@Composable
private fun RecentActivityCard(activities: List<RecentActivity>) {
    Card(
        Modifier.fillMaxWidth().padding(horizontal = 20.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(1.dp)
    ) {
        Column(Modifier.padding(16.dp)) {
            Text("最近活动", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(12.dp))
            activities.take(8).forEach { activity ->
                Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                    val dotColor = try { Color(android.graphics.Color.parseColor(activity.color.ifEmpty { "#6B7FAE" })) } catch (_: Exception) { MaterialTheme.colorScheme.primary }
                    Box(Modifier.size(8.dp).clip(CircleShape).background(dotColor))
                    Spacer(Modifier.width(12.dp))
                    Text(activity.text, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(activity.time, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

// ── Plan Card ─────────────────────────────────────────────────

@Composable
private fun PlanCard(plan: LearningPlan, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Card(
        modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(1.dp)
    ) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            val iconSvg = plan.getIconSvg()
            Box(
                Modifier.size(44.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(
                        if (plan.getEffectiveStatus() == LearningPlan.STATUS_COMPLETED)
                            MaterialTheme.colorScheme.secondaryContainer
                        else MaterialTheme.colorScheme.primaryContainer
                    ),
                contentAlignment = Alignment.Center
            ) {
                if (!iconSvg.isNullOrBlank()) {
                    SvgIcon(svgString = iconSvg, modifier = Modifier.size(36.dp))
                } else {
                    Icon(
                        when (plan.getEffectiveStatus()) {
                            LearningPlan.STATUS_COMPLETED -> Icons.Default.CheckCircle
                            LearningPlan.STATUS_GENERATING -> Icons.Default.Sync
                            else -> Icons.Default.MenuBook
                        }, null,
                        tint = when (plan.getEffectiveStatus()) {
                            LearningPlan.STATUS_COMPLETED -> MaterialTheme.colorScheme.secondary
                            LearningPlan.STATUS_GENERATING -> MaterialTheme.colorScheme.tertiary
                            else -> MaterialTheme.colorScheme.primary
                        },
                        modifier = Modifier.size(24.dp)
                    )
                }
            }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(plan.title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Spacer(Modifier.height(2.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(shape = RoundedCornerShape(6.dp), color = statusColor(plan).copy(alpha = 0.12f)) {
                        Text(plan.getStatusText(), Modifier.padding(horizontal = 6.dp, vertical = 2.dp), style = MaterialTheme.typography.labelSmall, color = statusColor(plan))
                    }
                    plan.createdAt?.let {
                        Spacer(Modifier.width(8.dp))
                        Text(it.take(10), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            val pct = plan.getPercentProgress()
            if (pct > 0) {
                Column(horizontalAlignment = Alignment.End) {
                    Text("$pct%", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Medium, color = MaterialTheme.colorScheme.primary)
                    Spacer(Modifier.height(4.dp))
                    LinearProgressIndicator(progress = { pct / 100f }, modifier = Modifier.width(48.dp).height(4.dp).clip(RoundedCornerShape(2.dp)), trackColor = MaterialTheme.colorScheme.surfaceVariant)
                }
            }
        }
    }
}

// ── Error Banner ──────────────────────────────────────────────

@Composable
private fun ErrorBanner(error: String, onRetry: () -> Unit) {
    Card(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 8.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer), shape = RoundedCornerShape(12.dp)) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Warning, null, tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(8.dp))
            Text(error, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onErrorContainer, modifier = Modifier.weight(1f))
            TextButton(onClick = onRetry) { Text("重试") }
        }
    }
}

// ── Helpers ───────────────────────────────────────────────────

private fun statusColor(plan: LearningPlan) = when (plan.getEffectiveStatus()) {
    LearningPlan.STATUS_COMPLETED -> Emerald500
    LearningPlan.STATUS_GENERATING -> Amber500
    LearningPlan.STATUS_LEARNING -> Navy600
    else -> Navy400
}

private fun formatStudyHours(hours: Double): String {
    return when {
        hours >= 1.0 -> "${"%.0f".format(hours)}h"
        hours > 0.0 -> "${"%.1f".format(hours)}h"
        else -> "0h"
    }
}

private fun formatMinutesShort(minutes: Int): String {
    return when {
        minutes >= 60 -> "${minutes / 60}h${minutes % 60}m"
        minutes > 0 -> "${minutes}m"
        else -> "0"
    }
}
