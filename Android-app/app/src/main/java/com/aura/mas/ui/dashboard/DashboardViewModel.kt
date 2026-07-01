package com.aura.mas.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.*
import com.aura.mas.data.repository.AuthStore
import com.aura.mas.data.repository.StatsRepository
import com.aura.mas.data.repository.PlanRepository
import com.aura.mas.data.api.PythonApiService
import com.aura.mas.data.api.ApiService
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardUiState(
    val isLoading: Boolean = true,
    val greeting: String = "",
    val aiGreeting: String = "",
    val totalPlans: Int = 0,
    val completedPlans: Int = 0,
    val totalResources: Int = 0,
    val totalStudyHours: Double = 0.0,
    val weeklyMinutes: List<WeeklyMinute> = emptyList(),
    val recentPlans: List<LearningPlan> = emptyList(),
    val heatmapData: List<StudyHeatmapData> = emptyList(),
    val recentActivity: List<RecentActivity> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val statsRepo: StatsRepository,
    private val planRepo: PlanRepository,
    private val authStore: AuthStore,
    private val api: ApiService,
    private val pythonApi: PythonApiService
) : ViewModel() {

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()
    val currentUser = authStore.currentUser

    init { loadDashboard() }

    fun loadDashboard() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                // 1. Fetch dashboard stats from Java backend
                val statsResult = statsRepo.getDashboardStats()
                val stats = statsResult.data

                // 2. Fetch plans list for progress calculation
                val plansResult = api.getPlans(size = 50)
                val plans = plansResult.data?.records ?: emptyList()

                // 3. Calculate progress for each plan
                val plansWithProgress = plans.map { plan ->
                    try {
                        val resResult = api.getResourcesByPlan(plan.id)
                        val progResult = planRepo.getProgress(plan.id)
                        val resources = resResult.data ?: emptyList()
                        val progress = progResult.data ?: emptyList()
                        val validIds = resources.filter { it.status >= LearningResource.STATUS_READY }.map { it.id }.toSet()
                        val completed = progress.count { it.completed && it.resourceId in validIds }
                        val total = validIds.size
                        val pct = if (total > 0) (completed * 100.0 / total).coerceIn(0.0, 100.0) else 0.0
                        plan.copy(progress = pct / 100.0)
                    } catch (_: Exception) { plan }
                }

                // 4. Fetch heatmap
                val heatmapResult = statsRepo.getStudyHeatmap()

                _uiState.value = DashboardUiState(
                    isLoading = false,
                    greeting = buildGreeting(),
                    totalPlans = stats?.totalPlans?.toInt() ?: plans.size,
                    completedPlans = stats?.completedPlans?.toInt() ?: plans.count { it.status == LearningPlan.STATUS_COMPLETED },
                    totalResources = stats?.totalResources?.toInt() ?: 0,
                    totalStudyHours = stats?.totalStudyHours ?: 0.0,
                    weeklyMinutes = stats?.weeklyMinutes ?: emptyList(),
                    recentPlans = plansWithProgress.take(10),
                    heatmapData = heatmapResult.data?.dailyData ?: emptyList(),
                    recentActivity = stats?.recentActivity ?: emptyList()
                )

                // 5. Fetch AI greeting (async, non-blocking)
                loadAiGreeting()

            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    greeting = buildGreeting(),
                    error = e.message
                )
            }
        }
    }

    private fun loadAiGreeting() {
        viewModelScope.launch {
            try {
                val ticket = api.issueTicket().data ?: return@launch
                val response = pythonApi.getGreeting(ticket)
                val json = com.google.gson.Gson().fromJson(response.string(), com.google.gson.JsonObject::class.java)
                val greeting = json?.get("greeting")?.asString
                if (!greeting.isNullOrBlank()) {
                    _uiState.value = _uiState.value.copy(aiGreeting = greeting)
                }
            } catch (_: Exception) {}
        }
    }

    private fun buildGreeting(): String {
        val hour = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
        val name = authStore.currentUser.value?.nickname ?: "同学"
        return when {
            hour < 6 -> "夜深了，$name"
            hour < 12 -> "早上好，$name"
            hour < 14 -> "中午好，$name"
            hour < 18 -> "下午好，$name"
            else -> "晚上好，$name"
        }
    }
}
