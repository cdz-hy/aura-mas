package com.aura.mas.data.api

import okhttp3.ResponseBody
import retrofit2.http.*

interface PythonApiService {

    @GET("/api/ai/chat")
    suspend fun chat(
        @Query("session_id") sessionId: String,
        @Query("message") message: String,
        @Query("plan_id") planId: Long? = null,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/resource/generate")
    suspend fun generateResource(
        @Query("plan_id") planId: Long,
        @Query("module_order") moduleOrder: Int,
        @Query("resource_type") resourceType: String,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/profile/chat")
    suspend fun profileChat(
        @Query("session_id") sessionId: String,
        @Query("message") message: String,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/plan/generate")
    suspend fun generatePlan(
        @Query("session_id") sessionId: String,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/flashcard/generate")
    suspend fun generateFlashcards(
        @Query("note_id") noteId: Long,
        @Query("ticket") ticket: String
    ): ResponseBody

    @POST("/api/ai/note/format")
    suspend fun formatNote(
        @Query("content") content: String,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/tutor/chat")
    suspend fun tutorChat(
        @Query("session_id") sessionId: String,
        @Query("message") message: String,
        @Query("plan_id") planId: Long? = null,
        @Query("resource_id") resourceId: Long? = null,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/tree/plan/{planId}/bootstrap")
    suspend fun bootstrapTree(
        @Path("planId") planId: Long,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/tree/plan/{planId}/grow-children")
    suspend fun growChildren(
        @Path("planId") planId: Long,
        @Query("node_id") nodeId: Long,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/tree/{treeId}/nodes/{nodeId}/explain")
    suspend fun explainNode(
        @Path("treeId") treeId: Long,
        @Path("nodeId") nodeId: Long,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/tree/{treeId}/nodes/{nodeId}/subdivide")
    suspend fun subdivideNode(
        @Path("treeId") treeId: Long,
        @Path("nodeId") nodeId: Long,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/tree/{treeId}/nodes/{nodeId}/quiz")
    suspend fun generateNodeQuiz(
        @Path("treeId") treeId: Long,
        @Path("nodeId") nodeId: Long,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/tree/{treeId}/nodes/{nodeId}/flashcards")
    suspend fun generateNodeFlashcards(
        @Path("treeId") treeId: Long,
        @Path("nodeId") nodeId: Long,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/quiz/submit")
    suspend fun submitQuiz(
        @Query("resource_id") resourceId: Long,
        @Query("answers") answers: String,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/analytics/greeting")
    suspend fun getGreeting(@Query("ticket") ticket: String): ResponseBody

    @POST("/api/analytics/plan-icon")
    suspend fun generatePlanIcon(
        @Body request: Map<String, @JvmSuppressWildcards Any>,
        @Query("ticket") ticket: String
    ): ResponseBody

    // ── Stream Control ────────────────────────────────────────
    @GET("/api/ai/stream-state")
    suspend fun getStreamState(
        @Query("session_id") sessionId: String,
        @Query("ticket") ticket: String
    ): ResponseBody

    @POST("/api/ai/stop")
    suspend fun stopGeneration(
        @Query("session_id") sessionId: String,
        @Query("ticket") ticket: String
    ): ResponseBody

    // ── Knowledge Tree Extended ───────────────────────────────
    @GET("/api/ai/tree/{treeId}/nodes/{nodeId}/multi-angle-subdivide")
    suspend fun multiAngleSubdivide(
        @Path("treeId") treeId: Long,
        @Path("nodeId") nodeId: Long,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/tree/{treeId}/nodes/{nodeId}/first-principles")
    suspend fun firstPrinciples(
        @Path("treeId") treeId: Long,
        @Path("nodeId") nodeId: Long,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/tree/{treeId}/nodes/{nodeId}/subdivision-options")
    suspend fun getSubdivisionOptions(
        @Path("treeId") treeId: Long,
        @Path("nodeId") nodeId: Long,
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/ai/tree/plan/{planId}/preview-topics")
    suspend fun previewTopics(
        @Path("planId") planId: Long,
        @Query("ticket") ticket: String
    ): ResponseBody

    // ── Knowledge Graph ───────────────────────────────────────
    @POST("/api/ai/knowledge-graph/analyze")
    suspend fun analyzeKnowledgeGraph(
        @Query("ticket") ticket: String
    ): ResponseBody

    // ── Templates ─────────────────────────────────────────────
    @GET("/api/ai/templates")
    suspend fun getTemplates(@Query("ticket") ticket: String): ResponseBody

    // ── Knowledge Base ────────────────────────────────────────
    @POST("/api/v1/kb/ingest")
    suspend fun ingestKB(
        @Query("ticket") ticket: String
    ): ResponseBody

    @GET("/api/v1/kb/collections/{name}/stats")
    suspend fun getCollectionStats(
        @Path("name") collectionName: String,
        @Query("ticket") ticket: String
    ): ResponseBody

    // ── RAG ───────────────────────────────────────────────────
    @POST("/api/v1/query/search")
    suspend fun ragSearch(
        @Query("query") query: String,
        @Query("ticket") ticket: String
    ): ResponseBody

    @POST("/api/v1/query/chat")
    suspend fun ragChat(
        @Query("query") query: String,
        @Query("ticket") ticket: String
    ): ResponseBody
}
