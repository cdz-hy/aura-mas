package com.aura.mas.ui.tree

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.KnowledgeNode
import com.aura.mas.data.model.KnowledgeTree
import com.aura.mas.data.model.TreeMessage
import com.aura.mas.data.api.ApiService
import com.aura.mas.data.repository.ChatRepository
import com.aura.mas.ui.common.*
import com.aura.mas.util.SseClient
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class TreeUiState(
    val isLoading: Boolean = true,
    val tree: KnowledgeTree? = null,
    val selectedNode: KnowledgeNode? = null,
    val messages: List<TreeMessage> = emptyList(),
    val isStreaming: Boolean = false,
    val streamContent: String = "",
    val showChat: Boolean = false,
    val scale: Float = 1f,
    val offsetX: Float = 0f,
    val offsetY: Float = 0f,
    val error: String? = null
)

@HiltViewModel
class KnowledgeTreeViewModel @Inject constructor(
    private val api: ApiService,
    private val chatRepo: ChatRepository,
    private val sseClient: SseClient
) : ViewModel() {
    private val _uiState = MutableStateFlow(TreeUiState())
    val uiState: StateFlow<TreeUiState> = _uiState.asStateFlow()

    fun loadTree(planId: Long) {
        viewModelScope.launch {
            _uiState.value = TreeUiState(isLoading = true)
            try {
                val result = api.ensureKnowledgeTree(planId)
                if (result.isSuccess && result.data != null) {
                    val treeResult = api.getKnowledgeTree(result.data.id)
                    if (treeResult.isSuccess && treeResult.data != null) {
                        _uiState.value = TreeUiState(tree = treeResult.data, isLoading = false)
                    } else {
                        _uiState.value = TreeUiState(error = treeResult.message, isLoading = false)
                    }
                } else {
                    _uiState.value = TreeUiState(error = result.message, isLoading = false)
                }
            } catch (e: Exception) {
                _uiState.value = TreeUiState(error = e.message, isLoading = false)
            }
        }
    }

    fun selectNode(node: KnowledgeNode) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(selectedNode = node, showChat = true)
            try {
                val result = api.getTreeNodeMessages(node.id)
                if (result.isSuccess && result.data != null) {
                    _uiState.value = _uiState.value.copy(messages = result.data)
                }
            } catch (_: Exception) {}
        }
    }

    fun explainNode(treeId: String, nodeId: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isStreaming = true, streamContent = "")
            try {
                chatRepo.issueTicket()
                val ticket = api.issueTicket().data ?: return@launch
                val baseUrl = com.aura.mas.util.Constants.PYTHON_BASE_URL
                val url = "$baseUrl/api/ai/tree/$treeId/nodes/$nodeId/explain?ticket=$ticket"
                sseClient.connect(url).collect { event ->
                    when (event.type) {
                        "chunk", "stream_text" -> {
                            val data = sseClient.parseEventData(event.data)
                            val text = data?.get("text")?.asString ?: data?.get("content")?.asString ?: ""
                            _uiState.value = _uiState.value.copy(streamContent = _uiState.value.streamContent + text)
                        }
                        "done" -> {
                            _uiState.value = _uiState.value.copy(isStreaming = false)
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

    fun closeChat() {
        _uiState.value = _uiState.value.copy(showChat = false, selectedNode = null, messages = emptyList())
    }

    fun updateTransform(scale: Float, offsetX: Float, offsetY: Float) {
        _uiState.value = _uiState.value.copy(scale = scale, offsetX = offsetX, offsetY = offsetY)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun KnowledgeTreeScreen(
    planId: Long,
    onBack: () -> Unit,
    viewModel: KnowledgeTreeViewModel = hiltViewModel()
) {
    LaunchedEffect(planId) { viewModel.loadTree(planId) }
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = { TopAppBar("知识树", onBack = onBack) }
    ) { padding ->
        if (uiState.isLoading) {
            LoadingIndicator(Modifier.padding(padding))
            return@Scaffold
        }

        val tree = uiState.tree
        if (tree == null) {
            EmptyState(Icons.Filled.Folder, "暂无知识树", modifier = Modifier.padding(padding))
            return@Scaffold
        }

        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            // Tree canvas with pan/zoom
            Box(
                modifier = Modifier.fillMaxSize()
                    .pointerInput(Unit) {
                        detectTransformGestures { _, pan, zoom, _ ->
                            val newScale = (uiState.scale * zoom).coerceIn(0.5f, 3f)
                            viewModel.updateTransform(
                                newScale,
                                uiState.offsetX + pan.x,
                                uiState.offsetY + pan.y
                            )
                        }
                    }
                    .graphicsLayer {
                        scaleX = uiState.scale
                        scaleY = uiState.scale
                        translationX = uiState.offsetX
                        translationY = uiState.offsetY
                    }
            ) {
                TreeCanvas(
                    nodes = tree.nodes,
                    onNodeClick = { viewModel.selectNode(it) }
                )
            }

            // Chat overlay
            if (uiState.showChat) {
                Surface(
                    modifier = Modifier.align(Alignment.BottomCenter).fillMaxWidth().fillMaxHeight(0.5f),
                    shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
                    shadowElevation = 16.dp
                ) {
                    Column {
                        Box(Modifier.fillMaxWidth().padding(top = 8.dp), contentAlignment = Alignment.Center) {
                            Box(Modifier.size(40.dp, 4.dp).clip(RoundedCornerShape(2.dp)).background(MaterialTheme.colorScheme.onSurfaceVariant.copy(0.3f)))
                        }
                        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                            Text(uiState.selectedNode?.label ?: "", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                            Row {
                                IconButton(onClick = {
                                    val node = uiState.selectedNode
                                    if (node != null) viewModel.explainNode(tree.id, node.id)
                                }) { Icon(Icons.Default.AutoAwesome, "AI解释") }
                                IconButton(onClick = { viewModel.closeChat() }, modifier = Modifier.size(24.dp)) {
                                    Icon(Icons.Default.Close, null, modifier = Modifier.size(18.dp))
                                }
                            }
                        }
                        Divider()

                        // Messages + stream
                        LazyColumn(Modifier.weight(1f).padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp), contentPadding = PaddingValues(vertical = 8.dp)) {
                            items(uiState.messages) { msg ->
                                Text(msg.content, style = MaterialTheme.typography.bodySmall)
                            }
                            if (uiState.streamContent.isNotBlank()) {
                                item {
                                    Card(shape = RoundedCornerShape(12.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                                        Text(uiState.streamContent, modifier = Modifier.padding(12.dp), style = MaterialTheme.typography.bodySmall)
                                    }
                                }
                            }
                            if (uiState.isStreaming && uiState.streamContent.isBlank()) {
                                item { CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp) }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TreeCanvas(nodes: List<KnowledgeNode>, onNodeClick: (KnowledgeNode) -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        nodes.forEach { node ->
            TreeNodeCard(node, onNodeClick)
            if (node.children.isNotEmpty()) {
                node.children.forEach { child ->
                    TreeNodeCard(child, onNodeClick, depth = 1)
                    child.children.forEach { grandChild ->
                        TreeNodeCard(grandChild, onNodeClick, depth = 2)
                    }
                }
            }
        }
    }
}

@Composable
private fun TreeNodeCard(node: KnowledgeNode, onClick: (KnowledgeNode) -> Unit, depth: Int = 0) {
    Card(
        modifier = Modifier.padding(start = (depth * 24).dp, top = 4.dp, bottom = 4.dp)
            .clickable { onClick(node) },
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = when (depth) {
                0 -> MaterialTheme.colorScheme.primaryContainer
                1 -> MaterialTheme.colorScheme.secondaryContainer
                else -> MaterialTheme.colorScheme.surfaceVariant
            }
        )
    ) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(24.dp).clip(CircleShape).background(MaterialTheme.colorScheme.primary),
                contentAlignment = Alignment.Center
            ) {
                Text("${depth + 1}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onPrimary)
            }
            Spacer(Modifier.width(8.dp))
            Text(node.label, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
        }
    }
}
