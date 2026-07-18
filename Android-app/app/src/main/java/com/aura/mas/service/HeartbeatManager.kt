package com.aura.mas.service

import com.aura.mas.data.api.ApiService
import kotlinx.coroutines.*
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Tracks learning time per resource via periodic heartbeats.
 * Sends elapsedSeconds based on real wall-clock time, not hardcoded values.
 * Flushes accumulated time when switching resources or stopping.
 */
@Singleton
class HeartbeatManager @Inject constructor(
    private val api: ApiService
) {
    private var heartbeatJob: Job? = null
    private var currentPlanId: Long = 0
    private var currentResourceId: Long = 0
    private var lastTickTime: Long = 0L
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    companion object {
        private const val HEARTBEAT_INTERVAL_MS = 30_000L
        private const val MAX_ELAPSED_SECONDS = 60  // sanity guard: ignore gaps > 60s (app backgrounded)
    }

    /**
     * Start tracking time for a resource. If already tracking a different resource,
     * flushes the accumulated time for the old resource first.
     */
    fun startTracking(planId: Long, resourceId: Long) {
        if (currentPlanId == planId && currentResourceId == resourceId && heartbeatJob?.isActive == true) {
            return  // already tracking this resource
        }
        // Flush time for previous resource before switching
        flushAndStop()
        currentPlanId = planId
        currentResourceId = resourceId
        lastTickTime = System.currentTimeMillis()
        heartbeatJob = scope.launch {
            while (isActive) {
                delay(HEARTBEAT_INTERVAL_MS)
                if (!isActive) break
                val elapsed = tickElapsedSeconds()
                if (elapsed > 0) {
                    try {
                        api.heartbeat(currentPlanId, currentResourceId, elapsed)
                    } catch (_: Exception) {}
                }
            }
        }
    }

    /**
     * Stop tracking and flush any remaining accumulated time.
     */
    fun flushAndStop() {
        heartbeatJob?.cancel()
        heartbeatJob = null
        if (currentPlanId > 0 && currentResourceId > 0 && lastTickTime > 0) {
            val elapsed = tickElapsedSeconds()
            if (elapsed > 0) {
                try {
                    // Synchronous flush on calling thread (usually main/IO)
                    kotlinx.coroutines.runBlocking {
                        api.heartbeat(currentPlanId, currentResourceId, elapsed)
                    }
                } catch (_: Exception) {}
            }
        }
        currentPlanId = 0
        currentResourceId = 0
        lastTickTime = 0L
    }

    /**
     * Update the resource being tracked without flushing (for mid-session updates).
     */
    fun updateResource(planId: Long, resourceId: Long) {
        if (currentResourceId != resourceId) {
            // Different resource - flush old one and start new
            startTracking(planId, resourceId)
        }
    }

    fun isTracking(): Boolean = heartbeatJob?.isActive == true

    private fun tickElapsedSeconds(): Int {
        val now = System.currentTimeMillis()
        val elapsed = ((now - lastTickTime) / 1000).toInt()
        lastTickTime = now
        // Sanity guard: if app was backgrounded, elapsed could be very large
        return if (elapsed in 1..MAX_ELAPSED_SECONDS) elapsed else 0
    }
}
