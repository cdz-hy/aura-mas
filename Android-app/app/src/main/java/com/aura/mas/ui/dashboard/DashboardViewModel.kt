package com.aura.mas.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.*
import com.aura.mas.data.repository.AuthStore
import com.aura.mas.data.repository.StatsRepository
import com.aura.mas.data.repository.PlanRepository
import com.aura.mas.data.api.PythonApiService
import com.aura.mas.data.api.ApiService
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
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

            // Step 2: Launch parallel requests, update UI incrementally
            val hasCache = cachedPlans.isNotEmpty()

            // 2a. Stats (update stats cards as soon as ready)
            val statsJob = async {
                try {
                    kotlinx.coroutines.withTimeout(8_000L) { statsRepo.getDashboardStats() }.data
                } catch (_: Exception) { null }
            }

            // 2b. Plans (update plan list as soon as ready)
            val plansJob = async {
                try {
                    val plansResult = api.getPlans(size = 50)
                    val plansList = plansResult.data?.records ?: emptyList()
                    offlineCache.cachePlans(plansList)
                    plansList
                } catch (_: Exception) { null }
            }

            // 2c. Heatmap (update heatmap independently)
            val heatmapJob = async {
                try { statsRepo.getStudyHeatmap().data?.dailyData } catch (_: Exception) { null }
            }

            // 2d. AI greeting (fire and forget)
            loadAiGreeting()

            // --- Update stats cards as soon as ready ---
            val stats = statsJob.await()
            if (stats != null) {
                _uiState.value = _uiState.value.copy(
                    totalPlans = stats.totalPlans.toInt(),
                    completedPlans = stats.completedPlans.toInt(),
                    totalResources = stats.totalResources,
                    totalStudyHours = stats.totalStudyHours,
                    weeklyMinutes = stats.weeklyMinutes,
                    recentActivity = stats.recentActivity
                )
            }

            // --- Update plan list as soon as ready ---
            val freshPlans = plansJob.await()
            if (freshPlans != null) {
                _uiState.value = _uiState.value.copy(
                    recentPlans = freshPlans.take(10),
                    totalPlans = freshPlans.size,
                    completedPlans = freshPlans.count { it.status == LearningPlan.STATUS_COMPLETED },
                    isLoading = false
                )

                // Fetch progress in background (doesn't block UI)
                val planIds = freshPlans.map { it.id }
                if (planIds.isNotEmpty()) {
                    launch {
                        try {
                            val progressMap = api.getBatchProgress(planIds).data ?: emptyMap()
                            val plansWithProgress = freshPlans.map { plan ->
                                val summary = progressMap[plan.id.toString()]
                                plan.copy(progress = summary?.progress?.toDouble() ?: 0.0)
                            }
                            _uiState.value = _uiState.value.copy(recentPlans = plansWithProgress.take(10))
                        } catch (_: Exception) {}
                    }
                }

                // Cache resources in background (doesn't block UI)
                launch {
                    freshPlans.forEach { plan ->
                        try {
                            val res = api.getResourcesByPlan(plan.id)
                            if (res.isSuccess && res.data != null) {
                                offlineCache.cacheResources(res.data)
                            }
                        } catch (_: Exception) {}
                    }
                }
            }

            // --- Update heatmap as soon as ready ---
            val heatmapData = heatmapJob.await()
            if (heatmapData != null) {
                _uiState.value = _uiState.value.copy(heatmapData = heatmapData)
            }

            // Done refreshing
            _uiState.value = _uiState.value.copy(isRefreshing = false)

            // Fallback: if no cache and all requests failed
            if (!hasCache && freshPlans == null && stats == null) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "网络连接失败，请检查网络设置"
                )
            }
        }
    }

    private fun loadAiGreeting() {
        viewModelScope.launch {
            try {
                val userId = authStore.currentUser.value?.id ?: return@launch
                val response = pythonApi.getGreeting(userId)
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

    fun markAllComplete(planId: Long) {
        viewModelScope.launch {
            try {
                api.markAllComplete(planId)
                loadDashboard()
            } catch (_: Exception) {}
        }
    }
}
