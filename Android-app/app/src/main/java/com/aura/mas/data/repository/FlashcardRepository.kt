package com.aura.mas.data.repository

import com.aura.mas.data.api.ApiService
import com.aura.mas.data.local.dao.FlashcardDao
import com.aura.mas.data.local.entity.CachedFlashcard
import com.aura.mas.data.model.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class FlashcardRepository @Inject constructor(
    private val api: ApiService,
    private val flashcardDao: FlashcardDao
) {
    suspend fun getDueFlashcards(): ApiResponse<List<Flashcard>> {
        return try {
            api.getDueFlashcards()
        } catch (e: Exception) {
            ApiResponse(message = e.message ?: "Network error")
        }
    }

    suspend fun getFlashcardsByNote(noteId: Long): ApiResponse<List<Flashcard>> {
        return try {
            api.getFlashcardsByNote(noteId)
        } catch (e: Exception) {
            ApiResponse(message = e.message ?: "Network error")
        }
    }

    suspend fun getDueCount(): ApiResponse<Int> {
        return try {
            api.getDueFlashcardCount()
        } catch (e: Exception) {
            ApiResponse(message = e.message ?: "Network error")
        }
    }

    suspend fun submitReview(cardId: Long, quality: Int): ApiResponse<Unit> {
        return api.submitFlashcardReview(
            cardId,
            mapOf("quality" to quality)
        )
    }

    suspend fun saveFlashcards(noteId: Long, cards: List<Flashcard>): ApiResponse<List<Flashcard>> {
        val result = api.saveFlashcards(FlashcardSaveRequest(noteId, cards))
        if (result.isSuccess && result.data != null) {
            flashcardDao.insertAll(result.data.map { it.toCached() })
        }
        return result
    }

    fun getCachedFlashcards(noteId: Long): Flow<List<CachedFlashcard>> =
        flashcardDao.getFlashcardsByNote(noteId)

    private fun Flashcard.toCached() = CachedFlashcard(
        id = id, userId = userId, noteId = noteId,
        question = question, answer = answer, difficulty = difficulty,
        nextReviewAt = nextReviewAt, easeFactor = easeFactor, interval = interval
    )
}
