package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName

data class QuizQuestion(
    val id: Long = 0,
    @SerializedName("resourceId") val resourceId: Long = 0,
    @SerializedName("questionType") val questionType: String = "single_choice",
    @SerializedName("questionText") val questionText: String = "",
    @SerializedName("correctAnswer") val correctAnswer: String = "",
    val options: List<String>? = null,
    val difficulty: Int = 1,
    val score: Int = 0,
    @SerializedName("isCorrect") val isCorrect: Boolean? = null,
    val userAnswer: String = "",
    val feedback: String = ""
) {
    companion object {
        const val TYPE_SINGLE_CHOICE = "single_choice"
        const val TYPE_MULTIPLE_CHOICE = "multiple_choice"
        const val TYPE_TRUE_FALSE = "true_false"
        const val TYPE_FILL_BLANK = "fill_blank"
        const val TYPE_SHORT_ANSWER = "short_answer"
        const val TYPE_CODE_OUTPUT = "code_output"
    }
}

data class QuizSubmission(
    @SerializedName("resourceId") val resourceId: Long,
    val answers: Map<String, String>
)

data class QuizRecord(
    val id: Long = 0,
    @SerializedName("resourceId") val resourceId: Long = 0,
    @SerializedName("userId") val userId: Long = 0,
    @SerializedName("planId") val planId: Long = 0,
    @SerializedName("questionType") val questionType: String = "",
    @SerializedName("questionText") val questionText: String = "",
    @SerializedName("correctAnswer") val correctAnswer: String = "",
    @SerializedName("userAnswer") val userAnswer: String = "",
    val score: Int = 0,
    @SerializedName("isCorrect") val isCorrect: Boolean = false,
    val feedback: String = ""
)
