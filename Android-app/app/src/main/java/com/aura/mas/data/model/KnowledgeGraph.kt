package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName

data class UserKnowledgeDomain(
    val id: Long,
    val userId: Long,
    val domainName: String,
    val graphData: GraphData? = null,
    val createdAt: String? = null,
    val updatedAt: String? = null
)

data class KnowledgeGraphNode(
    val id: String,
    val name: String,
    val description: String? = null,
    @SerializedName("resource_ids") val resourceIds: List<Long>? = null,
    @SerializedName("mastery_level") val masteryLevel: Float? = null,
    val importance: Float? = null
)

data class KnowledgeGraphEdge(
    val id: String? = null,
    val source: String,
    val target: String,
    val relationship: String? = null
)

data class GraphData(
    val nodes: List<KnowledgeGraphNode> = emptyList(),
    val edges: List<KnowledgeGraphEdge> = emptyList()
)
