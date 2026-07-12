package com.aura.mas.ui.analytics

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import androidx.compose.ui.graphics.vector.ImageVector
import kotlin.math.abs
import javax.inject.Inject

data class AnalyticsUiState(
    val isLoading: Boolean = true,
    val data: AnalyticsData? = null,
    val error: String? = null
)

private val intentLabelMap = mapOf(
    "generate_resource" to "资源生成",
    "resource_generated" to "资源已生成",
    "generate_quiz" to "题目生成",
    "generate_animation" to "动画生成",
    "generate_type_resource" to "类型资源生成",
    "grade_quiz" to "题目批改",
    "task_breakdown" to "任务分解",
    "simple_qa" to "简单问答",
    "chat" to "普通对话",
    "plan_chat" to "计划对话",
    "follow_up" to "追问",
    "ambiguous" to "意图模糊",
    "clarify" to "需求澄清",
    "plan_advisor" to "学习顾问",
    "profile" to "画像构建",
    "profile_maintenance" to "画像维护",
    "stopped" to "已停止",
    "cancel" to "取消操作",
    "animation_summarization" to "动画摘要",
)

@HiltViewModel
class AnalyticsViewModel @Inject constructor(
    private val api: com.aura.mas.data.api.ApiService
) : ViewModel() {
    private val _uiState = MutableStateFlow(AnalyticsUiState())
    val uiState: StateFlow<AnalyticsUiState> = _uiState.asStateFlow()

    init { loadAnalytics() }

    fun loadAnalytics() {
        viewModelScope.launch {
            _uiState.value = AnalyticsUiState(isLoading = true)
            try {
                val result = kotlinx.coroutines.withTimeout(15_000L) { api.getAnalytics() }
                if (result.isSuccess && result.data != null) {
                    _uiState.value = AnalyticsUiState(isLoading = false, data = result.data)
                } else {
                    _uiState.value = AnalyticsUiState(isLoading = false, error = result.message.ifEmpty { "获取数据失败" })
                }
            } catch (e: Exception) {
                _uiState.value = AnalyticsUiState(isLoading = false, error = e.message ?: "网络错误")
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalyticsScreen(
    onBack: () -> Unit,
    viewModel: AnalyticsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("学习分析", fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface
                )
            )
        }
    ) { paddingValues ->
        when {
            uiState.isLoading -> {
                Box(
                    Modifier
                        .fillMaxSize()
                        .padding(paddingValues),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }

            uiState.error != null -> {
                com.aura.mas.ui.common.ErrorState(
                    message = uiState.error ?: "加载失败",
                    onRetry = { viewModel.loadAnalytics() },
                    modifier = Modifier.padding(paddingValues)
                )
            }

            else -> {
                val data = uiState.data
                if (data == null) {
                    Box(
                        Modifier
                            .fillMaxSize()
                            .padding(paddingValues),
                        contentAlignment = Alignment.Center
                    ) {
                        Text("暂无数据", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                } else {
                    AnalyticsContent(data, paddingValues)
                }
            }
        }
    }
}

@Composable
private fun AnalyticsContent(data: AnalyticsData, paddingValues: PaddingValues) {
    val hasAnyData = data.quizAnalysis != null ||
            data.flashcardStats != null ||
            data.aiInteraction != null ||
            data.weekComparison != null ||
            data.knowledgeMastery != null ||
            data.studyEfficiency != null

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        if (!hasAnyData) {
            EmptyCard("暂无分析数据", "完成更多学习活动后将生成分析报告")
        } else {
            data.weekComparison?.let { WeekOverviewGrid(it) }
            data.knowledgeMastery?.performance?.let { LearningPerformanceCard(it) }
            data.quizAnalysis?.let { QuizAnalysisCard(it) }
            data.flashcardStats?.let { FlashcardStatsCard(it) }
            data.studyEfficiency?.let { StudyEfficiencyCard(it) }
            data.aiInteraction?.let { AiInteractionCard(it) }
        }

        Spacer(modifier = Modifier.height(32.dp))
    }
}

// ── 周对比卡片 ───────────────────────────────────────────────────

@Composable
private fun WeekOverviewGrid(week: WeekComparison) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        week.studyMinutes?.let { sm ->
            OverviewMetricCard(
                title = "学习时长",
                value = "${sm.thisWeek.toInt()}m",
                subtext = "上周 ${sm.lastWeek.toInt()}m",
                change = sm.change,
                icon = Icons.Default.Schedule,
                iconColor = Color(0xFF3B82F6),
                modifier = Modifier.weight(1f)
            )
        }
        week.quizAccuracy?.let { qa ->
            OverviewMetricCard(
                title = "答题正确率",
                value = "${qa.thisWeek.toInt()}%",
                subtext = "上周 ${qa.lastWeek.toInt()}%",
                change = qa.change,
                icon = Icons.Default.Star,
                iconColor = Color(0xFF10B981),
                modifier = Modifier.weight(1f)
            )
        }
        week.activeDays?.let { ad ->
            OverviewMetricCard(
                title = "活跃天数",
                value = "${ad.thisWeek}天",
                subtext = "上周 ${ad.lastWeek}天",
                change = if (ad.lastWeek > 0) ((ad.thisWeek - ad.lastWeek).toDouble() / ad.lastWeek * 100) else 0.0,
                icon = Icons.Default.CheckCircle,
                iconColor = Color(0xFFF59E0B),
                modifier = Modifier.weight(1f),
                showPercent = false
            )
        }
    }
}

@Composable
private fun OverviewMetricCard(
    title: String,
    value: String,
    subtext: String,
    change: Double,
    icon: ImageVector,
    iconColor: Color,
    modifier: Modifier = Modifier,
    showPercent: Boolean = true
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(
            modifier = Modifier.padding(10.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(iconColor.copy(alpha = 0.1f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(icon, contentDescription = null, tint = iconColor, modifier = Modifier.size(14.dp))
                }
                
                val changeColor = if (change >= 0) Color(0xFF10B981) else Color(0xFFEF4444)
                val changeIcon = if (change >= 0) Icons.Default.TrendingUp else Icons.Default.TrendingDown
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(changeIcon, null, tint = changeColor, modifier = Modifier.size(10.dp))
                    Spacer(Modifier.width(2.dp))
                    Text(
                        text = if (showPercent) "${abs(change).toInt()}%" else "${abs(change).toInt()}",
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        color = changeColor
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(value, fontSize = 16.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
            Spacer(Modifier.height(2.dp))
            Text(title, fontSize = 10.sp, fontWeight = FontWeight.Medium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(2.dp))
            Text(subtext, fontSize = 8.sp, color = MaterialTheme.colorScheme.outline)
        }
    }
}

// ── 测验分析卡片 ─────────────────────────────────────────────────

@Composable
private fun QuizAnalysisCard(quiz: QuizAnalysis) {
    SectionCard(title = "测验表现") {
        quiz.recentTrend?.let { trend ->
            val trendText = when (trend.direction) {
                "up" -> "上升趋势"
                "down" -> "下降趋势"
                else -> "保持稳定"
            }
            val trendColor = when (trend.direction) {
                "up" -> Color(0xFF16A34A)
                "down" -> Color(0xFFDC2626)
                else -> Color(0xFF64748B)
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    if (trend.direction == "up") Icons.Default.TrendingUp else if (trend.direction == "down") Icons.Default.TrendingDown else Icons.Default.TrendingFlat,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp),
                    tint = trendColor
                )
                Spacer(Modifier.width(6.dp))
                Text(trendText, fontSize = 13.sp, color = trendColor, fontWeight = FontWeight.Medium)
                if (trend.changePercent != 0.0) {
                    Spacer(Modifier.width(6.dp))
                    Text(
                        "近7天 ${if (trend.changePercent >= 0) "+" else ""}${trend.changePercent}%",
                        fontSize = 12.sp,
                        color = Color(0xFF94A3B8)
                    )
                }
            }
            Spacer(Modifier.height(16.dp))
        }

        // 按题型
        if (quiz.byQuestionType.isNotEmpty()) {
            Text("按题型", fontSize = 12.sp, color = Color(0xFF94A3B8), fontWeight = FontWeight.Medium)
            Spacer(Modifier.height(8.dp))
            quiz.byQuestionType.forEach { item ->
                QuizTypeRow(item.type, item.total, item.correct, item.accuracy)
                Spacer(Modifier.height(6.dp))
            }
        }

        // 按难度
        if (quiz.byDifficulty.isNotEmpty()) {
            Spacer(Modifier.height(12.dp))
            Text("按难度", fontSize = 12.sp, color = Color(0xFF94A3B8), fontWeight = FontWeight.Medium)
            Spacer(Modifier.height(8.dp))
            val diffLabels = mapOf(1 to "简单", 2 to "较易", 3 to "中等", 4 to "较难", 5 to "困难")
            quiz.byDifficulty.filter { it.total > 0 }.forEach { item ->
                QuizTypeRow(diffLabels[item.difficulty] ?: "难度${item.difficulty}", item.total, item.correct, item.accuracy)
                Spacer(Modifier.height(6.dp))
            }
        }
    }
}

@Composable
private fun QuizTypeRow(label: String, total: Int, correct: Int, accuracy: Double) {
    Row(
        Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, fontSize = 13.sp, color = Color(0xFF475569), modifier = Modifier.width(56.dp))
        LinearProgressIndicator(
            progress = { (accuracy / 100).toFloat().coerceIn(0f, 1f) },
            modifier = Modifier
                .weight(1f)
                .height(6.dp)
                .clip(CircleShape),
            color = when {
                accuracy >= 80 -> Color(0xFF22C55E)
                accuracy >= 60 -> Color(0xFFF59E0B)
                else -> Color(0xFFEF4444)
            },
            trackColor = Color(0xFFF1F5F9)
        )
        Spacer(Modifier.width(8.dp))
        Text("${accuracy.toInt()}%", fontSize = 12.sp, color = Color(0xFF64748B), modifier = Modifier.width(36.dp))
        Text("$correct/$total", fontSize = 11.sp, color = Color(0xFF94A3B8))
    }
}

// ── 闪卡统计卡片 ─────────────────────────────────────────────────

@Composable
private fun FlashcardStatsCard(fc: FlashcardStats) {
    SectionCard(title = "闪卡复习") {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            StatItem("总卡片", "${fc.totalCards}")
            StatItem("已掌握", "${fc.mastered}")
            StatItem("学习中", "${fc.learning}")
            StatItem("待复习", "${fc.dueToday}")
        }
        if (fc.newCards > 0 || fc.avgEaseFactor > 0) {
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                StatItem("新卡片", "${fc.newCards}")
                StatItem("平均因子", String.format("%.2f", fc.avgEaseFactor))
            }
        }
    }
}

// ── 学习效率卡片 ─────────────────────────────────────────────────

@Composable
private fun StudyEfficiencyCard(eff: StudyEfficiency) {
    SectionCard(title = "学习效率") {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            StatItem("最佳学习时段", "${eff.bestStudyHour}:00")
            StatItem("最佳答题时段", "${eff.bestQuizHour}:00")
        }

        val activeHours = eff.hourlyData.filter { it.studyMinutes > 0 }.sortedByDescending { it.studyMinutes }
        if (activeHours.isNotEmpty()) {
            Spacer(Modifier.height(16.dp))
            Text("活跃时段", fontSize = 12.sp, color = Color(0xFF94A3B8), fontWeight = FontWeight.Medium)
            Spacer(Modifier.height(8.dp))
            val maxMinutes = activeHours.maxOf { it.studyMinutes }.coerceAtLeast(1)
            activeHours.take(6).forEach { item ->
                HourlyBar(item.hour, item.studyMinutes, maxMinutes)
                Spacer(Modifier.height(6.dp))
            }
        }
    }
}

@Composable
private fun HourlyBar(hour: Int, minutes: Int, maxMinutes: Int) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text("${hour}:00", fontSize = 12.sp, color = Color(0xFF64748B), modifier = Modifier.width(36.dp))
        Box(
            modifier = Modifier
                .weight(1f)
                .height(8.dp)
                .clip(CircleShape)
                .background(Color(0xFFF1F5F9))
        ) {
            Box(
                modifier = Modifier
                    .fillMaxHeight()
                    .fillMaxWidth((minutes.toFloat() / maxMinutes).coerceIn(0.01f, 1f))
                    .background(Color(0xFF60A5FA))
            )
        }
        Spacer(Modifier.width(8.dp))
        Text("${minutes}分钟", fontSize = 11.sp, color = Color(0xFF94A3B8), modifier = Modifier.width(52.dp))
    }
}

// ── 知识掌握卡片 ─────────────────────────────────────────────────

@Composable
private fun LearningPerformanceCard(performance: MasteryPerformance) {
    SectionCard(title = "学习表现") {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            PerformanceMetricRow("学习速度", performance.learningSpeed, Color(0xFF3B82F6))
            PerformanceMetricRow("学习参与度", performance.engagement, Color(0xFF8B5CF6))
            PerformanceMetricRow("测验正确率", performance.quizAccuracy, Color(0xFF10B981))
            PerformanceMetricRow("计划完成率", performance.completionRate, Color(0xFFF59E0B))
        }
    }
}

@Composable
private fun PerformanceMetricRow(label: String, value: Double, color: Color) {
    val displayValue = if (value <= 1.0) value * 100 else value
    val progress = (displayValue / 100.0).toFloat().coerceIn(0f, 1f)
    
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(label, fontSize = 13.sp, color = Color(0xFF475569), fontWeight = FontWeight.Medium)
            Text("${displayValue.toInt()}%", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = color)
        }
        Spacer(Modifier.height(6.dp))
        LinearProgressIndicator(
            progress = { progress },
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp)
                .clip(CircleShape),
            color = color,
            trackColor = Color(0xFFF1F5F9)
        )
    }
}

// ── AI 互动卡片 ─────────────────────────────────────────────────

@Composable
private fun AiInteractionCard(ai: AiInteractionStats) {
    SectionCard(title = "AI 互动") {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            StatItem("总对话", "${ai.totalDialogues}")
            StatItem("平均会话", String.format("%.1f 轮", ai.avgSessionLength))
        }
        if (ai.byIntentType.isNotEmpty()) {
            Spacer(Modifier.height(16.dp))
            Text("意图分布", fontSize = 12.sp, color = Color(0xFF94A3B8), fontWeight = FontWeight.Medium)
            Spacer(Modifier.height(8.dp))
            ai.byIntentType.sortedByDescending { it.count }.take(5).forEach { item ->
                Row(
                    Modifier.fillMaxWidth().padding(vertical = 3.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(intentLabelMap[item.intent] ?: item.intent, fontSize = 13.sp, color = Color(0xFF475569), modifier = Modifier.weight(1f))
                    LinearProgressIndicator(
                        progress = { (item.percentage / 100).toFloat().coerceIn(0f, 1f) },
                        modifier = Modifier
                            .width(80.dp)
                            .height(6.dp)
                            .clip(CircleShape),
                        color = Color(0xFF8B5CF6),
                        trackColor = Color(0xFFF1F5F9)
                    )
                    Spacer(Modifier.width(8.dp))
                    Text("${item.count}", fontSize = 12.sp, color = Color(0xFF64748B), modifier = Modifier.width(32.dp))
                    Text("${item.percentage}%", fontSize = 11.sp, color = Color(0xFF94A3B8))
                }
            }
        }
    }
}

// ── 通用组件 ─────────────────────────────────────────────────────

@Composable
private fun SectionCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(Modifier.padding(20.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(16.dp))
            content()
        }
    }
}

@Composable
private fun StatItem(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun EmptyCard(title: String, subtitle: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(40.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                Icons.Default.BarChart, null,
                modifier = Modifier.size(48.dp),
                tint = Color(0xFFCBD5E1)
            )
            Spacer(Modifier.height(12.dp))
            Text(title, style = MaterialTheme.typography.titleSmall, color = Color(0xFF64748B))
            Spacer(Modifier.height(4.dp))
            Text(subtitle, fontSize = 12.sp, color = Color(0xFF94A3B8))
        }
    }
}
