package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName

data class Flashcard(
    val id: Long = 0,
    @SerializedName("userId") val userId: Long = 0,
    @SerializedName("noteId") val noteId: Long = 0,
    val question: String = "",
    val answer: String = "",
    val difficulty: Int = 1,
    @SerializedName("nextReviewAt") val nextReviewAt: String? = null,
    @SerializedName("easeFactor") val easeFactor: Double = 2.5,
    @SerializedName("reviewInterval") val interval: Int = 0,
    @SerializedName("isDeleted") val isDeleted: Int = 0
)

data class FlashcardReviewResult(
    val quality: Int,
    @SerializedName("easeFactor") val easeFactor: Double,
    val interval: Int,
    @SerializedName("nextReviewAt") val nextReviewAt: String
)

data class FlashcardSaveRequest(
    @SerializedName("noteId") val noteId: Long,
    val flashcards: List<Flashcard>
)
