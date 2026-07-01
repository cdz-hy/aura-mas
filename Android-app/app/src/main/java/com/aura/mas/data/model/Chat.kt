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
    @SerializedName(value = "dialogueTime", alternate = ["createdAt"]) val createdAt: String = ""
) {
    companion object {
        const val ROLE_USER = "user"
        const val ROLE_ASSISTANT = "assistant"
        const val ROLE_SYSTEM = "system"
    }
}
