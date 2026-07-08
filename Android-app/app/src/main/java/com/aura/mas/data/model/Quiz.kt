package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName

data class QuizQuestion(
    val id: Long = 0,
    @SerializedName("resourceId") val resourceId: Long = 0,
    @SerializedName(value = "questionType", alternate = ["question_type"]) val questionType: String = "single_choice",
    @SerializedName(value = "questionText", alternate = ["question_text", "question"]) val questionText: String = "",
    @SerializedName(value = "correctAnswer", alternate = ["correct_answer", "answer"]) val correctAnswer: Any? = null,
    val options: List<String>? = null,
    val difficulty: Int = 1,
    val score: Float = 0f,
    @SerializedName("isCorrect") val isCorrect: Boolean? = null,
    val userAnswer: String = "",
    val feedback: String = "",
    val explanation: String = "",
    @SerializedName("key_points_hit") val keyPointsHit: List<String>? = null,
    @SerializedName("key_points_missed") val keyPointsMissed: List<String>? = null,
    @SerializedName("improvement_suggestions") val improvementSuggestions: List<String>? = null,
    @SerializedName("per_question_score") val perQuestionScore: Float? = null
) {
    companion object {
        const val TYPE_SINGLE_CHOICE = "single_choice"
        const val TYPE_MULTIPLE_CHOICE = "multiple_choice"
        const val TYPE_TRUE_FALSE = "true_false"
        const val TYPE_FILL_BLANK = "fill_blank"
        const val TYPE_SHORT_ANSWER = "short_answer"
        const val TYPE_CODE_OUTPUT = "code_output"
    }

    /**
     * Get correct answer indices for choice questions.
     * Handles: JSON array, Python list, comma-separated, letter-based ("A","B"), numeric.
     */
    fun getCorrectIndices(): Set<Int> {
        val raw = correctAnswer ?: return emptySet()
        val str = raw.toString().trim()

        // Try parsing as JSON array
        if (str.startsWith("[") && str.endsWith("]")) {
            try {
                val arr = com.google.gson.Gson().fromJson(str, List::class.java)
                return arr.mapNotNull {
                    val s = it.toString().trim()
                    s.toIntOrNull() ?: letterToIndex(s)
                }.toSet()
            } catch (_: Exception) {}
        }

        // Comma-separated: "0,2" or "A,C"
        if ("," in str) {
            return str.split(",").mapNotNull { s ->
                val t = s.trim().removeSurrounding("\"", "'")
                t.toIntOrNull() ?: letterToIndex(t)
            }.toSet()
        }

        // Single value
        val single = str.toIntOrNull() ?: letterToIndex(str)
        return if (single != null) setOf(single) else emptySet()
    }

    /**
     * Get the default options for true/false questions.
     */
    fun getOptionsOrDefault(): List<String> {
        if (!options.isNullOrEmpty()) return options
        return when (questionType) {
            TYPE_TRUE_FALSE -> listOf("正确", "错误")
            else -> options ?: emptyList()
        }
    }

    private fun letterToIndex(letter: String): Int? {
        val upper = letter.uppercase()
        return if (upper.length == 1 && upper[0] in 'A'..'Z') {
            upper[0] - 'A'
        } else null
    }
}

data class QuizSubmission(
    @SerializedName("resourceId") val resourceId: Long,
    val answers: Map<String, Any>
)

data class QuizRecord(
    val id: Long = 0,
    @SerializedName("resourceId") val resourceId: Long = 0,
    @SerializedName("userId") val userId: Long = 0,
    @SerializedName("planId") val planId: Long = 0,
    @SerializedName(value = "questionType", alternate = ["question_type"]) val questionType: String = "",
    @SerializedName(value = "questionText", alternate = ["question_text", "question"]) val questionText: String = "",
    @SerializedName(value = "correctAnswer", alternate = ["correct_answer", "answer"]) val correctAnswer: String = "",
    @SerializedName("userAnswer") val userAnswer: String = "",
    val score: Float = 0f,
    @SerializedName("isCorrect") val isCorrect: Boolean = false,
    val feedback: String = "",
    val difficulty: Int = 1
)
