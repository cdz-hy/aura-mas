package com.aura.mas.ui.plan

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.LearningPlan
import com.aura.mas.data.model.PlanCreateRequest
import com.aura.mas.data.repository.PlanRepository
import com.aura.mas.ui.common.TopAppBar
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PlanCreateUiState(
    val isLoading: Boolean = false,
    val plan: LearningPlan? = null,
    val error: String? = null
)

@HiltViewModel
class PlanCreateViewModel @Inject constructor(
    private val planRepo: PlanRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(PlanCreateUiState())
    val uiState: StateFlow<PlanCreateUiState> = _uiState.asStateFlow()

    fun createPlan(title: String, goal: String) {
        viewModelScope.launch {
            _uiState.value = PlanCreateUiState(isLoading = true)
            try {
                // Match Vue: learningGoal as object { raw: goal }, planConfig as object
                val learningGoalJson = com.google.gson.Gson().toJson(mapOf("raw" to goal))
                val result = planRepo.createPlan(PlanCreateRequest(
                    title = title.ifBlank { goal.take(50) },
                    learningGoal = learningGoalJson,
                    planConfig = "{}"
                ))
                if (result.isSuccess && result.data != null) {
                    _uiState.value = PlanCreateUiState(plan = result.data, isLoading = false)
                } else {
                    _uiState.value = PlanCreateUiState(error = result.message.ifEmpty { "创建失败" }, isLoading = false)
                }
            } catch (e: Exception) {
                _uiState.value = PlanCreateUiState(error = e.message ?: "网络错误", isLoading = false)
            }
        }
    }

    fun clearError() { _uiState.value = _uiState.value.copy(error = null) }
}

@Composable
fun PlanCreateScreen(
    onBack: () -> Unit,
    viewModel: PlanCreateViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    var title by remember { mutableStateOf("") }
    var goal by remember { mutableStateOf("") }

    LaunchedEffect(uiState.plan) {
        if (uiState.plan != null) onBack()
    }

    Scaffold(
        topBar = { TopAppBar("创建学习计划", onBack = onBack) }
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("新建学习计划", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(8.dp))

            OutlinedTextField(
                value = title, onValueChange = { title = it },
                label = { Text("计划标题") },
                placeholder = { Text("例如：深度学习基础") },
                leadingIcon = { Icon(Icons.Default.Title, null) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            )

            OutlinedTextField(
                value = goal, onValueChange = { goal = it },
                label = { Text("学习目标") },
                placeholder = { Text("描述你想要达到的学习目标...") },
                leadingIcon = { Icon(Icons.Default.Flag, null) },
                minLines = 3,
                maxLines = 6,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            )

            Spacer(Modifier.weight(1f))

            uiState.error?.let {
                Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }

            Button(
                onClick = { viewModel.createPlan(title, goal) },
                modifier = Modifier.fillMaxWidth().height(48.dp),
                enabled = !uiState.isLoading && (title.isNotBlank() || goal.isNotBlank()),
                shape = RoundedCornerShape(12.dp)
            ) {
                if (uiState.isLoading) {
                    CircularProgressIndicator(Modifier.size(24.dp), color = MaterialTheme.colorScheme.onPrimary, strokeWidth = 2.dp)
                } else {
                    Icon(Icons.Default.AutoAwesome, null)
                    Spacer(Modifier.width(8.dp))
                    Text("AI 生成计划", fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}
