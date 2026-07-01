package com.aura.mas.ui.analytics

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.*
import com.aura.mas.data.repository.StatsRepository
import com.aura.mas.ui.common.*
import com.aura.mas.ui.theme.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AnalyticsUiState(
    val isLoading: Boolean = true,
    val data: AnalyticsData? = null,
    val error: String? = null
)

@HiltViewModel
class AnalyticsViewModel @Inject constructor(
    private val statsRepo: StatsRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(AnalyticsUiState())
    val uiState: StateFlow<AnalyticsUiState> = _uiState.asStateFlow()

    init { loadAnalytics() }

    fun loadAnalytics() {
        viewModelScope.launch {
            _uiState.value = AnalyticsUiState(isLoading = true)
            try {
                val result = statsRepo.getAnalytics()
                if (result.code == 0 && result.data != null) {
                    _uiState.value = AnalyticsUiState(data = result.data)
                } else {
                    _uiState.value = AnalyticsUiState(error = result.message.ifEmpty { "获取数据失败" })
                }
            } catch (e: Exception) {
                _uiState.value = AnalyticsUiState(error = e.message ?: "网络错误")
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

    if (uiState.isLoading) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    if (uiState.error != null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(Icons.Default.Warning, null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.error)
                Spacer(Modifier.height(12.dp))
                Text(uiState.error ?: "", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(12.dp))
                Button(onClick = { viewModel.loadAnalytics() }) { Text("重试") }
            }
        }
        return
    }

    val data = uiState.data
    if (data == null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            EmptyState(Icons.Default.BarChart, "暂无数据", "暂无学习分析数据")
        }
        return
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("学习分析", fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, "返回")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Quiz accuracy
        data.quizAnalysis?.let { quiz ->
            item {
                AnalyticsCard("测验表现") {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                        AnalyticsStat("总题数", "${quiz.totalQuestions}")
                        AnalyticsStat("正确数", "${quiz.correctCount}")
                        AnalyticsStat("正确率", "${(quiz.accuracy * 100).toInt()}%")
                    }
                }
            }
        }

        // Flashcard stats
        data.flashcardStats?.let { fc ->
            item {
                AnalyticsCard("闪卡复习") {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                        AnalyticsStat("总卡片", "${fc.totalCards}")
                        AnalyticsStat("今日复习", "${fc.reviewedToday}")
                        AnalyticsStat("已掌握", "${fc.masteredCount}")
                        AnalyticsStat("待复习", "${fc.dueCount}")
                    }
                }
            }
        }

        // AI interaction
        data.aiInteraction?.let { ai ->
            item {
                AnalyticsCard("AI 互动") {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                        AnalyticsStat("消息数", "${ai.totalMessages}")
                        AnalyticsStat("会话数", "${ai.totalSessions}")
                    }
                }
            }
        }

        // Week comparison
        data.weekComparison?.let { week ->
            item {
                AnalyticsCard("本周对比") {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                        AnalyticsStat("本周", "${week.thisWeekMinutes}分钟")
                        AnalyticsStat("上周", "${week.lastWeekMinutes}分钟")
                        val change = if (week.changePercent >= 0) "+${week.changePercent.toInt()}%" else "${week.changePercent.toInt()}%"
                        AnalyticsStat("变化", change)
                    }
                }
            }
        }

        // Knowledge mastery
        if (data.knowledgeMastery.isNotEmpty()) {
            item {
                AnalyticsCard("知识掌握") {
                    data.knowledgeMastery.take(5).forEach { item ->
                        Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                            Text(item.topic, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
                            LinearProgressIndicator(
                                progress = { item.mastery.toFloat().coerceIn(0f, 1f) },
                                modifier = Modifier.width(100.dp),
                            )
                            Spacer(Modifier.width(8.dp))
                            Text("${(item.mastery * 100).toInt()}%", style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
            }
        }

        // Study efficiency
        if (data.studyEfficiency.isNotEmpty()) {
            item {
                AnalyticsCard("学习效率") {
                    data.studyEfficiency.take(5).forEach { item ->
                        Row(Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
                            Text("${item.hour}:00", style = MaterialTheme.typography.bodySmall, modifier = Modifier.width(40.dp))
                            LinearProgressIndicator(
                                progress = { item.efficiency.toFloat().coerceIn(0f, 1f) },
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                }
            }
        }

        // Empty state if all sections are empty
        if (data.quizAnalysis == null && data.flashcardStats == null &&
            data.aiInteraction == null && data.weekComparison == null &&
            data.knowledgeMastery.isEmpty() && data.studyEfficiency.isEmpty()) {
            item {
                EmptyState(Icons.Default.BarChart, "暂无分析数据", "完成更多学习活动后将生成分析报告")
            }
        }
    }
    }
}

@Composable
private fun AnalyticsCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(12.dp))
            content()
        }
    }
}

@Composable
private fun AnalyticsStat(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
