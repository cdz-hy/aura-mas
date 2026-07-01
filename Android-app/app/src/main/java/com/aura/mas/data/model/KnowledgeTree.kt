package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName

data class KnowledgeTree(
    val id: String = "",
    @SerializedName("planId") val planId: Long = 0,
    @SerializedName("userId") val userId: Long = 0,
    val metadata: String? = null,
    val nodes: List<KnowledgeNode> = emptyList()
)

data class KnowledgeNode(
    val id: String = "",
    @SerializedName("treeId") val treeId: String = "",
    @SerializedName("parentId") val parentId: String? = null,
    val label: String = "",
    val metadata: String? = null,
    val depth: Int = 0,
    @SerializedName("sortOrder") val sortOrder: Int = 0,
    val children: List<KnowledgeNode> = emptyList()
)

data class TreeMessage(
    val id: Long = 0,
    @SerializedName("nodeId") val nodeId: String = "",
    val role: String = "assistant",
    val content: String = "",
    @SerializedName("nextActions") val nextActions: String? = null,
    @SerializedName("searchSources") val searchSources: String? = null,
    val createdAt: String = ""
)
