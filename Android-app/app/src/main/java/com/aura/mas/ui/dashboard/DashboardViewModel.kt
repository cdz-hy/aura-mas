package com.aura.mas.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.*
import com.aura.mas.data.repository.AuthStore
import com.aura.mas.data.repository.StatsRepository
import com.aura.mas.data.repository.PlanRepository
import com.aura.mas.data.api.PythonApiService
import com.aura.mas.data.api.ApiService
import com.aura.mas.data.offline.OfflineCacheManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
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
    private val pythonApi: PythonApiService,
    private val offlineCache: OfflineCacheManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()
    val currentUser = authStore.currentUser

    private var retryJob: kotlinx.coroutines.Job? = null

    init { loadDashboard() }

    fun loadDashboard() {
        retryJob?.cancel()
        loadDashboardInternal()
    }

    private fun loadDashboardInternal() {
        viewModelScope.launch {
            // Step 1: Show cached data immediately
            val cachedPlans = offlineCache.getCachedPlans().sortedByDescending { it.id }
            if (cachedPlans.isNotEmpty()) {
                _uiState.value = DashboardUiState(
                    isLoading = false,
                    isRefreshing = true,
                    greeting = buildGreeting(),
                    recentPlans = cachedPlans.take(10),
                    totalPlans = cachedPlans.size,
                    completedPlans = cachedPlans.count { it.status == LearningPlan.STATUS_COMPLETED }
                )
            } else {
                _uiState.value = DashboardUiState(isLoading = true)
            }

            // Step 2: Fetch fresh data in background
            try {
                val statsResult = kotlinx.coroutines.withTimeout(15_000L) {
                    statsRepo.getDashboardStats()
                }
                val stats = statsResult.data

                val plansResult = api.getPlans(size = 50)
                val plans = plansResult.data?.records ?: emptyList()

                // Cache plans
                offlineCache.cachePlans(plans)

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

                // Cache resources for each plan
                plans.forEach { plan ->
                    try {
                        val res = api.getResourcesByPlan(plan.id)
                        if (res.isSuccess && res.data != null) {
                            offlineCache.cacheResources(res.data)
                        }
                    } catch (_: Exception) {}
                }

                val heatmapResult = statsRepo.getStudyHeatmap()

                _uiState.value = DashboardUiState(
                    isLoading = false,
                    isRefreshing = false,
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

                loadAiGreeting()
            } catch (e: Exception) {
                // Silent fail - cached data is already shown
                _uiState.value = _uiState.value.copy(isRefreshing = false)
                // Schedule retry if we have cached data (user is seeing stale data)
                if (cachedPlans.isNotEmpty()) {
                    retryJob = viewModelScope.launch {
                        kotlinx.coroutines.delay(30_000L) // Retry after 30 seconds
                        loadDashboardInternal()
                    }
                }
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
