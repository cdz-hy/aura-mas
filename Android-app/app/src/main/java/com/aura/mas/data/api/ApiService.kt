package com.aura.mas.data.api

import com.aura.mas.data.model.*
import retrofit2.http.*

interface ApiService {

    // ── Auth ──────────────────────────────────────────────────
    @POST("/api/auth/login")
    suspend fun login(@Body request: LoginRequest): ApiResponse<LoginResponse>

    @POST("/api/auth/register")
    suspend fun register(@Body request: RegisterRequest): ApiResponse<User>

    @POST("/api/ticket/issue")
    suspend fun issueTicket(): ApiResponse<String>

    // ── User ──────────────────────────────────────────────────
    @GET("/api/user/me")
    suspend fun getCurrentUser(): ApiResponse<User>

    @GET("/api/user/profile")
    suspend fun getUserProfile(): ApiResponse<StudentProfile>

    @PUT("/api/user/profile")
    suspend fun updateProfile(@Body profile: StudentProfile): ApiResponse<Unit>

    @PUT("/api/user/profile/behavior")
    suspend fun updateProfileBehavior(@Body behavior: ProfileDimensions): ApiResponse<Unit>

    @PUT("/api/user/info")
    suspend fun updateUserInfo(@Body info: Map<String, String>): ApiResponse<Unit>

    @Multipart
    @POST("/api/user/avatar")
    suspend fun uploadAvatar(@Part avatar: okhttp3.MultipartBody.Part): ApiResponse<String>

    @DELETE("/api/user/avatar")
    suspend fun clearAvatar(): ApiResponse<Unit>

    // ── Plans ─────────────────────────────────────────────────
    @GET("/api/plan/list")
    suspend fun getPlans(
        @Query("page") page: Int = 1,
        @Query("size") size: Int = 20
    ): ApiResponse<PaginatedResponse<LearningPlan>>

    @GET("/api/plan/{planId}")
    suspend fun getPlan(@Path("planId") planId: Long): ApiResponse<LearningPlan>

    @POST("/api/plan")
    suspend fun createPlan(@Body request: PlanCreateRequest): ApiResponse<LearningPlan>

    @PUT("/api/plan/{planId}")
    suspend fun updatePlan(@Path("planId") planId: Long, @Body plan: LearningPlan): ApiResponse<Unit>

    @DELETE("/api/plan/{planId}")
    suspend fun deletePlan(@Path("planId") planId: Long): ApiResponse<Unit>

    @PUT("/api/plan/{planId}/status")
    suspend fun updatePlanStatus(@Path("planId") planId: Long, @Body status: Map<String, Int>): ApiResponse<Unit>

    // ── Resources ─────────────────────────────────────────────
    @GET("/api/resource/plan/{planId}")
    suspend fun getResourcesByPlan(@Path("planId") planId: Long): ApiResponse<List<LearningResource>>

    @GET("/api/resource/{resourceId}")
    suspend fun getResource(@Path("resourceId") resourceId: Long): ApiResponse<LearningResource>

    @DELETE("/api/resource/{resourceId}")
    suspend fun deleteResource(@Path("resourceId") resourceId: Long): ApiResponse<Unit>

    @PUT("/api/resource/{resourceId}/content")
    suspend fun updateResourceContent(
        @Path("resourceId") resourceId: Long,
        @Body content: Map<String, @JvmSuppressWildcards Any>
    ): ApiResponse<Unit>

    @POST("/api/task/dispatch")
    suspend fun dispatchTask(@Body task: Map<String, Any>): ApiResponse<ResourceGenerationTask>

    @GET("/api/task/{taskId}")
    suspend fun getTaskStatus(@Path("taskId") taskId: Long): ApiResponse<ResourceGenerationTask>

    @POST("/api/task/{taskId}/retry")
    suspend fun retryTask(@Path("taskId") taskId: Long): ApiResponse<ResourceGenerationTask>

    // ── Progress ──────────────────────────────────────────────
    @POST("/api/progress/heartbeat")
    suspend fun heartbeat(
        @Query("planId") planId: Long,
        @Query("resourceId") resourceId: Long,
        @Query("elapsedSeconds") elapsedSeconds: Int
    ): ApiResponse<Unit>

    @POST("/api/progress/complete")
    suspend fun markComplete(
        @Query("planId") planId: Long,
        @Query("resourceId") resourceId: Long
    ): ApiResponse<Unit>

    @DELETE("/api/progress/complete")
    suspend fun unmarkComplete(
        @Query("planId") planId: Long,
        @Query("resourceId") resourceId: Long
    ): ApiResponse<Unit>

    @GET("/api/progress/plan")
    suspend fun getProgress(@Query("planId") planId: Long): ApiResponse<List<ResourceProgress>>

    // ── Notes ─────────────────────────────────────────────────
    @GET("/api/note/list")
    suspend fun getNotes(
        @Query("page") page: Int = 1,
        @Query("size") size: Int = 20,
        @Query("planId") planId: Long? = null,
        @Query("keyword") keyword: String? = null
    ): ApiResponse<PaginatedResponse<Note>>

    @GET("/api/note/{noteId}")
    suspend fun getNote(@Path("noteId") noteId: Long): ApiResponse<Note>

    @POST("/api/note")
    suspend fun createNote(@Body request: NoteCreateRequest): ApiResponse<Note>

    @PUT("/api/note/{noteId}")
    suspend fun updateNote(@Path("noteId") noteId: Long, @Body note: NoteCreateRequest): ApiResponse<Unit>

    @DELETE("/api/note/{noteId}")
    suspend fun deleteNote(@Path("noteId") noteId: Long): ApiResponse<Unit>

    @POST("/api/note/{noteId}/link-resource")
    suspend fun linkNoteResource(@Path("noteId") noteId: Long, @Body link: Map<String, Any>): ApiResponse<Unit>

    @GET("/api/note/{noteId}/resources")
    suspend fun getNoteResources(@Path("noteId") noteId: Long): ApiResponse<List<NoteResourceRel>>

    // ── Flashcard ─────────────────────────────────────────────
    @GET("/api/flashcard/by-note/{noteId}")
    suspend fun getFlashcardsByNote(@Path("noteId") noteId: Long): ApiResponse<List<Flashcard>>

    @GET("/api/flashcard/review")
    suspend fun getDueFlashcards(): ApiResponse<List<Flashcard>>

    @GET("/api/flashcard/review/count")
    suspend fun getDueFlashcardCount(): ApiResponse<Int>

    @PUT("/api/flashcard/{cardId}/review")
    suspend fun submitFlashcardReview(
        @Path("cardId") cardId: Long,
        @Body result: Map<String, Int>
    ): ApiResponse<Unit>

    @POST("/api/flashcard/save")
    suspend fun saveFlashcards(@Body request: FlashcardSaveRequest): ApiResponse<List<Flashcard>>

    @DELETE("/api/flashcard/{cardId}")
    suspend fun deleteFlashcard(@Path("cardId") cardId: Long): ApiResponse<Unit>

    // ── Chat / Dialogue ───────────────────────────────────────
    @GET("/api/dialogue/sessions")
    suspend fun getChatSessions(
        @Query("intentType") intentType: String? = null,
        @Query("planId") planId: Long? = null
    ): ApiResponse<List<ChatSession>>

    @GET("/api/dialogue/session/{sessionId}")
    suspend fun getSessionMessages(@Path("sessionId") sessionId: String): ApiResponse<List<ChatMessage>>

    @DELETE("/api/dialogue/session/{sessionId}")
    suspend fun deleteSession(@Path("sessionId") sessionId: String): ApiResponse<Unit>

    @GET("/api/dialogue/history")
    suspend fun getDialogueHistory(@Query("planId") planId: Long): ApiResponse<List<ChatMessage>>

    // ── Stats ─────────────────────────────────────────────────
    @GET("/api/stats/dashboard")
    suspend fun getDashboardStats(): ApiResponse<DashboardStats>

    @GET("/api/stats/study-heatmap")
    suspend fun getStudyHeatmap(): ApiResponse<HeatmapResponse>

    @GET("/api/stats/quiz-analysis")
    suspend fun getQuizAnalysis(): ApiResponse<QuizAnalysis>

    @GET("/api/stats/flashcard-stats")
    suspend fun getFlashcardStats(): ApiResponse<FlashcardStats>

    @GET("/api/stats/ai-interaction")
    suspend fun getAiInteractionStats(): ApiResponse<AiInteractionStats>

    @GET("/api/stats/knowledge-mastery")
    suspend fun getKnowledgeMastery(): ApiResponse<KnowledgeMastery>

    @GET("/api/stats/analytics")
    suspend fun getAnalytics(): ApiResponse<AnalyticsData>

    @GET("/api/stats/study-efficiency")
    suspend fun getStudyEfficiency(): ApiResponse<StudyEfficiency>

    @GET("/api/stats/week-comparison")
    suspend fun getWeekComparison(): ApiResponse<WeekComparison>

    // ── Knowledge Tree ────────────────────────────────────────
    @POST("/api/knowledge-tree/plan/{planId}")
    suspend fun ensureKnowledgeTree(@Path("planId") planId: Long): ApiResponse<KnowledgeTree>

    @GET("/api/knowledge-tree/{treeId}")
    suspend fun getKnowledgeTree(@Path("treeId") treeId: String): ApiResponse<KnowledgeTree>

    @PATCH("/api/knowledge-tree/nodes/{nodeId}")
    suspend fun updateTreeNode(@Path("nodeId") nodeId: String, @Body data: Map<String, Any>): ApiResponse<Unit>

    @DELETE("/api/knowledge-tree/nodes/{nodeId}")
    suspend fun deleteTreeNode(@Path("nodeId") nodeId: String): ApiResponse<Unit>

    @GET("/api/knowledge-tree/nodes/{nodeId}/messages")
    suspend fun getTreeNodeMessages(@Path("nodeId") nodeId: String): ApiResponse<List<TreeMessage>>

    // ── Knowledge Graph ───────────────────────────────────────
    @GET("/api/knowledge-graph/user/{userId}")
    suspend fun getKnowledgeDomains(@Path("userId") userId: Long): ApiResponse<List<Any>>

    // ── Quiz Records ──────────────────────────────────────────
    @GET("/api/quiz/internal/user/{userId}")
    suspend fun getQuizRecords(@Path("userId") userId: Long): ApiResponse<List<QuizRecord>>

    // ── Admin ─────────────────────────────────────────────────
    @GET("/api/admin/dashboard/stats")
    suspend fun getAdminStats(): ApiResponse<AdminStats>

    @GET("/api/admin/users")
    suspend fun getAdminUsers(
        @Query("page") page: Int = 1,
        @Query("size") size: Int = 20,
        @Query("keyword") keyword: String? = null
    ): ApiResponse<PaginatedResponse<User>>

    @PUT("/api/admin/users/{id}/status")
    suspend fun toggleUserStatus(@Path("id") userId: Long, @Body status: Map<String, Int>): ApiResponse<Unit>

    @GET("/api/admin/dashboard/logs/page")
    suspend fun getLogs(
        @Query("page") page: Int = 1,
        @Query("size") size: Int = 20
    ): ApiResponse<PaginatedResponse<SystemLog>>

    @GET("/api/admin/dashboard/logs/stats")
    suspend fun getLogStats(): ApiResponse<Any>

    @GET("/api/admin/dashboard/logs/trend")
    suspend fun getLogTrend(): ApiResponse<Any>

    @GET("/api/admin/dashboard/logs/hourly")
    suspend fun getLogHourly(): ApiResponse<Any>

    // ── Token Analysis ────────────────────────────────────────
    @GET("/api/admin/token/analysis")
    suspend fun getTokenAnalysis(): ApiResponse<Any>

    @GET("/api/admin/token/records")
    suspend fun getTokenRecords(
        @Query("page") page: Int = 1,
        @Query("size") size: Int = 20
    ): ApiResponse<PaginatedResponse<Any>>

    // ── Admin User CRUD ───────────────────────────────────────
    @GET("/api/admin/users/{id}")
    suspend fun getAdminUser(@Path("id") userId: Long): ApiResponse<User>

    @POST("/api/admin/users")
    suspend fun createAdminUser(@Body user: User): ApiResponse<User>

    @PUT("/api/admin/users/{id}")
    suspend fun updateAdminUser(@Path("id") userId: Long, @Body user: User): ApiResponse<Unit>

    @DELETE("/api/admin/users/{id}")
    suspend fun deleteAdminUser(@Path("id") userId: Long): ApiResponse<Unit>

    @PUT("/api/admin/users/{id}/role")
    suspend fun changeUserRole(@Path("id") userId: Long, @Body role: Map<String, String>): ApiResponse<Unit>

    @PUT("/api/admin/users/batch/status")
    suspend fun batchToggleStatus(@Body ids: Map<String, List<Long>>): ApiResponse<Unit>

    @DELETE("/api/admin/users/batch")
    suspend fun batchDeleteUsers(@Body ids: Map<String, List<Long>>): ApiResponse<Unit>

    // ── Knowledge Graph CRUD ──────────────────────────────────
    @GET("/api/knowledge-graph/domain/{domainId}")
    suspend fun getKnowledgeDomain(@Path("domainId") domainId: Long): ApiResponse<Any>

    @PUT("/api/knowledge-graph/domain/{domainId}")
    suspend fun updateKnowledgeDomain(@Path("domainId") domainId: Long, @Body data: Any): ApiResponse<Unit>

    @DELETE("/api/knowledge-graph/domain/{domainId}")
    suspend fun deleteKnowledgeDomain(@Path("domainId") domainId: Long): ApiResponse<Unit>

    @DELETE("/api/knowledge-graph/domain/{domainId}/node/{nodeId}")
    suspend fun deleteGraphNode(@Path("domainId") domainId: Long, @Path("nodeId") nodeId: Long): ApiResponse<Unit>

    @PATCH("/api/knowledge-graph/domain/{domainId}/node/{nodeId}")
    suspend fun patchGraphNode(@Path("domainId") domainId: Long, @Path("nodeId") nodeId: Long, @Body data: Map<String, Any>): ApiResponse<Unit>

    // ── Dialogue Extensions ───────────────────────────────────
    @DELETE("/api/dialogue/{id}")
    suspend fun deleteMessage(@Path("id") messageId: Long): ApiResponse<Unit>

    @DELETE("/api/dialogue/batch")
    suspend fun deleteMessages(@Body ids: Map<String, List<Long>>): ApiResponse<Unit>

    @PUT("/api/dialogue/session/{sessionId}/link-plan/{planId}")
    suspend fun linkSessionToPlan(@Path("sessionId") sessionId: String, @Path("planId") planId: Long): ApiResponse<Unit>

    // ── Token Refresh ─────────────────────────────────────────
    @POST("/api/auth/refresh")
    suspend fun refreshToken(): ApiResponse<String>

    // ── Account ───────────────────────────────────────────────
    @DELETE("/api/user/account")
    suspend fun deleteAccount(): ApiResponse<Unit>

    // ── Task Extensions ───────────────────────────────────────
    @GET("/api/task/by-resource/{resourceId}")
    suspend fun getTaskByResource(@Path("resourceId") resourceId: Long): ApiResponse<ResourceGenerationTask>
}
