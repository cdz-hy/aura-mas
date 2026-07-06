package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName

data class ChatSession(
    @SerializedName("sessionId") val sessionId: String = "",
    @SerializedName("intentType") val intentType: String = "",
    @SerializedName("planId") val planId: Long? = null,
    val title: String = "",
    @SerializedName("lastMessage") val lastMessage: String = "",
    @SerializedName(value = "lastMessageAt", alternate = ["updatedAt"]) val updatedAt: String = ""
)

data class ChatMessage(
    val id: Long = 0,
    @SerializedName("sessionId") val sessionId: String = "",
    @SerializedName(value = "dialogueType", alternate = ["role"]) val role: String = "user",
    @SerializedName(value = "conversationText", alternate = ["content"]) val content: String = "",
    @SerializedName("resourceId") val resourceId: Long? = null,
    @SerializedName(value = "dialogueTime", alternate = ["createdAt"]) val createdAt: String = "",
    @SerializedName("intentType") val intentType: String? = null,
    @SerializedName("conversationContext") val conversationContext: String? = null,
    
    // Enhanced fields for rich message types
    val type: String = "", // "confirm", "resource_generated", "modules"
    val confirmationType: String = "", // "task_breakdown" | "kb_check"
    val thinkings: List<ThinkingStep> = emptyList(),
    val searchSources: List<com.aura.mas.ui.chat.SearchSource> = emptyList(),
    val breakdown: TaskBreakdown? = null, // Task breakdown for confirmation
    val resources: List<GeneratedResourceRef> = emptyList()
) {
    companion object {
        const val ROLE_USER = "user"
        const val ROLE_ASSISTANT = "assistant"
        const val ROLE_SYSTEM = "system"
    }

    fun normalize(): ChatMessage {
        val normRole = if (role.equals("USER", ignoreCase = true) || role.equals("user", ignoreCase = true)) "user" else "assistant"
        
        var thinkingsParsed = thinkings
        if (!conversationContext.isNullOrBlank()) {
            try {
                val ctx = com.google.gson.Gson().fromJson(conversationContext.trim(), com.google.gson.JsonObject::class.java)
                if (ctx.has("thinkings")) {
                    val array = ctx.getAsJsonArray("thinkings")
                    thinkingsParsed = com.google.gson.Gson().fromJson(array, object : com.google.gson.reflect.TypeToken<List<ThinkingStep>>() {}.type)
                }
            } catch (_: Exception) {}
        }

        if (intentType == "task_breakdown") {
            val parsedBreakdown = try {
                com.google.gson.Gson().fromJson(content.trim(), TaskBreakdown::class.java)
            } catch (_: Exception) { null }
            return copy(
                role = normRole,
                type = "confirm",
                confirmationType = "task_breakdown",
                thinkings = thinkingsParsed,
                content = "学习路径已生成，请确认",
                breakdown = parsedBreakdown
            )
        }
        if (intentType == "kb_check") {
            return copy(
                role = normRole,
                type = "confirm",
                confirmationType = "kb_check",
                thinkings = thinkingsParsed,
                content = content.ifBlank { "知识库中暂无相关资料，是否继续生成？" },
                breakdown = null
            )
        }
        if (intentType == "resource_generated") {
            try {
                val data = com.google.gson.Gson().fromJson(content.trim(), com.google.gson.JsonObject::class.java)
                val summary = data.get("summary")?.asString ?: "学习资源已生成"
                val resArray = data.getAsJsonArray("resources")
                val resList = if (resArray != null) {
                    com.google.gson.Gson().fromJson<List<GeneratedResourceRef>>(resArray, object : com.google.gson.reflect.TypeToken<List<GeneratedResourceRef>>() {}.type)
                } else emptyList()
                return copy(
                    role = normRole,
                    type = "resource_generated",
                    thinkings = thinkingsParsed,
                    content = summary,
                    resources = resList
                )
            } catch (_: Exception) {}
        }

        // Default: normal message
        return copy(
            role = normRole,
            thinkings = thinkingsParsed
        )
    }
}

data class ThinkingStep(
    val agent: String = "",
    val content: String = ""
)

data class GeneratedResourceRef(
    val id: Long = 0,
    val type: String = "",
    val title: String = "",
    val content: String? = null,
    val html: String? = null
)

data class TaskBreakdown(
    val modules: List<TaskModule> = emptyList()
)

data class TaskModule(
    @SerializedName("module_id") val moduleId: String? = null,
    val title: String = "",
    @SerializedName("estimated_hours") val estimatedHours: Float? = null,
    val description: String? = null,
    val resources: List<TaskResource> = emptyList()
)

data class TaskResource(
    @SerializedName("resource_type") val resourceType: String = ""
)
