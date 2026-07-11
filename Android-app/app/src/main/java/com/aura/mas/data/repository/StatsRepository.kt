package com.aura.mas.data.repository

import com.aura.mas.data.api.ApiService
import com.aura.mas.data.model.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class StatsRepository @Inject constructor(private val api: ApiService) {
    suspend fun getDashboardStats() = api.getDashboardStats()
    suspend fun getStudyHeatmap() = api.getStudyHeatmap()
    suspend fun getQuizAnalysis() = api.getQuizAnalysis()
    suspend fun getFlashcardStats() = api.getFlashcardStats()
    suspend fun getAiInteractionStats() = api.getAiInteractionStats()
    suspend fun getKnowledgeMastery() = api.getKnowledgeMastery()
    suspend fun getAnalytics() = api.getAnalytics()
    suspend fun getStudyEfficiency() = api.getStudyEfficiency()
    suspend fun getWeekComparison() = api.getWeekComparison()
}
