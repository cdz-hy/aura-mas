package com.aura.mas.data.repository

import com.aura.mas.data.api.ApiService
import com.aura.mas.data.api.PythonApiService
import com.aura.mas.data.model.*
import com.aura.mas.util.SseClient
import com.aura.mas.util.SseEvent
import kotlinx.coroutines.flow.Flow
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChatRepository @Inject constructor(
    private val api: ApiService,
    private val pythonApi: PythonApiService,
    private val sseClient: SseClient,
    private val authStore: AuthStore
) {
    /**
     * Load AI assistant sessions for a plan.
     * Filters OUT tutor sessions (intentType='chat' or sessionId starts with 'tutor-').
     */
    suspend fun loadChatSessions(planId: Long): List<ChatSession> {
        val response = api.getChatSessions(intentType = null, planId = planId)
        val allSessions = response.data ?: emptyList()
        return allSessions.filter { s ->
            s.intentType != "chat" && !s.sessionId.startsWith("tutor-")
        }
    }

    /**
     * Load tutor sessions for a plan.
     * Filters to keep only sessions with sessionId starting with 'tutor-{planId}-'.
     */
    suspend fun loadTutorSessions(planId: Long): List<ChatSession> {
        val response = api.getChatSessions(intentType = "chat", planId = planId)
        val allSessions = response.data ?: emptyList()
        val prefix = "tutor-$planId-"
        return allSessions.filter { s ->
            s.sessionId.startsWith(prefix)
        }
    }

    /**
     * Load standalone tutor sessions (not bound to a specific plan).
     */
    suspend fun loadStandaloneTutorSessions(): List<ChatSession> {
        val response = api.getChatSessions(intentType = "chat", planId = null)
        val allSessions = response.data ?: emptyList()
        val userId = authStore.currentUser.value?.id ?: 0
        val prefix = "tutor-0-"
        return allSessions.filter { s ->
            s.sessionId.startsWith(prefix)
        }
    }

    suspend fun getMessages(sessionId: String) = api.getSessionMessages(sessionId)
    suspend fun deleteSession(sessionId: String) = api.deleteSession(sessionId)
    suspend fun getHistory(planId: Long) = api.getDialogueHistory(planId)

    /**
     * Generate a chat session ID (random UUID).
     */
    fun generateChatSessionId(): String {
        return UUID.randomUUID().toString()
    }

    /**
     * Generate a tutor session ID with the tutor prefix pattern.
     * Pattern: tutor-{planId}-{userId}-{12-char-random}
     */
    fun generateTutorSessionId(planId: Long): String {
        val userId = authStore.currentUser.value?.id ?: 0
        val rand = UUID.randomUUID().toString().replace("-", "").take(12)
        return "tutor-$planId-$userId-$rand".take(36)
    }

    /**
     * Send a message via AI assistant chat (SSE to /api/ai/chat).
     */
    suspend fun chat(
        sessionId: String,
        message: String,
        planId: Long? = null,
        extraParams: Map<String, String>? = null
    ): Flow<SseEvent> {
        val ticket = api.issueTicket().data ?: throw Exception("Failed to get ticket")
        val baseUrl = com.aura.mas.util.Constants.PYTHON_BASE_URL
        val url = buildString {
            append("$baseUrl/api/ai/chat?")
            append("session_id=$sessionId")
            append("&message=${java.net.URLEncoder.encode(message, "UTF-8")}")
            planId?.let { append("&plan_id=$it") }
            append("&ticket=$ticket")
            extraParams?.forEach { (k, v) ->
                append("&$k=${java.net.URLEncoder.encode(v, "UTF-8")}")
            }
        }
        return sseClient.connect(url)
    }

    /**
     * Send a message via tutor chat (SSE to /api/ai/tutor/chat).
     */
    suspend fun tutorChat(
        sessionId: String, message: String,
        planId: Long? = null, resourceId: Long? = null
    ): Flow<SseEvent> {
        val ticket = api.issueTicket().data ?: throw Exception("Failed to get ticket")
        val baseUrl = com.aura.mas.util.Constants.PYTHON_BASE_URL
        val url = buildString {
            append("$baseUrl/api/ai/tutor/chat?")
            append("session_id=$sessionId")
            append("&message=${java.net.URLEncoder.encode(message, "UTF-8")}")
            planId?.let { append("&plan_id=$it") }
            resourceId?.let { append("&resource_id=$it") }
            append("&ticket=$ticket")
        }
        return sseClient.connect(url)
    }

    suspend fun issueTicket() = api.issueTicket()
}
