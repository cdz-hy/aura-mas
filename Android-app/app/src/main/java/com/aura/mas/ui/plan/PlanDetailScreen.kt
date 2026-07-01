package com.aura.mas.ui.plan

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.filled.Assistant
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.AddComment
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.api.ApiService
import com.aura.mas.data.model.*
import com.aura.mas.data.repository.ChatRepository
import com.aura.mas.data.repository.PlanRepository
import com.aura.mas.ui.common.*
import com.aura.mas.ui.components.resource.MarkdownRenderer
import com.aura.mas.ui.theme.*
import com.aura.mas.util.SseClient
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject



data class PlanDetailUiState(
    val isLoading: Boolean = true,
    val plan: LearningPlan? = null,
    val resources: List<LearningResource> = emptyList(),
    val selectedResource: LearningResource? = null,
    val progress: List<ResourceProgress> = emptyList(),
    
    // Chat state
    val chatMode: String = "assistant", // "assistant" or "tutor"
    val chatMessages: List<ChatMessage> = emptyList(),
    val chatSessions: List<ChatSession> = emptyList(),
    val isStreaming: Boolean = false,
    val streamContent: String = "",
    val showChat: Boolean = false,
    val showSessionList: Boolean = false,
    
    val showResourceTree: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class PlanDetailViewModel @Inject constructor(
    private val planRepo: PlanRepository,
    private val api: ApiService,
    private val chatRepo: ChatRepository,
    private val sseClient: SseClient
) : ViewModel() {
    private val _uiState = MutableStateFlow(PlanDetailUiState())
    val uiState: StateFlow<PlanDetailUiState> = _uiState.asStateFlow()
    private var planId: Long = 0

    fun loadPlan(id: Long) {
        planId = id
        viewModelScope.launch {
            _uiState.value = PlanDetailUiState(isLoading = true)
            try {
                val planResult = planRepo.getPlan(id)
                val resourcesResult = api.getResourcesByPlan(id)
                val progressResult = planRepo.getProgress(id)

                val resources = resourcesResult.data ?: emptyList()
                val defaultSelected = _uiState.value.selectedResource 
                    ?: resources.firstOrNull { it.status >= LearningResource.STATUS_READY } 
                    ?: resources.firstOrNull()

                _uiState.value = PlanDetailUiState(
                    plan = planResult.data,
                    resources = resources,
                    selectedResource = defaultSelected,
                    progress = progressResult.data ?: emptyList(),
                    isLoading = false
                )

                loadSessions()

                // Check for stuck resources (status=1 generating)
                resources.filter { it.status == LearningResource.STATUS_GENERATING }.forEach { res ->
                    try {
                        val taskResult = api.getTaskByResource(res.id)
                        // Task exists and is running - will be updated via SSE
                    } catch (_: Exception) {}
                }
            } catch (e: Exception) {
                _uiState.value = PlanDetailUiState(error = e.message, isLoading = false)
            }
        }
    }

    private fun loadSessions() {
        viewModelScope.launch {
            try {
                val sessions = if (_uiState.value.chatMode == "assistant") {
                    chatRepo.loadChatSessions(planId)
                } else {
                    chatRepo.loadTutorSessions(planId)
                }
                _uiState.value = _uiState.value.copy(chatSessions = sessions)
                // Auto-load the latest session if no messages are currently shown
                if (sessions.isNotEmpty() && _uiState.value.chatMessages.isEmpty()) {
                    val latest = sessions.firstOrNull()
                    if (latest != null) {
                        try {
                            val messagesResult = chatRepo.getMessages(latest.sessionId)
                            _uiState.value = _uiState.value.copy(
                                chatMessages = messagesResult.data ?: emptyList()
                            )
                        } catch (_: Exception) {}
                    }
                }
            } catch (_: Exception) {}
        }
    }

    fun selectResource(resource: LearningResource) {
        _uiState.value = _uiState.value.copy(selectedResource = resource)
    }

    fun toggleChat() {
        _uiState.value = _uiState.value.copy(showChat = !_uiState.value.showChat)
    }
    
    fun toggleResourceTree() {
        _uiState.value = _uiState.value.copy(showResourceTree = !_uiState.value.showResourceTree)
    }
    
    fun toggleChatMode() {
        val currentMode = _uiState.value.chatMode
        val newMode = if (currentMode == "assistant") "tutor" else "assistant"
        _uiState.value = _uiState.value.copy(
            chatMode = newMode,
            chatMessages = emptyList(), // Clear messages on mode switch
            showSessionList = false
        )
        loadSessions()
    }

    fun selectSession(session: ChatSession) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(showSessionList = false, isStreaming = true)
            try {
                val messagesResult = chatRepo.getMessages(session.sessionId)
                _uiState.value = _uiState.value.copy(
                    chatMessages = messagesResult.data ?: emptyList(),
                    isStreaming = false
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isStreaming = false)
            }
        }
    }
    
    fun toggleSessionList() {
        _uiState.value = _uiState.value.copy(showSessionList = !_uiState.value.showSessionList)
    }
    
    fun newSession() {
        val sessionId = if (_uiState.value.chatMode == "tutor") {
            chatRepo.generateTutorSessionId(planId)
        } else {
            chatRepo.generateChatSessionId()
        }
        _uiState.value = _uiState.value.copy(
            chatMessages = emptyList(),
            showSessionList = false
        )
    }

    fun sendMessage(message: String) {
        if (message.isBlank()) return
        val currentMode = _uiState.value.chatMode

        viewModelScope.launch {
            val sessionId = if (currentMode == "tutor") {
                chatRepo.generateTutorSessionId(planId)
            } else {
                chatRepo.generateChatSessionId()
            }
            val userMsg = ChatMessage(role = ChatMessage.ROLE_USER, content = message)
            _uiState.value = _uiState.value.copy(
                chatMessages = _uiState.value.chatMessages + userMsg,
                isStreaming = true,
                streamContent = ""
            )
            try {
                val flow = if (currentMode == "tutor") {
                    val resourceId = _uiState.value.selectedResource?.id
                    chatRepo.tutorChat(sessionId, message, planId, resourceId)
                } else {
                    chatRepo.chat(sessionId, message, planId)
                }
                flow.collect { event ->
                    when (event.type) {
                        "chunk", "stream_text" -> {
                            val data = sseClient.parseEventData(event.data)
                            val text = data?.get("text")?.asString ?: data?.get("content")?.asString ?: ""
                            _uiState.value = _uiState.value.copy(
                                streamContent = _uiState.value.streamContent + text
                            )
                        }
                        "resource_generated", "resource_type_generated" -> {
                            loadPlan(planId)
                        }
                        "done" -> {
                            val content = _uiState.value.streamContent
                            if (content.isNotBlank()) {
                                val assistantMsg = ChatMessage(role = ChatMessage.ROLE_ASSISTANT, content = content)
                                _uiState.value = _uiState.value.copy(
                                    chatMessages = _uiState.value.chatMessages + assistantMsg,
                                    streamContent = "",
                                    isStreaming = false
                                )
                            } else {
                                _uiState.value = _uiState.value.copy(isStreaming = false)
                            }
                        }
                        "error" -> {
                            _uiState.value = _uiState.value.copy(isStreaming = false)
                        }
                    }
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isStreaming = false)
            }
        }
    }

    fun generateResource(type: String) {
        val resource = _uiState.value.selectedResource ?: return
        val msg = "请为模块「${resource.getModuleName()}」生成补充资源: $type"
        sendMessage(msg)
    }

    fun markComplete(resourceId: Long) {
        viewModelScope.launch {
            planRepo.markComplete(planId, resourceId)
            loadPlan(planId)
        }
    }

    fun retryTask(resourceId: Long) {
        viewModelScope.launch {
            try {
                val task = api.getTaskByResource(resourceId)
                if (task.code == 0 && task.data != null) {
                    api.retryTask(task.data.id)
                }
            } catch (_: Exception) {}
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlanDetailScreen(
    planId: Long,
    onBack: () -> Unit,
    viewModel: PlanDetailViewModel = hiltViewModel()
) {
    LaunchedEffect(planId) { viewModel.loadPlan(planId) }
    val uiState by viewModel.uiState.collectAsState()

    if (uiState.isLoading) {
        Scaffold(topBar = { TopAppBar("加载中...", onBack = onBack) }) { LoadingIndicator(Modifier.padding(it)) }
        return
    }

    val plan = uiState.plan
    if (plan == null) {
        Scaffold(topBar = { TopAppBar("错误", onBack = onBack) }) {
            EmptyState(Icons.Default.Error, "计划不存在", modifier = Modifier.padding(it))
        }
        return
    }

    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    Scaffold(
        topBar = {
            TopAppBar(
                title = plan.title,
                onBack = onBack,
                actions = {
                    val completed = uiState.progress.count { it.completed }
                    val total = uiState.resources.count { it.status >= LearningResource.STATUS_READY }.coerceAtLeast(1)
                    val percent = (completed * 100 / total)
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.primaryContainer,
                        modifier = Modifier.padding(end = 8.dp)
                    ) {
                        Text(
                            "进度 $percent%",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                        )
                    }
                    IconButton(onClick = { viewModel.toggleResourceTree() }) {
                        Icon(Icons.Default.Menu, "知识树")
                    }
                }
            )
        },
        floatingActionButton = {
            if (!uiState.showChat) {
                FloatingActionButton(
                    onClick = { viewModel.toggleChat() },
                    shape = CircleShape,
                    containerColor = MaterialTheme.colorScheme.primary
                ) {
                    Icon(Icons.Default.Chat, "AI助手", tint = MaterialTheme.colorScheme.onPrimary)
                }
            }
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding).background(MaterialTheme.colorScheme.background)) {
            // Main Content: Full-screen Resource Viewer
            val selected = uiState.selectedResource
            if (selected != null) {
                Column(
                    modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)
                ) {
                    ResourceContentView(selected)
                }
            } else {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("暂无资源可浏览", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }

            // Chat bottom sheet
            if (uiState.showChat) {
                ModalBottomSheet(
                    onDismissRequest = { viewModel.toggleChat() },
                    sheetState = sheetState,
                    containerColor = MaterialTheme.colorScheme.surface,
                    dragHandle = { BottomSheetDefaults.DragHandle() }
                ) {
                    ChatPanel(
                        uiState = uiState,
                        onSend = { viewModel.sendMessage(it) },
                        onClose = { viewModel.toggleChat() },
                        onToggleMode = { viewModel.toggleChatMode() },
                        onToggleSessions = { viewModel.toggleSessionList() },
                        onNewSession = { viewModel.newSession() },
                        onSelectSession = { viewModel.selectSession(it) },
                        onGenerateResource = { viewModel.generateResource(it) },
                        modifier = Modifier.fillMaxWidth().fillMaxHeight(0.85f)
                    )
                }
            }
            
            // Resource Tree bottom sheet
            if (uiState.showResourceTree) {
                ModalBottomSheet(
                    onDismissRequest = { viewModel.toggleResourceTree() },
                    sheetState = sheetState,
                    containerColor = MaterialTheme.colorScheme.surface,
                    dragHandle = { BottomSheetDefaults.DragHandle() }
                ) {
                    ResourceTreePanel(
                        resources = uiState.resources,
                        progress = uiState.progress,
                        selectedResource = uiState.selectedResource,
                        onResourceClick = { 
                            viewModel.selectResource(it)
                            viewModel.toggleResourceTree()
                        },
                        onComplete = { viewModel.markComplete(it) },
                        onRetry = { viewModel.retryTask(it) }
                    )
                }
            }
        }
    }
}

@Composable
private fun ResourceTreePanel(
    resources: List<LearningResource>,
    progress: List<ResourceProgress>,
    selectedResource: LearningResource?,
    onResourceClick: (LearningResource) -> Unit,
    onComplete: (Long) -> Unit,
    onRetry: (Long) -> Unit
) {
    Column(modifier = Modifier.fillMaxWidth().fillMaxHeight(0.85f)) {
        Text(
            "学习大纲",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(start = 24.dp, end = 24.dp, bottom = 8.dp)
        )
        HorizontalDivider()
        LazyColumn(
            modifier = Modifier.fillMaxWidth().weight(1f),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            val grouped = resources.groupBy { it.moduleOrder }.toSortedMap()
            grouped.forEach { (moduleOrder, moduleResources) ->
                item(key = "module_$moduleOrder") {
                    val moduleTitle = moduleResources.firstOrNull()?.getModuleName()?.ifEmpty { "模块 $moduleOrder" } ?: "模块 $moduleOrder"
                    Text(
                        moduleTitle,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(top = 8.dp, bottom = 4.dp)
                    )
                }
                items(moduleResources, key = { it.id }) { resource ->
                    ResourceItem(
                        resource = resource,
                        isCompleted = progress.any { it.resourceId == resource.id && it.completed },
                        isSelected = selectedResource?.id == resource.id,
                        onClick = { onResourceClick(resource) },
                        onComplete = { onComplete(resource.id) },
                        onRetry = { onRetry(resource.id) }
                    )
                }
            }
        }
    }
}
@Composable
private fun ResourceItem(
    resource: LearningResource,
    isCompleted: Boolean,
    isSelected: Boolean,
    onClick: () -> Unit,
    onComplete: () -> Unit,
    onRetry: () -> Unit
) {
    val isGenerating = resource.status == LearningResource.STATUS_GENERATING
    val isReady = resource.status >= LearningResource.STATUS_READY

    Card(
        modifier = Modifier.fillMaxWidth().clickable(enabled = isReady) { onClick() },
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = when {
                isSelected -> MaterialTheme.colorScheme.primaryContainer
                isGenerating -> MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.5f)
                else -> MaterialTheme.colorScheme.surface
            }
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = if (isSelected) 2.dp else 0.5.dp)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Icon
            Box(
                modifier = Modifier.size(36.dp).clip(RoundedCornerShape(8.dp))
                    .background(
                        if (isCompleted) Sage100
                        else if (isGenerating) MaterialTheme.colorScheme.tertiaryContainer
                        else MaterialTheme.colorScheme.surfaceVariant
                    ),
                contentAlignment = Alignment.Center
            ) {
                if (isGenerating) {
                    CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.tertiary)
                } else {
                    Icon(
                        if (isCompleted) Icons.Default.CheckCircle else getResourceIcon(resource.moduleType),
                        null,
                        tint = if (isCompleted) Sage500 else MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    resource.getResourceTitle().ifEmpty { resource.getModuleName() },
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Row {
                    Text(
                        getResourceTypeName(resource.moduleType),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    if (isGenerating) {
                        Spacer(Modifier.width(8.dp))
                        Text(
                            "生成中...",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.tertiary
                        )
                    }
                }
            }
            if (isReady && !isCompleted) {
                IconButton(onClick = onComplete, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.CheckCircleOutline, "完成", modifier = Modifier.size(18.dp))
                }
            }
            if (isGenerating) {
                IconButton(onClick = onRetry, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.Refresh, "重试", modifier = Modifier.size(18.dp))
                }
            }
        }
    }
}

@Composable
private fun ResourceContentView(resource: LearningResource) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Type badge
            Surface(
                shape = RoundedCornerShape(20.dp),
                color = MaterialTheme.colorScheme.primaryContainer
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        getResourceIcon(resource.moduleType),
                        null,
                        modifier = Modifier.size(14.dp),
                        tint = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        getResourceTypeName(resource.moduleType),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }
            }

            Spacer(Modifier.height(12.dp))

            // Title
            Text(
                resource.getResourceTitle().ifEmpty { resource.getModuleName() },
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(Modifier.height(16.dp))

            // Content based on type
            when (resource.moduleType) {
                "quiz" -> {
                    QuizContentView(resource)
                }
                "mindmap" -> {
                    MindmapContentView(resource)
                }
                "video" -> {
                    VideoContentView(resource)
                }
                "podcast" -> {
                    PodcastContentView(resource)
                }
                "pptx" -> {
                    PptxContentView(resource)
                }
                "animation" -> {
                    AnimationContentView(resource)
                }
                else -> {
                    // Document, reading, summary, code, etc. - render as markdown
                    DocumentContentView(resource)
                }
            }
        }
    }
}

@Composable
private fun DocumentContentView(resource: LearningResource) {
    val content = resource.getContent()
    if (content.isBlank()) {
        if (resource.status == LearningResource.STATUS_GENERATING) {
            GeneratingPlaceholder()
        } else {
            Text("暂无内容", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        return
    }

    // Strip citation/references section
    val cleanContent = stripCitationSection(content)

    MarkdownRenderer(
        content = cleanContent,
        modifier = Modifier.fillMaxWidth()
    )
}

@Composable
private fun QuizContentView(resource: LearningResource) {
    val questions = resource.getQuizQuestions()
    if (questions.isEmpty()) {
        if (resource.status == LearningResource.STATUS_GENERATING) {
            GeneratingPlaceholder()
        } else {
            Text("暂无测验题目", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        return
    }

    Column {
        Text("共 ${questions.size} 题", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(8.dp))
        questions.forEachIndexed { index, question ->
            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)
            ) {
                Column(Modifier.padding(12.dp)) {
                    Text("${index + 1}. ${question.questionText}", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                    question.options?.forEach { option ->
                        Text("  • $option", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    }
}

@Composable
private fun MindmapContentView(resource: LearningResource) {
    val mindmapData = resource.getMindmapData()
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer)
    ) {
        Column(Modifier.padding(16.dp)) {
            Icon(Icons.Default.Folder, null, tint = MaterialTheme.colorScheme.tertiary, modifier = Modifier.size(32.dp))
            Spacer(Modifier.height(8.dp))
            Text("思维导图", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(8.dp))
            if (mindmapData != null) {
                Text(mindmapData.toString().take(200), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onTertiaryContainer)
            } else {
                Text("思维导图数据加载中", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onTertiaryContainer.copy(alpha = 0.7f))
            }
        }
    }
}

@Composable
private fun VideoContentView(resource: LearningResource) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(Icons.Default.PlayCircle, null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(12.dp))
            Text("视频资源", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text("点击播放视频内容", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun PodcastContentView(resource: LearningResource) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(Icons.Default.Headphones, null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(12.dp))
            Text("播客音频", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { }) { Icon(Icons.Default.SkipPrevious, null) }
                FilledIconButton(onClick = { }, modifier = Modifier.size(56.dp)) {
                    Icon(Icons.Default.PlayArrow, null, modifier = Modifier.size(32.dp))
                }
                IconButton(onClick = { }) { Icon(Icons.Default.SkipNext, null) }
            }
        }
    }
}

@Composable
private fun PptxContentView(resource: LearningResource) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(Icons.Default.Slideshow, null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(12.dp))
            Text("演示文稿", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text("点击查看 PPT 内容", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun AnimationContentView(resource: LearningResource) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(Icons.Default.Animation, null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(12.dp))
            Text("动画资源", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun GeneratingPlaceholder() {
    Column(
        modifier = Modifier.fillMaxWidth().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        CircularProgressIndicator(modifier = Modifier.size(32.dp), strokeWidth = 3.dp)
        Spacer(Modifier.height(12.dp))
        Text("内容生成中...", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(4.dp))
        Text("AI 正在为你生成学习资源，请稍候", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f))
    }
}

@Composable
private fun ChatPanel(
    uiState: PlanDetailUiState,
    onSend: (String) -> Unit,
    onClose: () -> Unit,
    onToggleMode: () -> Unit,
    onToggleSessions: () -> Unit,
    onNewSession: () -> Unit,
    onSelectSession: (ChatSession) -> Unit,
    onGenerateResource: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var input by remember { mutableStateOf("") }
    val isAssistant = uiState.chatMode == "assistant"
    val listState = androidx.compose.foundation.lazy.rememberLazyListState()

    // Auto-scroll to bottom when messages change or streaming
    val totalItems = uiState.chatMessages.size + (if (uiState.isStreaming) 1 else 0)
    LaunchedEffect(totalItems) {
        if (totalItems > 0) {
            listState.animateScrollToItem(totalItems - 1)
        }
    }
    
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            // Drag handle
            Box(Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 4.dp), contentAlignment = Alignment.Center) {
                Box(Modifier.size(width = 36.dp, height = 4.dp).clip(CircleShape).background(MaterialTheme.colorScheme.outlineVariant))
            }

            // Header
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Mode Toggle
                Surface(
                    shape = RoundedCornerShape(20.dp),
                    color = if (isAssistant) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.tertiaryContainer,
                    modifier = Modifier.clickable { onToggleMode() }
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            if (isAssistant) Icons.Default.Assistant else Icons.Default.School,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp),
                            tint = if (isAssistant) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onTertiaryContainer
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            if (isAssistant) "AI 学习助手" else "智能辅导",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = if (isAssistant) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onTertiaryContainer
                        )
                        Spacer(Modifier.width(4.dp))
                        Icon(Icons.Default.SwapHoriz, null, modifier = Modifier.size(14.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                
                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Session history button with count badge
                    Box {
                        IconButton(onClick = onToggleSessions, modifier = Modifier.size(36.dp)) {
                            Icon(Icons.Default.History, "历史会话", modifier = Modifier.size(20.dp))
                        }
                        if (uiState.chatSessions.isNotEmpty()) {
                            Surface(
                                modifier = Modifier.align(Alignment.TopEnd).size(16.dp),
                                shape = CircleShape,
                                color = MaterialTheme.colorScheme.primary
                            ) {
                                Box(contentAlignment = Alignment.Center) {
                                    Text(
                                        uiState.chatSessions.size.coerceAtMost(99).toString(),
                                        style = MaterialTheme.typography.labelSmall,
                                        fontSize = 8.sp,
                                        color = MaterialTheme.colorScheme.onPrimary
                                    )
                                }
                            }
                        }
                    }
                    IconButton(onClick = onNewSession, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Default.AddComment, "新建", modifier = Modifier.size(20.dp))
                    }
                    IconButton(onClick = onClose, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Default.Close, "关闭", modifier = Modifier.size(20.dp))
                    }
                }
            }
            
            if (uiState.showSessionList) {
                LazyColumn(
                    modifier = Modifier.fillMaxWidth().heightIn(max = 200.dp)
                        .background(MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    items(uiState.chatSessions) { session ->
                        Row(
                            modifier = Modifier.fillMaxWidth()
                                .clickable { onSelectSession(session) }
                                .padding(horizontal = 16.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                Modifier.size(28.dp).clip(RoundedCornerShape(8.dp))
                                    .background(MaterialTheme.colorScheme.primary),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(Icons.Default.ChatBubbleOutline, null,
                                    modifier = Modifier.size(14.dp),
                                    tint = MaterialTheme.colorScheme.onPrimary)
                            }
                            Spacer(Modifier.width(12.dp))
                            Column(Modifier.weight(1f)) {
                                Text(session.title.ifBlank { "对话" },
                                    style = MaterialTheme.typography.bodySmall,
                                    fontWeight = FontWeight.Medium,
                                    maxLines = 1,
                                    overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                                if (session.updatedAt.isNotBlank()) {
                                    Text(session.updatedAt.take(16).replace("T", " "),
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    }
                }
            }
            
            HorizontalDivider()

            // Messages list
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                contentPadding = PaddingValues(vertical = 12.dp)
            ) {
                // Welcome Message
                if (uiState.chatMessages.isEmpty() && !uiState.isStreaming) {
                    item {
                        if (isAssistant) {
                            AssistantWelcome(onSend)
                        } else {
                            TutorWelcome(uiState.selectedResource?.getResourceTitle())
                        }
                    }
                }
                
                items(uiState.chatMessages) { msg -> 
                    ChatBubble(msg, isAssistant) 
                }
                
                if (uiState.isStreaming && uiState.streamContent.isNotBlank()) {
                    item {
                        ChatBubble(ChatMessage(role = ChatMessage.ROLE_ASSISTANT, content = uiState.streamContent), isAssistant)
                    }
                } else if (uiState.isStreaming) {
                    item {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(Modifier.size(32.dp).clip(RoundedCornerShape(8.dp))
                                .background(if (isAssistant) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.tertiary),
                                contentAlignment = Alignment.Center) {
                                Icon(if (isAssistant) Icons.Default.AutoAwesome else Icons.Default.School,
                                    null, tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(18.dp))
                            }
                            Spacer(Modifier.width(8.dp))
                            // Animated typing dots
                            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                repeat(3) { i ->
                                    androidx.compose.runtime.key(i) {
                                        Box(
                                            Modifier.size(8.dp).clip(CircleShape)
                                                .background(MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f))
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
                
                // Context Prompt at the bottom if Assistant and selectedResource exists
                if (isAssistant && !uiState.isStreaming && uiState.selectedResource != null) {
                    item {
                        ContextPrompt(uiState.selectedResource.getResourceTitle().ifEmpty { uiState.selectedResource.getModuleName() }, onGenerateResource)
                    }
                }
                
                // Tutor follow up at the bottom
                if (!isAssistant && !uiState.isStreaming && uiState.chatMessages.isNotEmpty()) {
                    item {
                        TutorWelcome(uiState.selectedResource?.getResourceTitle())
                    }
                }
            }

            // Input
            Row(
                modifier = Modifier.fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surface)
                    .padding(horizontal = 12.dp, vertical = 8.dp)
                    .navigationBarsPadding(),
                verticalAlignment = Alignment.Bottom
            ) {
                OutlinedTextField(
                    value = input, 
                    onValueChange = { input = it },
                    placeholder = { Text(if (isAssistant) "描述你想学习的内容..." else "输入你的问题...") },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(20.dp),
                    maxLines = 4,
                    enabled = !uiState.isStreaming
                )
                Spacer(Modifier.width(8.dp))
                FilledIconButton(
                    onClick = { if (input.isNotBlank()) { onSend(input); input = "" } },
                    enabled = input.isNotBlank() && !uiState.isStreaming,
                    modifier = Modifier.size(48.dp),
                    shape = CircleShape,
                    colors = IconButtonDefaults.filledIconButtonColors(
                        containerColor = if (isAssistant) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.tertiary
                    )
                ) {
                    Icon(Icons.AutoMirrored.Filled.Send, null)
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun AssistantWelcome(onSend: (String) -> Unit) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Start) {
        Box(Modifier.size(32.dp).clip(RoundedCornerShape(8.dp)).background(MaterialTheme.colorScheme.primary), contentAlignment = Alignment.Center) {
            Icon(Icons.Default.AutoAwesome, null, tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(18.dp))
        }
        Spacer(Modifier.width(8.dp))
        Surface(
            shape = RoundedCornerShape(topStart = 4.dp, topEnd = 16.dp, bottomStart = 16.dp, bottomEnd = 16.dp),
            color = MaterialTheme.colorScheme.surfaceVariant
        ) {
            Column(Modifier.padding(12.dp)) {
                Text("你好！请告诉我你想学习什么，我会为你规划学习路径并生成个性化资源。", style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(8.dp))
                val quicks = listOf("我想学习 Python 基础", "帮我生成一些练习题", "这个知识点不太理解")
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    quicks.forEach { q ->
                        Surface(
                            shape = CircleShape,
                            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                            color = MaterialTheme.colorScheme.surface,
                            modifier = Modifier.clickable { onSend(q) }
                        ) {
                            Text(q, modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ContextPrompt(title: String, onGenerate: (String) -> Unit) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Start) {
        Box(Modifier.size(32.dp).clip(RoundedCornerShape(8.dp)).background(MaterialTheme.colorScheme.primary), contentAlignment = Alignment.Center) {
            Icon(Icons.Default.AutoAwesome, null, tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(18.dp))
        }
        Spacer(Modifier.width(8.dp))
        Surface(
            shape = RoundedCornerShape(topStart = 4.dp, topEnd = 16.dp, bottomStart = 16.dp, bottomEnd = 16.dp),
            color = MaterialTheme.colorScheme.surfaceVariant
        ) {
            Column(Modifier.padding(12.dp)) {
                Text("你正在查看「${title}」，如需为该模块生成补充资源，请点击：", style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(8.dp))
                val opts = listOf("测验" to "quiz", "思维导图" to "mindmap", "代码示例" to "code", "总结" to "summary", "PPT" to "pptx")
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    opts.forEach { (label, type) ->
                        Surface(
                            shape = CircleShape,
                            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                            color = MaterialTheme.colorScheme.surface,
                            modifier = Modifier.clickable { onGenerate(type) }
                        ) {
                            Text(label, modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TutorWelcome(resourceTitle: String?) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Start) {
        Box(Modifier.size(32.dp).clip(RoundedCornerShape(8.dp)).background(MaterialTheme.colorScheme.tertiary), contentAlignment = Alignment.Center) {
            Icon(Icons.Default.School, null, tint = MaterialTheme.colorScheme.onTertiary, modifier = Modifier.size(18.dp))
        }
        Spacer(Modifier.width(8.dp))
        Surface(
            shape = RoundedCornerShape(topStart = 4.dp, topEnd = 16.dp, bottomStart = 16.dp, bottomEnd = 16.dp),
            color = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha=0.5f)
        ) {
            Text("关于${resourceTitle?.let { "「$it」" } ?: "当前内容"}，有什么不懂的地方吗？我可以帮你哦", modifier = Modifier.padding(12.dp), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
        }
    }
}

@Composable
private fun ChatBubble(message: ChatMessage, isAssistant: Boolean) {
    val isUser = message.role == ChatMessage.ROLE_USER
    val displayContent = remember(message.content) { parseMessageContent(message.content) }

    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start) {
        if (!isUser) {
            Box(Modifier.size(32.dp).clip(RoundedCornerShape(8.dp)).background(if (isAssistant) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.tertiary), contentAlignment = Alignment.Center) {
                Icon(if (isAssistant) Icons.Default.AutoAwesome else Icons.Default.School, null, tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.width(8.dp))
        }
        Surface(
            shape = RoundedCornerShape(topStart = if (isUser) 16.dp else 4.dp, topEnd = if (isUser) 4.dp else 16.dp, bottomStart = 16.dp, bottomEnd = 16.dp),
            color = if (isUser) (if(isAssistant) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.tertiary) else MaterialTheme.colorScheme.surfaceVariant,
            tonalElevation = if (isUser) 0.dp else 1.dp
        ) {
            if (isUser) {
                Text(displayContent, modifier = Modifier.padding(12.dp), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onPrimary)
            } else {
                Column(Modifier.padding(12.dp)) {
                    // Strip citation sections before rendering
                    val cleanContent = remember(displayContent) { stripCitationSection(displayContent) }
                    MarkdownRenderer(content = cleanContent)
                }
            }
        }
    }
}

/**
 * Parse message content - handles both plain text and JSON-encoded content.
 * Matches Vue frontend's extractTextSegments() logic.
 */
private fun parseMessageContent(content: String): String {
    if (content.isBlank()) return ""
    val trimmed = content.trim()

    // Not JSON-like, return as plain text
    if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return trimmed

    return try {
        val json = com.google.gson.Gson().fromJson(trimmed, com.google.gson.JsonElement::class.java)
        when {
            json.isJsonObject -> extractTextFromObject(json.asJsonObject)
            json.isJsonArray -> extractTextFromArray(json.asJsonArray)
            else -> trimmed
        }
    } catch (_: Exception) {
        // Not valid JSON (e.g., code snippet starting with {), return as-is
        trimmed
    }
}

private fun extractTextFromObject(obj: com.google.gson.JsonObject): String {
    // Priority 1: conversationText (Java backend field name)
    obj.get("conversationText")?.asString?.let { if (it.isNotBlank()) return it }

    // Priority 2: content / text / message
    obj.get("content")?.asString?.let { if (it.isNotBlank()) return it }
    obj.get("text")?.asString?.let { if (it.isNotBlank()) return it }
    obj.get("message")?.asString?.let { if (it.isNotBlank()) return it }

    // Priority 3: Nested data object
    obj.getAsJsonObject("data")?.let { data ->
        extractTextFromObject(data).let { if (it != data.toString()) return it }
    }
    obj.getAsJsonObject("generated_content")?.let { gc ->
        extractTextFromObject(gc).let { if (it != gc.toString()) return it }
    }

    // Priority 4: segments / parts array
    val segments = obj.getAsJsonArray("segments")
        ?: obj.getAsJsonArray("parts")
        ?: obj.getAsJsonArray("messages")
    if (segments != null) return extractTextFromArray(segments)

    // Fallback: return the raw JSON string (will be rendered as-is)
    return obj.toString()
}

private fun extractTextFromArray(arr: com.google.gson.JsonArray): String {
    return arr.mapNotNull { element ->
        when {
            element.isJsonObject -> {
                val obj = element.asJsonObject
                obj.get("content")?.asString
                    ?: obj.get("text")?.asString
                    ?: obj.get("message")?.asString
                    ?: obj.get("conversationText")?.asString
            }
            element.isJsonPrimitive -> element.asString
            else -> null
        }
    }.filter { it.isNotBlank() }.joinToString("\n")
}

private fun stripCitationSection(content: String): String {
    val headers = listOf("## 参考文献", "### 参考文献", "## 参考资料", "### 参考资料", "## 引用文献", "### 引用文献")
    for (header in headers) {
        val idx = content.indexOf(header)
        if (idx != -1) {
            return content.substring(0, idx).trim()
        }
    }
    return content
}

private fun getResourceIcon(type: String) = when (type) {
    "document", "reading" -> Icons.Outlined.Description
    "summary" -> Icons.Outlined.Summarize
    "mindmap" -> Icons.Filled.Folder
    "quiz" -> Icons.Outlined.Quiz
    "code" -> Icons.Outlined.Code
    "video" -> Icons.Filled.PlayCircle
    "podcast" -> Icons.Filled.Headphones
    "pptx" -> Icons.Filled.Slideshow
    "animation" -> Icons.Filled.Animation
    else -> Icons.Outlined.Article
}

private fun getResourceTypeName(type: String) = when (type) {
    "document" -> "文档"
    "reading" -> "阅读材料"
    "summary" -> "摘要"
    "mindmap" -> "思维导图"
    "quiz" -> "测验"
    "code" -> "代码"
    "video" -> "视频"
    "podcast" -> "播客"
    "pptx" -> "演示文稿"
    "animation" -> "动画"
    else -> "资源"
}
