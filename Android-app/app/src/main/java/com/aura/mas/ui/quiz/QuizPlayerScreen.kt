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
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class QuizUiState(
    val isLoading: Boolean = true,
    val questions: List<QuizQuestion> = emptyList(),
    val currentIndex: Int = 0,
    val answers: MutableMap<Int, String> = mutableMapOf(),
    val isSubmitting: Boolean = false,
    val results: Map<Int, QuizQuestion>? = null,
    val score: Int = 0,
    val total: Int = 0,
    val error: String? = null
)

@HiltViewModel
class QuizViewModel @Inject constructor(
    private val api: ApiService
) : ViewModel() {
    private val _uiState = MutableStateFlow(QuizUiState())
    val uiState: StateFlow<QuizUiState> = _uiState.asStateFlow()

    fun loadQuiz(resourceId: Long) {
        viewModelScope.launch {
            _uiState.value = QuizUiState(isLoading = true)
            // Quiz data comes from resource content, parse it
            try {
                val resource = api.getResource(resourceId)
                // Parse quiz questions from resource content (JSON)
                _uiState.value = QuizUiState(isLoading = false)
            } catch (e: Exception) {
                _uiState.value = QuizUiState(isLoading = false, error = e.message)
            }
        }
    }

    fun selectAnswer(questionIndex: Int, answer: String) {
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

    fun submitQuiz() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSubmitting = true)
            // Submit answers via SSE
            _uiState.value = _uiState.value.copy(isSubmitting = false)
        }
    }
}

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
                Text("暂无测验题目")
            }
            return@Scaffold
        }

        val question = uiState.questions[uiState.currentIndex]
        val selectedAnswer = uiState.answers[uiState.currentIndex]

        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)
        ) {
            // Progress
            LinearProgressIndicator(
                progress = { (uiState.currentIndex + 1).toFloat() / uiState.questions.size },
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(8.dp))
            Text("第 ${uiState.currentIndex + 1} / ${uiState.questions.size} 题", style = MaterialTheme.typography.labelMedium)

            Spacer(Modifier.height(16.dp))

            Column(modifier = Modifier.weight(1f).verticalScroll(rememberScrollState())) {
                Text(question.questionText, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(16.dp))

                question.options?.forEach { option ->
                    val isSelected = selectedAnswer == option
                    Card(
                        onClick = { viewModel.selectAnswer(uiState.currentIndex, option) },
                        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = if (isSelected) MaterialTheme.colorScheme.primaryContainer
                            else MaterialTheme.colorScheme.surface
                        )
                    ) {
                        Text(
                            option,
                            modifier = Modifier.padding(16.dp),
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }
            }

            // Navigation buttons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                OutlinedButton(
                    onClick = { viewModel.prevQuestion() },
                    enabled = uiState.currentIndex > 0
                ) { Text("上一题") }

                if (uiState.currentIndex == uiState.questions.size - 1) {
                    Button(onClick = { viewModel.submitQuiz() }, enabled = !uiState.isSubmitting) {
                        Text("提交")
                    }
                } else {
                    Button(onClick = { viewModel.nextQuestion() }) { Text("下一题") }
                }
            }
        }
    }
}
