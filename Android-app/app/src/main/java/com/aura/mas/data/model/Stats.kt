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

// ── Quiz Analysis ────────────────────────────────────────────────

data class QuizAnalysis(
    @SerializedName("byQuestionType") val byQuestionType: List<QuestionTypeItem> = emptyList(),
    @SerializedName("byDifficulty") val byDifficulty: List<DifficultyItem> = emptyList(),
    @SerializedName("dailyAccuracy") val dailyAccuracy: List<DailyAccuracyItem> = emptyList(),
    @SerializedName("recentTrend") val recentTrend: RecentTrend? = null
)

data class QuestionTypeItem(
    val type: String = "",
    val total: Int = 0,
    val correct: Int = 0,
    val accuracy: Double = 0.0
)

data class DifficultyItem(
    val difficulty: Int = 0,
    val total: Int = 0,
    val correct: Int = 0,
    val accuracy: Double = 0.0
)

data class DailyAccuracyItem(
    val date: String = "",
    val total: Int = 0,
    val accuracy: Double = 0.0
)

data class RecentTrend(
    val direction: String = "stable",
    val changePercent: Double = 0.0
)

// ── Heatmap ──────────────────────────────────────────────────────

data class HeatmapData(
    @SerializedName("dailyData") val dailyData: List<StudyHeatmapData> = emptyList(),
    @SerializedName("currentStreak") val currentStreak: Int = 0,
    @SerializedName("longestStreak") val longestStreak: Int = 0,
    @SerializedName("totalActiveDays") val totalActiveDays: Int = 0
)

// ── Flashcard Stats ──────────────────────────────────────────────

data class FlashcardStats(
    @SerializedName("totalCards") val totalCards: Int = 0,
    @SerializedName("dueToday") val dueToday: Int = 0,
    @SerializedName("mastered") val mastered: Int = 0,
    @SerializedName("learning") val learning: Int = 0,
    @SerializedName("newCards") val newCards: Int = 0,
    @SerializedName("avgEaseFactor") val avgEaseFactor: Double = 0.0,
    @SerializedName("easeFactorDistribution") val easeFactorDistribution: List<EaseFactorDistItem> = emptyList()
)

data class EaseFactorDistItem(
    val label: String = "",
    val count: Long = 0
)

// ── AI Interaction ───────────────────────────────────────────────

data class AiInteractionStats(
    @SerializedName("totalDialogues") val totalDialogues: Int = 0,
    @SerializedName("byIntentType") val byIntentType: List<IntentTypeItem> = emptyList(),
    @SerializedName("dailyDialogues") val dailyDialogues: List<DailyDialogueItem> = emptyList(),
    @SerializedName("avgSessionLength") val avgSessionLength: Double = 0.0
)

data class IntentTypeItem(
    val intent: String = "",
    val count: Long = 0,
    val percentage: Double = 0.0
)

data class DailyDialogueItem(
    val date: String = "",
    val count: Long = 0
)

// ── Knowledge Mastery ────────────────────────────────────────────

data class KnowledgeMastery(
    @SerializedName("mastered") val mastered: List<String> = emptyList(),
    @SerializedName("weakAreas") val weakAreas: List<String> = emptyList(),
    @SerializedName("interests") val interests: List<String> = emptyList(),
    @SerializedName("performance") val performance: MasteryPerformance? = null,
    @SerializedName("learningStyle") val learningStyle: MasteryLearningStyle? = null
)

data class MasteryPerformance(
    val learningSpeed: Double = 0.0,
    val engagement: Double = 0.0,
    val quizAccuracy: Double = 0.0,
    val completionRate: Double = 0.0
)

data class MasteryLearningStyle(
    @SerializedName("visual_vs_verbal") val visualVerbal: Double = 0.0,
    @SerializedName("active_vs_reflective") val activeReflective: Double = 0.0,
    @SerializedName("sensing_vs_intuitive") val sensingIntuitive: Double = 0.0,
    @SerializedName("sequential_vs_global") val sequentialGlobal: Double = 0.0
)

// ── Study Efficiency ─────────────────────────────────────────────

data class StudyEfficiency(
    @SerializedName("hourlyData") val hourlyData: List<HourlyDataItem> = emptyList(),
    @SerializedName("bestStudyHour") val bestStudyHour: Int = 0,
    @SerializedName("bestQuizHour") val bestQuizHour: Int = 0,
    @SerializedName("bestQuizAccuracy") val bestQuizAccuracy: Double = 0.0
)

data class HourlyDataItem(
    val hour: Int = 0,
    val studyMinutes: Int = 0,
    val sessionCount: Int = 0,
    val quizTotal: Int = 0,
    val quizCorrect: Int = 0,
    val accuracy: Double = 0.0
)

// ── Week Comparison ──────────────────────────────────────────────

data class WeekComparison(
    @SerializedName("studyMinutes") val studyMinutes: WeekMetric? = null,
    @SerializedName("quizAccuracy") val quizAccuracy: WeekMetric? = null,
    @SerializedName("activeDays") val activeDays: ActiveDaysMetric? = null
)

data class WeekMetric(
    val thisWeek: Double = 0.0,
    val lastWeek: Double = 0.0,
    val change: Double = 0.0
)

data class ActiveDaysMetric(
    val thisWeek: Int = 0,
    val lastWeek: Int = 0
)

// ── Aggregated Analytics ─────────────────────────────────────────

data class AnalyticsData(
    @SerializedName("quizAnalysis") val quizAnalysis: QuizAnalysis? = null,
    @SerializedName("heatmap") val heatmap: HeatmapData? = null,
    @SerializedName("flashcardStats") val flashcardStats: FlashcardStats? = null,
    @SerializedName("aiInteraction") val aiInteraction: AiInteractionStats? = null,
    @SerializedName("knowledgeMastery") val knowledgeMastery: KnowledgeMastery? = null,
    @SerializedName("studyEfficiency") val studyEfficiency: StudyEfficiency? = null,
    @SerializedName("weekComparison") val weekComparison: WeekComparison? = null
)

data class StudentProfile(
    @SerializedName("userId") val userId: Long = 0,
    val gender: String = "",
    val age: String = "",
    val domain: String = "",
    @SerializedName("learningBehavior") val learningBehavior: ProfileDimensions? = null
)

data class QuizPreference(
    val types: List<String> = emptyList(),
    val count: Int? = null,
    val difficulty: String = ""
)

data class ProfileDimensions(
    @SerializedName("active_vs_reflective") val activeReflective: Double = 0.0,
    @SerializedName("sensing_vs_intuitive") val sensingIntuitive: Double = 0.0,
    @SerializedName("visual_vs_verbal") val visualVerbal: Double = 0.0,
    @SerializedName("sequential_vs_global") val sequentialGlobal: Double = 0.0,
    @SerializedName("knowledge_base") val knowledgeBase: List<String> = emptyList(),
    @SerializedName("interest_tags") val interestTags: List<String> = emptyList(),
    @SerializedName("goal_orientation") val goalOrientation: String = "",
    @SerializedName("weak_areas") val weakAreas: List<String> = emptyList(),
    @SerializedName("preferred_resource_types") val preferredResourceTypes: List<String> = emptyList(),
    @SerializedName("preferred_quiz_preference") val preferredQuizPreference: QuizPreference? = null
)

data class PaginatedResponse<T>(
    val records: List<T> = emptyList(),
    val total: Long = 0,
    val page: Int = 1,
    val size: Int = 20,
    val pages: Int = 0
)
