package com.aura.mas.service

import android.app.Application
import android.util.Log
import com.aura.mas.data.api.ApiService
import com.aura.mas.data.repository.AuthStore
import kotlinx.coroutines.*
import java.util.concurrent.ConcurrentLinkedQueue

/**
 * 学习行为追踪 SDK
 * 自动采集用户学习行为，批量上报到后端
 */
class LearningTracker(
    private val application: Application,
    private val apiService: ApiService,
    private val authStore: AuthStore
) {
    private val eventQueue = ConcurrentLinkedQueue<Map<String, Any>>()
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var flushJob: Job? = null

    companion object {
        private const val TAG = "LearningTracker"
        private const val FLUSH_INTERVAL_MS = 30_000L  // 30秒批量发送
        private const val MAX_BATCH_SIZE = 50
        private const val MAX_RETRIES = 3
    }

    fun start() {
        if (flushJob?.isActive == true) return
        flushJob = scope.launch {
            while (isActive) {
                delay(FLUSH_INTERVAL_MS)
                flush()
            }
        }
        Log.i(TAG, "学习追踪已启动")
    }

    fun stop() {
        flushJob?.cancel()
        flush()
    }

    /**
     * 追踪学习事件
     */
    fun track(eventType: String, data: Map<String, Any> = emptyMap()) {
        if (!authStore.isLoggedIn.value) return

        val event = mapOf(
            "eventType" to eventType,
            "data" to (data + mapOf("timestamp" to System.currentTimeMillis()))
        )
        eventQueue.add(event)

        if (eventQueue.size >= MAX_BATCH_SIZE) {
            scope.launch { flush() }
        }
    }

    /**
     * 批量发送事件
     */
    private suspend fun flush() {
        if (eventQueue.isEmpty()) return
        if (!authStore.isLoggedIn.value) return

        val eventsToSend = mutableListOf<Map<String, Any>>()
        while (eventQueue.isNotEmpty() && eventsToSend.size < MAX_BATCH_SIZE) {
            eventQueue.poll()?.let { eventsToSend.add(it) }
        }

        if (eventsToSend.isEmpty()) return

        try {
            apiService.trackEvents(eventsToSend)
        } catch (e: Exception) {
            Log.w(TAG, "事件上报失败: ${e.message}")
            // 失败的事件放回队列（有限制）
            if (eventQueue.size < MAX_BATCH_SIZE * 2) {
                eventsToSend.forEach { eventQueue.add(it) }
            }
        }
    }

    // ── 便捷追踪方法 ──

    fun trackPageView(page: String, planId: Long? = null, resourceId: Long? = null) {
        track("page_view", buildMap {
            put("page", page)
            planId?.let { put("planId", it) }
            resourceId?.let { put("resourceId", it) }
        })
    }

    fun trackResourceView(resourceId: Long, resourceType: String, planId: Long? = null) {
        track("resource_view", buildMap {
            put("resourceId", resourceId)
            put("resourceType", resourceType)
            planId?.let { put("planId", it) }
        })
    }

    fun trackResourceComplete(resourceId: Long, resourceType: String, planId: Long? = null) {
        track("resource_complete", buildMap {
            put("resourceId", resourceId)
            put("resourceType", resourceType)
            planId?.let { put("planId", it) }
        })
    }

    fun trackQuizSubmit(resourceId: Long, score: Int, totalQuestions: Int, correctAnswers: Int, planId: Long? = null) {
        track("quiz_submit", buildMap {
            put("resourceId", resourceId)
            put("score", score)
            put("totalQuestions", totalQuestions)
            put("correctAnswers", correctAnswers)
            planId?.let { put("planId", it) }
        })
    }

    fun trackFlashcardReview(cardId: Long, quality: Int, isCorrect: Boolean) {
        track("flashcard_review", buildMap {
            put("cardId", cardId)
            put("quality", quality)
            put("isCorrect", isCorrect)
        })
    }

    fun trackAiChat(sessionId: String, messageLength: Int, planId: Long? = null) {
        track("ai_chat", buildMap {
            put("sessionId", sessionId)
            put("messageLength", messageLength)
            planId?.let { put("planId", it) }
        })
    }
}
