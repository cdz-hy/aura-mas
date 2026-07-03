package com.aura.mas.ui.quiz

import androidx.compose.animation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.api.ApiService
import com.aura.mas.data.model.QuizQuestion
import com.aura.mas.ui.common.LoadingIndicator
import com.aura.mas.ui.common.TopAppBar
import com.aura.mas.util.SseClient
import com.aura.mas.util.Constants
import com.google.gson.Gson
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.net.URLEncoder
import javax.inject.Inject

data class QuizUiState(
    val isLoading: Boolean = true,
    val questions: List<QuizQuestion> = emptyList(),
    val currentIndex: Int = 0,
    val answers: Map<Int, Any> = emptyMap(),
    val isSubmitting: Boolean = false,
    val results: Map<Int, QuizQuestion>? = null,
    val score: Int = 0,
    val total: Int = 0,
    val planId: Long = 0L,
    val error: String? = null
)

@HiltViewModel
class QuizViewModel @Inject constructor(
    private val api: ApiService,
    private val sseClient: SseClient,
    private val networkUtil: com.aura.mas.util.NetworkUtil
) : ViewModel() {
    private val _uiState = MutableStateFlow(QuizUiState())
    val uiState: StateFlow<QuizUiState> = _uiState.asStateFlow()

    private var resourceId: Long = 0L

    fun loadQuiz(resourceId: Long) {
        this.resourceId = resourceId
        viewModelScope.launch {
            _uiState.value = QuizUiState(isLoading = true)
            try {
                val response = api.getResource(resourceId)
                val resource = response.data
                if (resource != null) {
                    val parsed = resource.getParsedModuleData()
                    val qList = parsed["questions"] as? List<*>
                    val parsedQuestions = qList?.filterIsInstance<Map<String, Any>>()?.mapIndexed { idx, qMap ->
                        val optionsRaw = qMap["options"] as? List<*>
                        val options = optionsRaw?.mapNotNull { it?.toString() }
                        QuizQuestion(
                            id = idx.toLong(),
                            resourceId = resourceId,
                            questionType = qMap["type"]?.toString() ?: qMap["questionType"]?.toString() ?: "short_answer",
                            questionText = qMap["question"]?.toString() ?: qMap["question_text"]?.toString() ?: "",
                            correctAnswer = qMap["correctAnswer"]?.toString() ?: qMap["correct_answer"]?.toString() ?: "",
                            options = options
                        )
                    } ?: emptyList()

                    // Try to restore previous results if they exist in latestResult
                    val latestResult = parsed["latestResult"] as? Map<*, *>
                    val score = (latestResult?.get("score") as? Number)?.toInt() ?: 0
                    val total = (latestResult?.get("total") as? Number)?.toInt() ?: parsedQuestions.size
                    
                    val answers = mutableMapOf<Int, Any>()
                    val prevAnswers = latestResult?.get("answers") as? Map<*, *>
                    prevAnswers?.forEach { (k, v) ->
                        val keyInt = k.toString().toIntOrNull()
                        if (keyInt != null && v != null) {
                            answers[keyInt] = v
                        }
                    }

                    val results = if (latestResult != null) {
                        val detailsList = latestResult["details"] as? List<*>
                        val resultsMap = mutableMapOf<Int, QuizQuestion>()
                        detailsList?.filterIsInstance<Map<String, Any>>()?.forEach { dMap ->
                            val idx = (dMap["index"] as? Number)?.toInt() ?: 0
                            if (idx >= 0 && idx < parsedQuestions.size) {
                                val isCorrect = dMap["is_correct"] as? Boolean ?: false
                                val feedback = dMap["feedback"] as? String ?: ""
                                resultsMap[idx] = parsedQuestions[idx].copy(
                                    isCorrect = isCorrect,
                                    feedback = feedback
                                )
                            }
                        }
                        resultsMap
                    } else null

                    val updatedQuestions = if (results != null) {
                        parsedQuestions.mapIndexed { idx, q ->
                            val r = results[idx]
                            if (r != null) q.copy(isCorrect = r.isCorrect, feedback = r.feedback) else q
                        }
                    } else parsedQuestions

                    _uiState.value = QuizUiState(
                        isLoading = false,
                        questions = updatedQuestions,
                        answers = answers,
                        planId = resource.planId,
                        results = results,
                        score = score,
                        total = total
                    )
                } else {
                    _uiState.value = QuizUiState(isLoading = false, error = "资源未加载")
                }
            } catch (e: Exception) {
                _uiState.value = QuizUiState(isLoading = false, error = e.message)
            }
        }
    }

    fun selectAnswer(questionIndex: Int, answer: Any) {
        val answers = _uiState.value.answers.toMutableMap()
        answers[questionIndex] = answer
        _uiState.value = _uiState.value.copy(answers = answers)
    }

    fun nextQuestion() {
        val state = _uiState.value
        if (state.currentIndex < state.questions.size - 1) {
            _uiState.value = state.copy(currentIndex = state.currentIndex + 1)
        }
    }

    fun prevQuestion() {
        val state = _uiState.value
        if (state.currentIndex > 0) {
            _uiState.value = state.copy(currentIndex = state.currentIndex - 1)
        }
    }

    fun submitQuiz(planId: Long) {
        val state = _uiState.value
        if (state.isSubmitting || state.questions.isEmpty()) return
        if (!networkUtil.isOnline()) {
            _uiState.value = state.copy(error = "离线状态，无法提交测验")
            return
        }
        _uiState.value = state.copy(isSubmitting = true, error = null)

        viewModelScope.launch {
            try {
                val ticketResult = api.issueTicket()
                if (!ticketResult.isSuccess || ticketResult.data == null) {
                    _uiState.value = _uiState.value.copy(isSubmitting = false, error = "无法申请答题票据")
                    return@launch
                }
                val ticket = ticketResult.data?.get("ticket")
                if (ticket.isNullOrBlank()) {
                    _uiState.value = _uiState.value.copy(isSubmitting = false, error = "票据获取失败")
                    return@launch
                }

                val answersMap = state.answers.mapKeys { it.key.toString() }
                val answersJson = Gson().toJson(answersMap)

                val url = "${Constants.PYTHON_BASE_URL}api/ai/quiz/submit?" +
                        "ticket=$ticket" +
                        "&resource_id=$resourceId" +
                        "&plan_id=$planId" +
                        "&answers=${URLEncoder.encode(answersJson, "UTF-8")}"

                val questionResultsMap = mutableMapOf<Int, QuizQuestion>()
                var finalScore = 0
                var finalTotal = state.questions.size
                var finalCorrect = 0

                sseClient.connect(url).collect { event ->
                    val json = sseClient.parseEventData(event.data)
                    if (json != null) {
                        when (json.get("type")?.asString) {
                            "quiz_question_result" -> {
                                val idx = json.get("index")?.asInt ?: 0
                                val resultObj = json.getAsJsonObject("result")
                                if (resultObj != null && idx >= 0 && idx < state.questions.size) {
                                    val isCorrect = resultObj.get("is_correct")?.asBoolean ?: false
                                    val feedback = resultObj.get("feedback")?.asString ?: ""
                                    val updatedQ = state.questions[idx].copy(
                                        isCorrect = isCorrect,
                                        feedback = feedback
                                    )
                                    questionResultsMap[idx] = updatedQ
                                    updateQuestionInState(idx, isCorrect, feedback)
                                }
                            }
                            "quiz_result" -> {
                                val resultObj = json.getAsJsonObject("result")
                                if (resultObj != null) {
                                    finalScore = resultObj.get("score")?.asInt ?: 0
                                    finalTotal = resultObj.get("total")?.asInt ?: state.questions.size
                                    finalCorrect = resultObj.get("correct")?.asInt ?: 0
                                }
                            }
                            "done" -> {
                                val response = api.getResource(resourceId)
                                val resource = response.data
                                if (resource != null) {
                                    val parsed = resource.getParsedModuleData().toMutableMap()
                                    parsed["latestResult"] = mapOf(
                                        "answers" to answersMap,
                                        "score" to finalScore,
                                        "total" to finalTotal,
                                        "correct" to finalCorrect,
                                        "details" to questionResultsMap.map { (idx, q) ->
                                            mapOf(
                                                "index" to idx,
                                                "question" to q.questionText,
                                                "is_correct" to q.isCorrect,
                                                "feedback" to q.feedback
                                            )
                                        }
                                    )
                                    api.updateResourceContent(resourceId, mapOf(
                                        "moduleData" to Gson().toJson(parsed),
                                        "status" to 2
                                    ))
                                }

                                _uiState.value = _uiState.value.copy(
                                    isSubmitting = false,
                                    score = finalScore,
                                    total = finalTotal,
                                    results = questionResultsMap.toMap()
                                )
                            }
                            "error" -> {
                                val content = json.get("content")?.asString ?: "判分出错"
                                _uiState.value = _uiState.value.copy(isSubmitting = false, error = content)
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isSubmitting = false, error = e.message ?: "提交失败")
            }
        }
    }

    private fun updateQuestionInState(index: Int, isCorrect: Boolean, feedback: String) {
        val questions = _uiState.value.questions.toMutableList()
        if (index >= 0 && index < questions.size) {
            questions[index] = questions[index].copy(
                isCorrect = isCorrect,
                feedback = feedback
            )
            _uiState.value = _uiState.value.copy(questions = questions)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun QuizPlayerScreen(
    resourceId: Long,
    onBack: () -> Unit,
    viewModel: QuizViewModel = hiltViewModel()
) {
    LaunchedEffect(resourceId) { viewModel.loadQuiz(resourceId) }
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = { TopAppBar("测验", onBack = onBack) }
    ) { padding ->
        if (uiState.isLoading) {
            LoadingIndicator(Modifier.padding(padding))
            return@Scaffold
        }

        if (uiState.questions.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text(uiState.error ?: "暂无测验题目")
            }
            return@Scaffold
        }

        val question = uiState.questions[uiState.currentIndex]
        val selectedAnswer = uiState.answers[uiState.currentIndex]

        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)
        ) {
            if (uiState.results != null) {
                Card(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Stars, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(24.dp))
                            Spacer(Modifier.width(8.dp))
                            Text("测验已评分", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onPrimaryContainer)
                        }
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "得分: ${uiState.score} / ${uiState.total} 分",
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "你可以通过下方的“上一题/下一题”翻看 AI 对每一道题目的详细解析反馈。",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
                        )
                    }
                }
            }

            if (uiState.error != null) {
                Text(
                    text = uiState.error ?: "",
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
            }

            QuizQuestionView(
                question = question,
                questionIndex = uiState.currentIndex,
                totalQuestions = uiState.questions.size,
                selectedAnswer = selectedAnswer,
                onAnswer = { ans -> viewModel.selectAnswer(uiState.currentIndex, ans) },
                onNext = { viewModel.nextQuestion() },
                onPrev = { viewModel.prevQuestion() },
                onSubmit = { viewModel.submitQuiz(uiState.planId) },
                isSubmitting = uiState.isSubmitting,
                showResult = uiState.results != null,
                modifier = Modifier.weight(1f)
            )
        }
    }
}
