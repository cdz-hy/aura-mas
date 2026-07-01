package com.aura.mas.service

import com.aura.mas.data.api.ApiService
import kotlinx.coroutines.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class HeartbeatManager @Inject constructor(
    private val api: ApiService
) {
    private var heartbeatJob: Job? = null
    private var currentPlanId: Long = 0
    private var currentResourceId: Long = 0
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    fun startTracking(planId: Long, resourceId: Long = 0) {
        stopTracking()
        currentPlanId = planId
        currentResourceId = resourceId
        heartbeatJob = scope.launch {
            while (isActive) {
                try {
                    api.heartbeat(currentPlanId, currentResourceId, 30)
                } catch (_: Exception) {}
                delay(30_000L)
            }
        }
    }

    fun stopTracking() {
        heartbeatJob?.cancel()
        heartbeatJob = null
        currentPlanId = 0
        currentResourceId = 0
    }

    fun updateResource(resourceId: Long) {
        currentResourceId = resourceId
    }
}
