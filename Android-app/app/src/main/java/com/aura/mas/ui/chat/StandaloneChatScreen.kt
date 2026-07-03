package com.aura.mas.ui.chat

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.*
import com.aura.mas.data.repository.ChatRepository
import com.aura.mas.ui.common.*
import com.aura.mas.ui.components.resource.MarkdownRenderer
import com.aura.mas.ui.theme.*
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
    val thinkingSteps: List<ThinkingStep> = emptyList(),
    val searchSources: List<SearchSource> = emptyList(),
    val isSearching: Boolean = false,
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
                // Auto-select the latest session
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
        val sessions = if (mode == ChatMode.ASSISTANT) _uiState.value.assistantSessions else _uiState.value.tutorSessions
        if (sessions.isNotEmpty()) {
            selectSession(sessions.first().sessionId)
        }
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
                if (result.isSuccess && result.data != null) {
                    _uiState.value = _uiState.value.copy(messages = result.data.map { it.normalize() })
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

    fun confirmBreakdown() {
        val lastMsg = _uiState.value.messages.lastOrNull()
        if (lastMsg != null && lastMsg.type == "confirm" && lastMsg.breakdown != null) {
            val breakdownJson = com.google.gson.Gson().toJson(lastMsg.breakdown)
            sendMessage("确认，开始生成学习资源", mapOf("task_breakdown" to breakdownJson))
        }
    }

    fun modifyBreakdown(feedback: String) {
        if (feedback.isBlank()) return
        val lastMsg = _uiState.value.messages.lastOrNull()
        if (lastMsg != null && lastMsg.type == "confirm" && lastMsg.breakdown != null) {
            val breakdownJson = com.google.gson.Gson().toJson(lastMsg.breakdown)
            sendMessage(feedback, mapOf("task_breakdown" to breakdownJson))
        }
    }

    fun sendMessage(message: String, extraParams: Map<String, String>? = null) {
        if (message.isBlank()) return
        val mode = _uiState.value.mode
        viewModelScope.launch {
            val sessionId = _uiState.value.activeSessionId ?: if (mode == ChatMode.TUTOR) {
                chatRepo.generateTutorSessionId(0)
            } else {
                chatRepo.generateChatSessionId()
            }
            if (_uiState.value.activeSessionId == null) {
                _uiState.value = _uiState.value.copy(activeSessionId = sessionId)
            }
            val userMsg = ChatMessage(role = ChatMessage.ROLE_USER, content = message, sessionId = sessionId)
            _uiState.value = _uiState.value.copy(
                messages = _uiState.value.messages + userMsg,
                isStreaming = true,
                streamContent = "",
                thinkingSteps = emptyList(),
                searchSources = emptyList()
            )
            try {
                val flow = when (mode) {
                    ChatMode.ASSISTANT -> chatRepo.chat(sessionId, message, extraParams = extraParams)
                    ChatMode.TUTOR -> chatRepo.tutorChat(sessionId, message)
                }
                flow.collect { event ->
                    handleSseEvent(event)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isStreaming = false)
            }
        }
    }

    private fun handleSseEvent(event: com.aura.mas.util.SseEvent) {
        val data = event.rawJson ?: sseClient.parseEventData(event.data)
        when (event.type) {
            "stream_text", "chunk" -> {
                val text = data?.get("content")?.asString ?: data?.get("text")?.asString ?: ""
                _uiState.value = _uiState.value.copy(streamContent = _uiState.value.streamContent + text)
            }
            "thinking", "thinking_start" -> {
                val agent = data?.get("agent")?.asString ?: "AI"
                val content = data?.get("content")?.asString ?: ""
                val step = ThinkingStep(agent = agent, content = content)
                _uiState.value = _uiState.value.copy(
                    thinkingSteps = _uiState.value.thinkingSteps + step
                )
            }
            "thinking_chunk" -> {
                val content = data?.get("content")?.asString ?: ""
                val steps = _uiState.value.thinkingSteps.toMutableList()
                if (steps.isNotEmpty()) {
                    val last = steps.last()
                    steps[steps.size - 1] = last.copy(content = last.content + content)
                    _uiState.value = _uiState.value.copy(thinkingSteps = steps)
                }
            }
            "search_start" -> {
                val query = data?.get("query")?.asString ?: ""
                _uiState.value = _uiState.value.copy(isSearching = true, searchSources = emptyList())
            }
            "search_result" -> {
                val title = data?.get("title")?.asString ?: ""
                val url = data?.get("url")?.asString ?: ""
                val snippet = data?.get("snippet")?.asString ?: ""
                _uiState.value = _uiState.value.copy(
                    searchSources = _uiState.value.searchSources + SearchSource(title, url, snippet)
                )
            }
            "search_done" -> {
                _uiState.value = _uiState.value.copy(isSearching = false)
            }
            "done" -> {
                flushStreamBuffer()
                viewModelScope.launch {
                    try {
                        val activeId = _uiState.value.activeSessionId
                        if (activeId != null) {
                            val messagesResult = chatRepo.getMessages(activeId)
                            _uiState.value = _uiState.value.copy(
                                messages = messagesResult.data?.map { it.normalize() } ?: emptyList()
                            )
                        }
                    } catch (_: Exception) {}
                    loadSessions()
                }
            }
            "error" -> {
                flushStreamBuffer()
            }
        }
    }

    private fun flushStreamBuffer() {
        val content = _uiState.value.streamContent
        if (content.isNotBlank()) {
            val msg = ChatMessage(
                role = ChatMessage.ROLE_ASSISTANT,
                content = content,
                thinkings = _uiState.value.thinkingSteps,
                searchSources = _uiState.value.searchSources
            )
            _uiState.value = _uiState.value.copy(
                messages = _uiState.value.messages + msg,
                streamContent = "",
                thinkingSteps = emptyList(),
                searchSources = emptyList(),
                isSearching = false,
                isStreaming = false
            )
        } else {
            _uiState.value = _uiState.value.copy(
                isStreaming = false,
                thinkingSteps = emptyList(),
                searchSources = emptyList(),
                isSearching = false
            )
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
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        FilterChip(
                            selected = uiState.mode == ChatMode.ASSISTANT,
                            onClick = { viewModel.switchMode(ChatMode.ASSISTANT) },
                            label = { Text("AI 助手") },
                            modifier = Modifier.height(32.dp)
                        )
                        Spacer(Modifier.width(8.dp))
                        FilterChip(
                            selected = uiState.mode == ChatMode.TUTOR,
                            onClick = { viewModel.switchMode(ChatMode.TUTOR) },
                            label = { Text("智能辅导") },
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
                val listState = rememberLazyListState()
                val messages = uiState.messages
                val isStreaming = uiState.isStreaming
                val streamContent = uiState.streamContent

                var input by remember { mutableStateOf("") }

                // Auto-scroll to bottom
                LaunchedEffect(messages.size, streamContent) {
                    val totalItems = messages.size + (if (isStreaming && streamContent.isNotBlank()) 1 else 0)
                    if (totalItems > 0) {
                        listState.scrollToItem(totalItems - 1)
                    }
                }

                LazyColumn(
                    state = listState,
                    modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    contentPadding = PaddingValues(vertical = 16.dp)
                ) {
                    // Welcome message with quick questions
                    if (messages.isEmpty() && !isStreaming) {
                        item {
                            WelcomeMessage(uiState.mode, onQuickQuestion = { viewModel.sendMessage(it) })
                        }
                    }

                    // Messages
                    items(messages, key = { "${it.sessionId}_${it.createdAt}_${it.content.take(20)}" }) { msg ->
                        val context = androidx.compose.ui.platform.LocalContext.current
                        MessageBubble(
                            message = msg,
                            mode = uiState.mode,
                            onOpenResource = { resourceId ->
                                android.widget.Toast.makeText(context, "打开资源 ID: $resourceId", android.widget.Toast.LENGTH_SHORT).show()
                            }
                        )
                    }

                    // Confirm action buttons
                    val lastMsg = messages.lastOrNull()
                    if (lastMsg != null && lastMsg.type == "confirm" && !isStreaming) {
                        item {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(start = 40.dp, top = 4.dp),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Button(
                                    onClick = { viewModel.confirmBreakdown() },
                                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                                    shape = RoundedCornerShape(10.dp)
                                ) {
                                    Text("确认并生成", style = MaterialTheme.typography.labelMedium)
                                }
                                OutlinedButton(
                                    onClick = { 
                                        input = "补充说明："
                                    },
                                    shape = RoundedCornerShape(10.dp)
                                ) {
                                    Text("反馈修改", style = MaterialTheme.typography.labelMedium)
                                }
                            }
                        }
                    }

                    // Streaming content with thinking process
                    if (isStreaming) {
                        item {
                            StreamingMessage(
                                streamContent = streamContent,
                                thinkingSteps = uiState.thinkingSteps,
                                searchSources = uiState.searchSources,
                                isSearching = uiState.isSearching,
                                mode = uiState.mode
                            )
                        }
                    }
                }

                // Input bar
                ChatInputBar(
                    input = input,
                    onInputValueChange = { input = it },
                    isStreaming = isStreaming,
                    onSend = { viewModel.sendMessage(it) },
                    onStop = { viewModel.stopGeneration() }
                )
            }

            // Session drawer
            if (showSessionDrawer) {
                SessionDrawer(
                    sessions = currentSessions,
                    activeSessionId = uiState.activeSessionId,
                    mode = uiState.mode,
                    onSelect = { viewModel.selectSession(it); showSessionDrawer = false },
                    onDelete = { viewModel.deleteSession(it) },
                    onNewSession = { viewModel.newSession(); showSessionDrawer = false },
                    onClose = { showSessionDrawer = false }
                )
            }
        }
    }
}

// ── Welcome Message with Quick Questions ─────────────────────

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun WelcomeMessage(mode: ChatMode, onQuickQuestion: (String) -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(vertical = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            Modifier.size(64.dp).clip(CircleShape)
                .background(if (mode == ChatMode.ASSISTANT) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.tertiaryContainer),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                if (mode == ChatMode.ASSISTANT) Icons.Default.AutoAwesome else Icons.Default.School,
                null, modifier = Modifier.size(32.dp),
                tint = if (mode == ChatMode.ASSISTANT) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.tertiary
            )
        }
        Spacer(Modifier.height(16.dp))
        Text(
            if (mode == ChatMode.ASSISTANT) "AI 学习助手" else "智能辅导",
            style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold
        )
        Spacer(Modifier.height(8.dp))
        Text(
            if (mode == ChatMode.ASSISTANT) "我可以帮你解答学习问题、生成学习资源、规划学习路径。" else "我会根据你的学习进度和薄弱点，提供针对性的辅导。",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(horizontal = 32.dp)
        )

        // Quick questions
        Spacer(Modifier.height(24.dp))
        val quickQuestions = if (mode == ChatMode.ASSISTANT) {
            listOf("我想学习 Python 基础", "帮我生成一些练习题", "这个知识点不太理解")
        } else {
            listOf("这个知识点我不太理解，能详细解释一下吗？", "给我出几道练习题", "能给我一些代码示例吗？")
        }
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            quickQuestions.forEach { question ->
                SuggestionChip(
                    onClick = { onQuickQuestion(question) },
                    label = { Text(question, style = MaterialTheme.typography.labelMedium) }
                )
            }
        }
    }
}

// ── Message Bubble ───────────────────────────────────────────

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun MessageBubble(
    message: ChatMessage,
    mode: ChatMode,
    onOpenResource: (Long) -> Unit
) {
    val isUser = message.role.equals(ChatMessage.ROLE_USER, ignoreCase = true) || message.role.equals("USER", ignoreCase = true)
    val displayContent = remember(message.content) { parseMessageContent(message.content) }

    Column {
        // Thinking process (for assistant messages)
        if (!isUser && message.thinkings.isNotEmpty()) {
            ThinkingProcess(thinkings = message.thinkings, isStreaming = false)
            Spacer(Modifier.height(8.dp))
        }

        // Search sources (for tutor messages)
        if (!isUser && message.searchSources.isNotEmpty()) {
            SearchSources(sources = message.searchSources)
            Spacer(Modifier.height(8.dp))
        }

        // Message bubble
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
            verticalAlignment = Alignment.Top
        ) {
            if (!isUser) {
                Box(
                    Modifier.size(32.dp).clip(CircleShape)
                        .background(if (mode == ChatMode.ASSISTANT) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.tertiary),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        if (mode == ChatMode.ASSISTANT) Icons.Default.AutoAwesome else Icons.Default.School,
                        null, modifier = Modifier.size(18.dp),
                        tint = MaterialTheme.colorScheme.onPrimary
                    )
                }
                Spacer(Modifier.width(8.dp))
            }

            Surface(
                shape = RoundedCornerShape(
                    topStart = if (isUser) 16.dp else 4.dp,
                    topEnd = if (isUser) 4.dp else 16.dp,
                    bottomStart = 16.dp,
                    bottomEnd = 16.dp
                ),
                color = if (isUser) {
                    if (mode == ChatMode.ASSISTANT) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.tertiary
                } else {
                    MaterialTheme.colorScheme.surfaceVariant
                },
                tonalElevation = if (isUser) 0.dp else 1.dp
            ) {
                if (isUser) {
                    Text(
                        displayContent,
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
                        when (message.type) {
                            "confirm" -> {
                                Text(displayContent, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                                message.breakdown?.modules?.let { modules ->
                                    Spacer(Modifier.height(8.dp))
                                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                        modules.forEachIndexed { idx, mod ->
                                            Card(
                                                modifier = Modifier.fillMaxWidth(),
                                                shape = RoundedCornerShape(8.dp),
                                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                                            ) {
                                                Column(Modifier.padding(10.dp)) {
                                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                                        Box(
                                                            modifier = Modifier.size(20.dp).clip(CircleShape).background(MaterialTheme.colorScheme.primary),
                                                            contentAlignment = Alignment.Center
                                                        ) {
                                                            Text(
                                                                text = mod.moduleId ?: (idx + 1).toString(),
                                                                style = MaterialTheme.typography.labelSmall,
                                                                color = MaterialTheme.colorScheme.onPrimary
                                                            )
                                                        }
                                                        Spacer(Modifier.width(8.dp))
                                                        Text(mod.title, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                                                        mod.estimatedHours?.let {
                                                            Spacer(Modifier.weight(1f))
                                                            Text("${it}h", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                                                        }
                                                    }
                                                    mod.description?.let {
                                                        Spacer(Modifier.height(4.dp))
                                                        Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                                    }
                                                    if (mod.resources.isNotEmpty()) {
                                                        Spacer(Modifier.height(6.dp))
                                                        FlowRow(
                                                            horizontalArrangement = Arrangement.spacedBy(6.dp),
                                                            verticalArrangement = Arrangement.spacedBy(4.dp)
                                                    ) {
                                                        mod.resources.forEach { r ->
                                                            val label = when (r.resourceType) {
                                                                "quiz" -> "测验"
                                                                "mindmap" -> "思维导图"
                                                                "code" -> "代码示例"
                                                                "summary" -> "总结"
                                                                "pptx" -> "PPT"
                                                                else -> r.resourceType
                                                            }
                                                            Surface(
                                                                shape = RoundedCornerShape(4.dp),
                                                                color = MaterialTheme.colorScheme.primaryContainer,
                                                                contentColor = MaterialTheme.colorScheme.onPrimaryContainer
                                                            ) {
                                                                Text(label, modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp), style = androidx.compose.ui.text.TextStyle(fontSize = 10.sp))
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        "resource_generated" -> {
                            Text(displayContent, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                            if (message.resources.isNotEmpty()) {
                                Spacer(Modifier.height(8.dp))
                                FlowRow(
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    verticalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    message.resources.forEach { r ->
                                        val label = when (r.type) {
                                            "quiz" -> "测验"
                                            "mindmap" -> "思维导图"
                                            "code" -> "代码示例"
                                            "summary" -> "总结"
                                            "pptx" -> "PPT"
                                            else -> r.type
                                        }
                                        Button(
                                            onClick = { onOpenResource(r.id) },
                                            colors = ButtonDefaults.buttonColors(
                                                containerColor = MaterialTheme.colorScheme.secondaryContainer,
                                                contentColor = MaterialTheme.colorScheme.onSecondaryContainer
                                            ),
                                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                                            shape = RoundedCornerShape(8.dp)
                                        ) {
                                            Icon(Icons.Default.Book, null, modifier = Modifier.size(16.dp))
                                            Spacer(Modifier.width(6.dp))
                                            Text("${r.title} ($label)", style = MaterialTheme.typography.bodySmall)
                                        }
                                    }
                                }
                            }
                        }
                        else -> {
                            MarkdownRenderer(content = displayContent)
                        }
                    }
                }
            }
        }
    }
}
}

// ── Streaming Message ────────────────────────────────────────

@Composable
private fun StreamingMessage(
    streamContent: String,
    thinkingSteps: List<ThinkingStep>,
    searchSources: List<SearchSource>,
    isSearching: Boolean,
    mode: ChatMode
) {
    Column {
        // Thinking process
        if (thinkingSteps.isNotEmpty()) {
            ThinkingProcess(thinkings = thinkingSteps, isStreaming = true)
            Spacer(Modifier.height(8.dp))
        }

        // Search sources
        if (searchSources.isNotEmpty() || isSearching) {
            SearchSources(sources = searchSources, isSearching = isSearching)
            Spacer(Modifier.height(8.dp))
        }

        // Streaming content
        Row(verticalAlignment = Alignment.Top) {
            Box(
                Modifier.size(32.dp).clip(CircleShape)
                    .background(if (mode == ChatMode.ASSISTANT) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.tertiary),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    if (mode == ChatMode.ASSISTANT) Icons.Default.AutoAwesome else Icons.Default.School,
                    null, modifier = Modifier.size(18.dp),
                    tint = MaterialTheme.colorScheme.onPrimary
                )
            }
            Spacer(Modifier.width(8.dp))
            if (streamContent.isBlank()) {
                // Typing indicator
                Surface(
                    shape = RoundedCornerShape(4.dp, 16.dp, 16.dp, 16.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Row(Modifier.padding(12.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        repeat(3) {
                            Box(Modifier.size(6.dp).clip(CircleShape).background(MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f)))
                        }
                    }
                }
            } else {
                Surface(
                    shape = RoundedCornerShape(4.dp, 16.dp, 16.dp, 16.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant
                ) {
                    MarkdownRenderer(
                        content = streamContent,
                        modifier = Modifier.padding(12.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun ChatInputBar(
    input: String,
    onInputValueChange: (String) -> Unit,
    isStreaming: Boolean,
    onSend: (String) -> Unit,
    onStop: () -> Unit
) {
    Surface(shadowElevation = 8.dp) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.Bottom
        ) {
            OutlinedTextField(
                value = input,
                onValueChange = onInputValueChange,
                placeholder = { Text("输入问题...") },
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(24.dp),
                maxLines = 4,
                enabled = !isStreaming
            )
            Spacer(Modifier.width(8.dp))
            if (isStreaming) {
                FilledIconButton(onClick = onStop, modifier = Modifier.size(48.dp)) {
                    Icon(Icons.Default.Stop, "停止")
                }
            } else {
                FilledIconButton(
                    onClick = { if (input.isNotBlank()) { onSend(input); onInputValueChange("") } },
                    enabled = input.isNotBlank(),
                    modifier = Modifier.size(48.dp)
                ) {
                    Icon(Icons.AutoMirrored.Filled.Send, "发送")
                }
            }
        }
    }
}

// ── Session Drawer ───────────────────────────────────────────

@Composable
private fun SessionDrawer(
    sessions: List<ChatSession>,
    activeSessionId: String?,
    mode: ChatMode,
    onSelect: (String) -> Unit,
    onDelete: (String) -> Unit,
    onNewSession: () -> Unit,
    onClose: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxHeight().width(300.dp),
        shadowElevation = 8.dp
    ) {
        Column {
            Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text(
                    if (mode == ChatMode.ASSISTANT) "AI助手会话" else "智能辅导会话",
                    style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold
                )
                IconButton(onClick = onClose, modifier = Modifier.size(24.dp)) {
                    Icon(Icons.Default.Close, null, modifier = Modifier.size(18.dp))
                }
            }
            HorizontalDivider()
            LazyColumn(Modifier.weight(1f)) {
                items(sessions) { session ->
                    val isActive = session.sessionId == activeSessionId
                    Row(
                        modifier = Modifier.fillMaxWidth()
                            .background(if (isActive) MaterialTheme.colorScheme.primaryContainer else Color.Transparent)
                            .clickable { onSelect(session.sessionId) }
                            .padding(horizontal = 16.dp, vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            if (mode == ChatMode.ASSISTANT) Icons.Default.ChatBubbleOutline else Icons.Default.School,
                            null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(Modifier.width(12.dp))
                        Column(Modifier.weight(1f)) {
                            Text(session.title.ifEmpty { "对话" }, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            session.updatedAt.takeIf { it.isNotBlank() }?.let {
                                Text(it.take(10), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                        IconButton(onClick = { onDelete(session.sessionId) }, modifier = Modifier.size(24.dp)) {
                            Icon(Icons.Default.Delete, null, modifier = Modifier.size(16.dp), tint = MaterialTheme.colorScheme.error.copy(alpha = 0.6f))
                        }
                    }
                }
            }
            HorizontalDivider()
            TextButton(onClick = onNewSession, modifier = Modifier.fillMaxWidth()) {
                Icon(Icons.Default.Add, null); Spacer(Modifier.width(8.dp)); Text("新建对话")
            }
        }
    }
}

// ── Helpers ──────────────────────────────────────────────────

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
