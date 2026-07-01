package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName

data class DashboardStats(
    @SerializedName("totalPlans") val totalPlans: Long = 0,
    @SerializedName("planCount") val planCount: Int = 0,
    @SerializedName("activePlans") val activePlans: Long = 0,
    @SerializedName("completedPlans") val completedPlans: Long = 0,
    @SerializedName("completedPlanCount") val completedPlanCount: Int = 0,
    @SerializedName("totalNotes") val totalNotes: Long = 0,
    @SerializedName("totalQuizzes") val totalQuizzes: Long = 0,
    @SerializedName("correctQuizzes") val correctQuizzes: Long = 0,
    @SerializedName("todayDurationSeconds") val todayDurationSeconds: Int = 0,
    @SerializedName("totalDurationSeconds") val totalDurationSeconds: Int = 0,
    @SerializedName("completedResources") val completedResources: Long = 0,
    @SerializedName("totalResources") val totalResources: Int = 0,
    @SerializedName("totalStudyHours") val totalStudyHours: Double = 0.0,
    @SerializedName("totalStudyMinutes") val totalStudyMinutes: Int = 0,
    @SerializedName("quizAccuracy") val quizAccuracy: Double = 0.0,
    @SerializedName("weeklyMinutes") val weeklyMinutes: List<WeeklyMinute> = emptyList(),
    @SerializedName("weeklyStudyData") val weeklyStudyData: List<DailyStudy> = emptyList(),
    @SerializedName("recentActivity") val recentActivity: List<RecentActivity> = emptyList(),
    @SerializedName("greeting") val greeting: String = ""
)

data class WeeklyMinute(
    val label: String = "",
    val minutes: Int = 0
)

data class RecentActivity(
    val text: String = "",
    val time: String = "",
    val color: String = ""
)

data class DailyStudy(
    val date: String = "",
    val dayOfWeek: String = "",
    @SerializedName("totalSeconds") val totalSeconds: Int = 0,
    val minutes: Int = 0,
    val label: String = ""
)

data class StudyHeatmapData(
    val date: String = "",
    val minutes: Int = 0,
    val level: Int = 0
)

data class HeatmapResponse(
    val dailyData: List<StudyHeatmapData> = emptyList(),
    val currentStreak: Int = 0,
    val longestStreak: Int = 0,
    val totalActiveDays: Int = 0
)

data class QuizAnalysis(
    @SerializedName("totalQuestions") val totalQuestions: Int = 0,
    @SerializedName("correctCount") val correctCount: Int = 0,
    @SerializedName("accuracy") val accuracy: Double = 0.0,
    @SerializedName("byType") val byType: Map<String, TypeAnalysis> = emptyMap()
)

data class TypeAnalysis(
    val total: Int = 0,
    val correct: Int = 0,
    val accuracy: Double = 0.0
)

data class AnalyticsData(
    val quizAnalysis: QuizAnalysis? = null,
    @SerializedName("studyHeatmap") val studyHeatmap: List<StudyHeatmapData> = emptyList(),
    @SerializedName("flashcardStats") val flashcardStats: FlashcardStats? = null,
    @SerializedName("aiInteraction") val aiInteraction: AiInteractionStats? = null,
    @SerializedName("knowledgeMastery") val knowledgeMastery: List<MasteryItem> = emptyList(),
    @SerializedName("studyEfficiency") val studyEfficiency: List<EfficiencyItem> = emptyList(),
    @SerializedName("weekComparison") val weekComparison: WeekComparison? = null
)

data class FlashcardStats(
    @SerializedName("totalCards") val totalCards: Int = 0,
    @SerializedName("reviewedToday") val reviewedToday: Int = 0,
    @SerializedName("mastered") val masteredCount: Int = 0,
    @SerializedName("dueToday") val dueCount: Int = 0
)

data class AiInteractionStats(
    @SerializedName("totalMessages") val totalMessages: Int = 0,
    @SerializedName("totalSessions") val totalSessions: Int = 0,
    @SerializedName("avgResponseTime") val avgResponseTime: Double = 0.0
)

data class MasteryItem(
    val topic: String = "",
    val mastery: Double = 0.0
)

data class EfficiencyItem(
    val hour: Int = 0,
    @SerializedName("studySeconds") val studySeconds: Int = 0,
    val efficiency: Double = 0.0
)

data class WeekComparison(
    @SerializedName("thisWeekMinutes") val thisWeekMinutes: Int = 0,
    @SerializedName("lastWeekMinutes") val lastWeekMinutes: Int = 0,
    @SerializedName("changePercent") val changePercent: Double = 0.0
)

data class StudentProfile(
    @SerializedName("userId") val userId: Long = 0,
    val gender: String = "",
    val age: Int = 0,
    val domain: String = "",
    @SerializedName("learningBehavior") val learningBehavior: ProfileDimensions? = null
)

data class ProfileDimensions(
    @SerializedName("active_reflective") val activeReflective: Double = 0.5,
    @SerializedName("sensing_intuitive") val sensingIntuitive: Double = 0.5,
    @SerializedName("visual_verbal") val visualVerbal: Double = 0.5,
    @SerializedName("sequential_global") val sequentialGlobal: Double = 0.5,
    @SerializedName("knowledge_base") val knowledgeBase: List<String> = emptyList(),
    @SerializedName("interest_tags") val interestTags: List<String> = emptyList(),
    @SerializedName("goal_orientation") val goalOrientation: String = "",
    @SerializedName("weak_areas") val weakAreas: List<String> = emptyList()
)

data class PaginatedResponse<T>(
    val records: List<T> = emptyList(),
    val total: Long = 0,
    val page: Int = 1,
    val size: Int = 20,
    val pages: Int = 0
)
