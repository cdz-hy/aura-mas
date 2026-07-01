package com.aura.mas.ui.chat

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.*
import com.aura.mas.data.repository.ChatRepository
import com.aura.mas.ui.common.*
import com.aura.mas.util.SseClient
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

enum class ChatMode { ASSISTANT, TUTOR }

data class StandaloneChatUiState(
    val isLoading: Boolean = true,
    val mode: ChatMode = ChatMode.ASSISTANT,
    val assistantSessions: List<ChatSession> = emptyList(),
    val tutorSessions: List<ChatSession> = emptyList(),
    val activeSessionId: String? = null,
    val messages: List<ChatMessage> = emptyList(),
    val isStreaming: Boolean = false,
    val streamContent: String = "",
    val error: String? = null
)

@HiltViewModel
class StandaloneChatViewModel @Inject constructor(
    private val chatRepo: ChatRepository,
    private val sseClient: SseClient
) : ViewModel() {
    private val _uiState = MutableStateFlow(StandaloneChatUiState())
    val uiState: StateFlow<StandaloneChatUiState> = _uiState.asStateFlow()

    init { loadSessions() }

    fun loadSessions() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val assistantSessions = chatRepo.loadChatSessions(planId = 0)
                val tutorSessions = chatRepo.loadStandaloneTutorSessions()
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    assistantSessions = assistantSessions,
                    tutorSessions = tutorSessions
                )
                // Auto-select the latest session for current mode
                val currentSessions = if (_uiState.value.mode == ChatMode.ASSISTANT) assistantSessions else tutorSessions
                if (currentSessions.isNotEmpty() && _uiState.value.activeSessionId == null) {
                    selectSession(currentSessions.first().sessionId)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun switchMode(mode: ChatMode) {
        _uiState.value = _uiState.value.copy(mode = mode, activeSessionId = null, messages = emptyList())
    }

    fun newSession() {
        val sessionId = when (_uiState.value.mode) {
            ChatMode.ASSISTANT -> chatRepo.generateChatSessionId()
            ChatMode.TUTOR -> chatRepo.generateTutorSessionId(planId = 0)
        }
        val session = ChatSession(sessionId = sessionId, intentType = if (_uiState.value.mode == ChatMode.TUTOR) "chat" else "", title = "新对话")
        val currentList = if (_uiState.value.mode == ChatMode.ASSISTANT) _uiState.value.assistantSessions else _uiState.value.tutorSessions
        val updatedList = listOf(session) + currentList
        _uiState.value = if (_uiState.value.mode == ChatMode.ASSISTANT) {
            _uiState.value.copy(assistantSessions = updatedList, activeSessionId = sessionId, messages = emptyList())
        } else {
            _uiState.value.copy(tutorSessions = updatedList, activeSessionId = sessionId, messages = emptyList())
        }
    }

    fun selectSession(sessionId: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(activeSessionId = sessionId)
            try {
                val result = chatRepo.getMessages(sessionId)
                if (result.code == 0 && result.data != null) {
                    _uiState.value = _uiState.value.copy(messages = result.data)
                }
            } catch (_: Exception) {}
        }
    }

    fun deleteSession(sessionId: String) {
        viewModelScope.launch {
            chatRepo.deleteSession(sessionId)
            loadSessions()
        }
    }

    fun sendMessage(message: String) {
        val sessionId = _uiState.value.activeSessionId ?: return
        val mode = _uiState.value.mode
        viewModelScope.launch {
            val userMsg = ChatMessage(role = ChatMessage.ROLE_USER, content = message)
            _uiState.value = _uiState.value.copy(
                messages = _uiState.value.messages + userMsg,
                isStreaming = true,
                streamContent = ""
            )
            try {
                val flow = when (mode) {
                    ChatMode.ASSISTANT -> chatRepo.chat(sessionId, message)
                    ChatMode.TUTOR -> chatRepo.tutorChat(sessionId, message)
                }
                flow.collect { event ->
                    when (event.type) {
                        "chunk", "stream_text" -> {
                            val data = sseClient.parseEventData(event.data)
                            val text = data?.get("text")?.asString ?: data?.get("content")?.asString ?: ""
                            _uiState.value = _uiState.value.copy(streamContent = _uiState.value.streamContent + text)
                        }
                        "thinking", "thinking_start", "thinking_chunk" -> {
                            // Could show thinking indicator
                        }
                        "search_start", "search_result", "search_done" -> {
                            // Could show search results
                        }
                        "done" -> {
                            flushStreamBuffer()
                        }
                        "error" -> {
                            flushStreamBuffer()
                        }
                    }
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isStreaming = false)
            }
        }
    }

    private fun flushStreamBuffer() {
        val content = _uiState.value.streamContent
        if (content.isNotBlank()) {
            val msg = ChatMessage(role = ChatMessage.ROLE_ASSISTANT, content = content)
            _uiState.value = _uiState.value.copy(
                messages = _uiState.value.messages + msg,
                streamContent = "",
                isStreaming = false
            )
        } else {
            _uiState.value = _uiState.value.copy(isStreaming = false)
        }
    }

    fun stopGeneration() {
        _uiState.value = _uiState.value.copy(isStreaming = false)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StandaloneChatScreen(
    onBack: () -> Unit,
    viewModel: StandaloneChatViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    var showSessionDrawer by remember { mutableStateOf(false) }

    val currentSessions = when (uiState.mode) {
        ChatMode.ASSISTANT -> uiState.assistantSessions
        ChatMode.TUTOR -> uiState.tutorSessions
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    // Mode switcher
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        FilterChip(
                            selected = uiState.mode == ChatMode.ASSISTANT,
                            onClick = { viewModel.switchMode(ChatMode.ASSISTANT) },
                            label = { Text("AI 助手", style = MaterialTheme.typography.labelSmall) },
                            modifier = Modifier.height(32.dp)
                        )
                        Spacer(Modifier.width(8.dp))
                        FilterChip(
                            selected = uiState.mode == ChatMode.TUTOR,
                            onClick = { viewModel.switchMode(ChatMode.TUTOR) },
                            label = { Text("智能辅导", style = MaterialTheme.typography.labelSmall) },
                            modifier = Modifier.height(32.dp)
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "返回") }
                },
                actions = {
                    IconButton(onClick = { showSessionDrawer = true }) {
                        Icon(Icons.Default.History, "历史会话")
                    }
                    IconButton(onClick = { viewModel.newSession() }) {
                        Icon(Icons.Default.Add, "新对话")
                    }
                }
            )
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            Column(modifier = Modifier.fillMaxSize()) {
                // Messages
                val listState = androidx.compose.foundation.lazy.rememberLazyListState()
                val totalItems = uiState.messages.size + (if (uiState.isStreaming && uiState.streamContent.isNotBlank()) 1 else 0)
                LaunchedEffect(totalItems) {
                    if (totalItems > 0) {
                        listState.animateScrollToItem(totalItems - 1)
                    }
                }

                LazyColumn(
                    state = listState,
                    modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(vertical = 8.dp)
                ) {
                    if (uiState.messages.isEmpty() && !uiState.isStreaming) {
                        item {
                            Box(Modifier.fillMaxWidth().padding(top = 100.dp), contentAlignment = Alignment.Center) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Icon(
                                        if (uiState.mode == ChatMode.ASSISTANT) Icons.Default.AutoAwesome else Icons.Default.School,
                                        null, modifier = Modifier.size(48.dp),
                                        tint = MaterialTheme.colorScheme.primary.copy(alpha = 0.5f)
                                    )
                                    Spacer(Modifier.height(12.dp))
                                    Text(
                                        if (uiState.mode == ChatMode.ASSISTANT) "开始新的对话" else "开始智能辅导",
                                        style = MaterialTheme.typography.titleMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                    Spacer(Modifier.height(4.dp))
                                    Text(
                                        if (uiState.mode == ChatMode.ASSISTANT) "输入你的问题，AI助手将为你解答" else "输入你的问题，智能导师将为你辅导",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
                                    )
                                }
                            }
                        }
                    }

                    items(uiState.messages) { msg -> ChatBubble(msg) }

                    if (uiState.isStreaming) {
                        item {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(Modifier.size(28.dp).clip(CircleShape).background(MaterialTheme.colorScheme.primary), contentAlignment = Alignment.Center) {
                                    Text("AI", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onPrimary)
                                }
                                Spacer(Modifier.width(8.dp))
                                if (uiState.streamContent.isBlank()) {
                                    CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                                }
                            }
                        }
                        if (uiState.streamContent.isNotBlank()) {
                            item {
                                Row {
                                    Spacer(Modifier.width(36.dp))
                                    Surface(shape = RoundedCornerShape(4.dp, 16.dp, 16.dp, 16.dp), color = MaterialTheme.colorScheme.surfaceVariant, tonalElevation = 1.dp) {
                                        Text(uiState.streamContent, modifier = Modifier.padding(12.dp), style = MaterialTheme.typography.bodyMedium)
                                    }
                                }
                            }
                        }
                    }
                }

                // Input
                ChatInputBar(
                    isStreaming = uiState.isStreaming,
                    onSend = { viewModel.sendMessage(it) },
                    onStop = { viewModel.stopGeneration() }
                )
            }

            // Session drawer
            if (showSessionDrawer) {
                Surface(
                    modifier = Modifier.fillMaxHeight().width(280.dp).align(Alignment.CenterStart),
                    shadowElevation = 8.dp
                ) {
                    Column {
                        Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                if (uiState.mode == ChatMode.ASSISTANT) "AI助手会话" else "智能辅导会话",
                                style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold
                            )
                            IconButton(onClick = { showSessionDrawer = false }, modifier = Modifier.size(24.dp)) {
                                Icon(Icons.Default.Close, null, modifier = Modifier.size(18.dp))
                            }
                        }
                        HorizontalDivider()
                        LazyColumn(Modifier.weight(1f)) {
                            items(currentSessions) { session ->
                                val isActive = session.sessionId == uiState.activeSessionId
                                Row(
                                    modifier = Modifier.fillMaxWidth()
                                        .background(if (isActive) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface)
                                        .clickable { viewModel.selectSession(session.sessionId); showSessionDrawer = false }
                                        .padding(12.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        if (uiState.mode == ChatMode.ASSISTANT) Icons.Default.ChatBubbleOutline else Icons.Default.School,
                                        null, modifier = Modifier.size(16.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                    Spacer(Modifier.width(8.dp))
                                    Text(session.title.ifEmpty { "对话" }, style = MaterialTheme.typography.bodySmall, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                                    IconButton(onClick = { viewModel.deleteSession(session.sessionId) }, modifier = Modifier.size(20.dp)) {
                                        Icon(Icons.Default.Delete, null, modifier = Modifier.size(14.dp))
                                    }
                                }
                            }
                        }
                        TextButton(onClick = { viewModel.newSession(); showSessionDrawer = false }, modifier = Modifier.fillMaxWidth()) {
                            Icon(Icons.Default.Add, null); Spacer(Modifier.width(4.dp)); Text("新建对话")
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ChatBubble(message: ChatMessage) {
    val isUser = message.role == ChatMessage.ROLE_USER
    val displayContent = remember(message.content) { parseMessageContent(message.content) }

    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start) {
        if (!isUser) {
            Box(Modifier.size(28.dp).clip(CircleShape).background(MaterialTheme.colorScheme.primary), contentAlignment = Alignment.Center) {
                Text("AI", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onPrimary)
            }
            Spacer(Modifier.width(8.dp))
        }
        Surface(
            shape = RoundedCornerShape(topStart = if (isUser) 16.dp else 4.dp, topEnd = if (isUser) 4.dp else 16.dp, bottomStart = 16.dp, bottomEnd = 16.dp),
            color = if (isUser) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant,
            tonalElevation = if (isUser) 0.dp else 1.dp
        ) {
            if (isUser) {
                Text(displayContent, modifier = Modifier.padding(12.dp), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onPrimary)
            } else {
                com.aura.mas.ui.components.resource.MarkdownRenderer(content = displayContent, modifier = Modifier.padding(12.dp))
            }
        }
    }
}

private fun parseMessageContent(content: String): String {
    if (content.isBlank()) return ""
    val trimmed = content.trim()
    if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return trimmed
    return try {
        val json = com.google.gson.Gson().fromJson(trimmed, com.google.gson.JsonElement::class.java)
        when {
            json.isJsonObject -> {
                val obj = json.asJsonObject
                obj.get("conversationText")?.asString?.let { if (it.isNotBlank()) return it }
                obj.get("content")?.asString?.let { if (it.isNotBlank()) return it }
                obj.get("text")?.asString?.let { if (it.isNotBlank()) return it }
                obj.get("message")?.asString?.let { if (it.isNotBlank()) return it }
                obj.getAsJsonObject("data")?.let { d ->
                    d.get("content")?.asString?.let { if (it.isNotBlank()) return it }
                }
                trimmed
            }
            json.isJsonArray -> {
                json.asJsonArray.mapNotNull { el ->
                    if (el.isJsonObject) el.asJsonObject.get("content")?.asString ?: el.asJsonObject.get("text")?.asString
                    else if (el.isJsonPrimitive) el.asString else null
                }.filter { it.isNotBlank() }.joinToString("\n").ifEmpty { trimmed }
            }
            else -> trimmed
        }
    } catch (_: Exception) { trimmed }
}

@Composable
private fun ChatInputBar(isStreaming: Boolean, onSend: (String) -> Unit, onStop: () -> Unit) {
    var input by remember { mutableStateOf("") }
    Surface(shadowElevation = 8.dp) {
        Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = input, onValueChange = { input = it },
                placeholder = { Text("输入问题...") },
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(24.dp),
                singleLine = true
            )
            Spacer(Modifier.width(8.dp))
            if (isStreaming) {
                FilledIconButton(onClick = onStop) { Icon(Icons.Default.Stop, "停止") }
            } else {
                FilledIconButton(onClick = { if (input.isNotBlank()) { onSend(input); input = "" } }, enabled = input.isNotBlank()) {
                    Icon(Icons.AutoMirrored.Filled.Send, "发送")
                }
            }
        }
    }
}
