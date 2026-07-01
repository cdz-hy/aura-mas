package com.aura.mas.ui.flashcard

import androidx.compose.animation.core.*
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.Flashcard
import com.aura.mas.data.repository.FlashcardRepository
import com.aura.mas.ui.common.LoadingIndicator
import com.aura.mas.ui.common.TopAppBar
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class FlashcardUiState(
    val isLoading: Boolean = true,
    val cards: List<Flashcard> = emptyList(),
    val currentIndex: Int = 0,
    val isFlipped: Boolean = false,
    val completedCount: Int = 0,
    val error: String? = null
)

@HiltViewModel
class FlashcardViewModel @Inject constructor(
    private val flashcardRepo: FlashcardRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(FlashcardUiState())
    val uiState: StateFlow<FlashcardUiState> = _uiState.asStateFlow()

    fun loadDueCards() {
        viewModelScope.launch {
            _uiState.value = FlashcardUiState(isLoading = true)
            try {
                val result = flashcardRepo.getDueFlashcards()
                if (result.code == 0 && result.data != null) {
                    _uiState.value = FlashcardUiState(cards = result.data, isLoading = false)
                } else {
                    _uiState.value = FlashcardUiState(error = result.message, isLoading = false)
                }
            } catch (e: Exception) {
                _uiState.value = FlashcardUiState(error = e.message, isLoading = false)
            }
        }
    }

    fun flipCard() {
        _uiState.value = _uiState.value.copy(isFlipped = !_uiState.value.isFlipped)
    }

    fun reviewCard(quality: Int) {
        viewModelScope.launch {
            val state = _uiState.value
            val card = state.cards.getOrNull(state.currentIndex) ?: return@launch
            flashcardRepo.submitReview(card.id, quality)
            val nextIndex = state.currentIndex + 1
            _uiState.value = state.copy(
                currentIndex = nextIndex,
                isFlipped = false,
                completedCount = state.completedCount + 1
            )
        }
    }
}

@Composable
fun FlashcardPlayerScreen(
    noteId: Long,
    onBack: () -> Unit,
    viewModel: FlashcardViewModel = hiltViewModel()
) {
    LaunchedEffect(Unit) { viewModel.loadDueCards() }
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = { TopAppBar("闪卡复习", onBack = onBack) }
    ) { padding ->
        if (uiState.isLoading) {
            LoadingIndicator(Modifier.padding(padding))
            return@Scaffold
        }

        if (uiState.cards.isEmpty() || uiState.currentIndex >= uiState.cards.size) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Default.CheckCircle, null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.secondary)
                    Spacer(Modifier.height(16.dp))
                    Text("复习完成！", style = MaterialTheme.typography.headlineSmall)
                    Text("已复习 ${uiState.completedCount} 张卡片", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            return@Scaffold
        }

        val card = uiState.cards[uiState.currentIndex]

        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Progress
            LinearProgressIndicator(
                progress = { (uiState.currentIndex + 1).toFloat() / uiState.cards.size },
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(8.dp))
            Text("${uiState.currentIndex + 1} / ${uiState.cards.size}", style = MaterialTheme.typography.labelMedium)

            Spacer(Modifier.height(32.dp))

            // Card
            val rotation by animateFloatAsState(
                targetValue = if (uiState.isFlipped) 180f else 0f,
                animationSpec = tween(400)
            )

            Card(
                modifier = Modifier.fillMaxWidth().weight(1f)
                    .graphicsLayer { rotationY = rotation; cameraDistance = 12f * density }
                    .clickable { viewModel.flipCard() },
                shape = RoundedCornerShape(24.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
            ) {
                Box(
                    modifier = Modifier.fillMaxSize().padding(32.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        if (rotation <= 90f) card.question else card.answer,
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Medium,
                        textAlign = TextAlign.Center
                    )
                }
            }

            Spacer(Modifier.height(16.dp))

            if (!uiState.isFlipped) {
                Text("点击卡片翻转", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                Text("你记住了吗？", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                Spacer(Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    listOf(
                        "忘记了" to 1,
                        "模糊" to 3,
                        "记住" to 5
                    ).forEach { (label, quality) ->
                        Button(
                            onClick = { viewModel.reviewCard(quality) },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = when (quality) {
                                    1 -> MaterialTheme.colorScheme.error
                                    3 -> MaterialTheme.colorScheme.tertiary
                                    else -> MaterialTheme.colorScheme.primary
                                }
                            ),
                            shape = RoundedCornerShape(12.dp)
                        ) { Text(label) }
                    }
                }
            }
        }
    }
}
