package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName
import com.google.gson.JsonElement

data class LearningPlan(
    val id: Long = 0,
    @SerializedName("userId") val userId: Long = 0,
    val title: String = "",
    @SerializedName("learningGoal") val learningGoal: String? = null,
    @SerializedName("planConfig") val planConfig: String? = null,
    val status: Int = 0,
    @SerializedName("displayStatus") val displayStatus: Int? = null,
    @SerializedName("isDeleted") val isDeleted: Int = 0,
    val createdAt: String? = null,
    val updatedAt: String? = null,
    val progress: Double = 0.0
) {
    fun getPercentProgress(): Int {
        return if (progress in 0.0001..1.0) {
            (progress * 100).toInt()
        } else {
            progress.toInt()
        }
    }

    companion object {
        const val STATUS_PENDING = 0
        const val STATUS_GENERATING = 1
        const val STATUS_CONFIRMING = 2
        const val STATUS_LEARNING = 3
        const val STATUS_COMPLETED = 4
    }

    fun getEffectiveStatus(): Int = displayStatus ?: status

    fun getStatusText(): String = when (getEffectiveStatus()) {
        STATUS_PENDING -> "待规划"
        STATUS_GENERATING -> "生成中"
        STATUS_CONFIRMING -> "确认中"
        STATUS_LEARNING -> "学习中"
        STATUS_COMPLETED -> "已完成"
        else -> "未知"
    }

    fun getIconSvg(): String? {
        return try {
            val configStr = planConfig ?: return null
            val json = com.google.gson.Gson().fromJson(configStr, com.google.gson.JsonObject::class.java)
            json?.get("iconSvg")?.asString
        } catch (e: Exception) {
            null
        }
    }
}

data class LearningResource(
    val id: Long = 0,
    @SerializedName("planId") val planId: Long = 0,
    @SerializedName("parentId") val parentId: Long? = null,
    @SerializedName("moduleType") val moduleType: String = "",
    @SerializedName("moduleOrder") val moduleOrder: Int = 0,
    @SerializedName("moduleData") val moduleData: Any? = null,
    val status: Int = 0,
    @SerializedName("storagePath") val storagePath: String? = null,
    @SerializedName("generatedByAgent") val generatedByAgent: String? = null,
    val version: Int = 0,
    val createdAt: String? = null,
    val updatedAt: String? = null
) {
    companion object {
        const val STATUS_NOT_STARTED = 0
        const val STATUS_GENERATING = 1
        const val STATUS_READY = 2
    }

    fun getModuleName(): String {
        val parsed = getParsedModuleData()
        return parsed["module_title"]?.toString()
            ?: parsed["title"]?.toString()
            ?: ""
    }

    fun getResourceTitle(): String {
        val parsed = getParsedModuleData()
        return parsed["title"]?.toString()
            ?: parsed["resource_title"]?.toString()
            ?: getModuleName()
    }

    fun getResourceType(): String = moduleType

    fun getContent(): String {
        val parsed = getParsedModuleData()
        // Try multiple content paths (matching Vue's normalizeResourceModuleData)
        val content = parsed["content"]?.toString()
            ?: parsed["html"]?.toString()
            ?: ""
        if (content.isNotBlank()) return content

        // Try nested generated_content or data
        val nested = parsed["generated_content"] as? Map<*, *>
            ?: parsed["data"] as? Map<*, *>
        if (nested != null) {
            return nested["content"]?.toString()
                ?: nested["html"]?.toString()
                ?: ""
        }
        return ""
    }

    fun getQuizQuestions(): List<QuizQuestion> {
        val parsed = getParsedModuleData()
        val questions = mutableListOf<QuizQuestion>()

        // Try md.questions first
        val questionsArray = parsed["questions"] as? List<*>
            ?: (parsed["generated_content"] as? Map<*, *>)?.get("questions") as? List<*>
            ?: (parsed["data"] as? Map<*, *>)?.get("questions") as? List<*>

        if (questionsArray != null) {
            questionsArray.forEach { q ->
                if (q is Map<*, *>) {
                    questions.add(QuizQuestion(
                        questionType = q["questionType"]?.toString() ?: q["type"]?.toString() ?: "single_choice",
                        questionText = q["questionText"]?.toString() ?: q["question"]?.toString() ?: "",
                        correctAnswer = q["correctAnswer"]?.toString() ?: q["answer"]?.toString() ?: "",
                        options = (q["options"] as? List<*>)?.map { it.toString() },
                        difficulty = (q["difficulty"] as? Number)?.toInt() ?: 1
                    ))
                }
            }
        }

        // Fallback: try content as JSON
        if (questions.isEmpty()) {
            val content = getContent()
            try {
                val json = com.google.gson.Gson().fromJson(content, com.google.gson.JsonObject::class.java)
                val qArray = json?.getAsJsonArray("questions")
                qArray?.forEach { element ->
                    if (element.isJsonObject) {
                        val q = element.asJsonObject
                        questions.add(QuizQuestion(
                            questionType = q.get("questionType")?.asString ?: q.get("type")?.asString ?: "single_choice",
                            questionText = q.get("questionText")?.asString ?: q.get("question")?.asString ?: "",
                            correctAnswer = q.get("correctAnswer")?.asString ?: q.get("answer")?.asString ?: "",
                            options = q.getAsJsonArray("options")?.map { it.asString },
                            difficulty = q.get("difficulty")?.asInt ?: 1
                        ))
                    }
                }
            } catch (_: Exception) {}
        }

        return questions
    }

    fun getMindmapData(): Any? {
        val parsed = getParsedModuleData()
        return parsed["nodeData"]
            ?: parsed["node_data"]
            ?: (parsed["generated_content"] as? Map<*, *>)?.get("nodeData")
            ?: (parsed["data"] as? Map<*, *>)?.get("nodeData")
    }

    fun getVideoUrls(): List<String> {
        val parsed = getParsedModuleData()
        val videos = parsed["videos"] as? List<*>
            ?: (parsed["generated_content"] as? Map<*, *>)?.get("videos") as? List<*>
        return videos?.mapNotNull { it?.toString() } ?: emptyList()
    }

    fun getParsedModuleData(): Map<String, Any> {
        val raw = when (moduleData) {
            is Map<*, *> -> {
                @Suppress("UNCHECKED_CAST")
                moduleData as Map<String, Any>
            }
            is String -> {
                try {
                    val json = com.google.gson.Gson().fromJson(moduleData, com.google.gson.JsonObject::class.java)
                    jsonToMap(json)
                } catch (e: Exception) {
                    mapOf("content" to moduleData)
                }
            }
            is JsonElement -> {
                try {
                    jsonToMap(moduleData as? com.google.gson.JsonObject)
                } catch (e: Exception) {
                    emptyMap()
                }
            }
            else -> emptyMap()
        }
        // Vue's normalizeResourceModuleData: unwrap generated_content / data nested objects
        return normalizeModuleData(raw)
    }

    /**
     * Matches Vue's normalizeResourceModuleData():
     * - Unwraps generated_content or data nested objects
     * - Type-specific field mapping
     */
    private fun normalizeModuleData(raw: Map<String, Any>): Map<String, Any> {
        val result = raw.toMutableMap()

        // Unwrap nested generated_content or data
        val nested = (result["generated_content"] as? Map<*, *>)
            ?: (result["data"] as? Map<*, *>)
        if (nested != null) {
            // Merge nested fields under, top-level wins
            nested.forEach { (key, value) ->
                if (key is String && value != null && !result.containsKey(key)) {
                    result[key] = value
                }
            }
        }

        // Type-specific normalization
        when (moduleType) {
            "animation" -> {
                val html = result["html"]?.toString() ?: result["content"]?.toString() ?: ""
                result["html"] = html
                if (!result.containsKey("content") || result["content"].toString().isBlank()) {
                    result["content"] = html
                }
            }
            "mindmap" -> {
                val nodeData = result["nodeData"] ?: result["node_data"]
                if (!result.containsKey("content") || result["content"].toString().isBlank()) {
                    if (nodeData != null) {
                        result["content"] = if (nodeData is String) nodeData
                        else com.google.gson.Gson().toJson(nodeData)
                    }
                }
            }
            else -> {
                if (!result.containsKey("content") || result["content"].toString().isBlank()) {
                    result["content"] = result["html"]?.toString() ?: ""
                }
            }
        }

        return result
    }

    private fun jsonToMap(json: com.google.gson.JsonObject?): Map<String, Any> {
        if (json == null) return emptyMap()
        val map = mutableMapOf<String, Any>()
        json.entrySet().forEach { (key, value) ->
            map[key] = jsonElementToAny(value)
        }
        return map
    }

    private fun jsonElementToAny(element: com.google.gson.JsonElement): Any {
        return when {
            element.isJsonPrimitive -> {
                val prim = element.asJsonPrimitive
                when {
                    prim.isBoolean -> prim.asBoolean
                    prim.isNumber -> prim.asNumber
                    else -> prim.asString
                }
            }
            element.isJsonObject -> jsonToMap(element.asJsonObject)
            element.isJsonArray -> element.asJsonArray.map { jsonElementToAny(it) }
            else -> element.toString()
        }
    }
}

data class ResourceGenerationTask(
    val id: Long = 0,
    @SerializedName("planId") val planId: Long = 0,
    @SerializedName("resourceId") val resourceId: Long = 0,
    @SerializedName("agentChain") val agentChain: String? = null,
    @SerializedName("taskStatus") val taskStatus: String = "pending"
)

data class PlanCreateRequest(
    val title: String,
    @SerializedName("learningGoal") val learningGoal: String = "",
    @SerializedName("planConfig") val planConfig: String = ""
)

data class ResourceProgress(
    val id: Long = 0,
    val planId: Long = 0,
    @SerializedName("resourceId") val resourceId: Long = 0,
    val status: Int = 0, // 0=未开始, 1=学习中, 2=已完成
    val durationSeconds: Int = 0
) {
    val completed: Boolean get() = status == 2
}
