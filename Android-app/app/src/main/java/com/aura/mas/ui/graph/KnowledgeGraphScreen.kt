package com.aura.mas.ui.graph

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Hub
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.api.ApiService
import com.aura.mas.data.model.UserKnowledgeDomain
import com.aura.mas.data.model.KnowledgeGraphNode
import com.aura.mas.ui.common.LoadingIndicator
import com.aura.mas.ui.common.TopAppBar
import com.aura.mas.ui.components.graph.KnowledgeGraphView
import com.aura.mas.ui.theme.Amber500
import com.aura.mas.ui.theme.Sage500
import com.google.gson.Gson
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class GraphUiState(
    val isLoading: Boolean = true,
    val domains: List<UserKnowledgeDomain> = emptyList(),
    val selectedDomain: UserKnowledgeDomain? = null,
    val graphJson: String = "",
    val selectedNode: KnowledgeGraphNode? = null,
    val error: String? = null
)

@HiltViewModel
class KnowledgeGraphViewModel @Inject constructor(
    private val api: ApiService
) : ViewModel() {
    private val _uiState = MutableStateFlow(GraphUiState())
    val uiState: StateFlow<GraphUiState> = _uiState.asStateFlow()
    private val gson = Gson()

    fun loadGraph(userId: Long) {
        viewModelScope.launch {
            _uiState.value = GraphUiState(isLoading = true)
            try {
                android.util.Log.d("KGViewModel", "loadGraph called with userId=$userId")
                val response = api.getKnowledgeDomains(userId)
                android.util.Log.d("KGViewModel", "getKnowledgeDomains response: code=${response.code}, dataSize=${response.data?.size}, message=${response.message}")
                if (response.isSuccess && !response.data.isNullOrEmpty()) {
                    val domains = response.data
                    _uiState.value = _uiState.value.copy(domains = domains, isLoading = false, error = null)
                    selectDomain(domains.first().id)
                } else {
                    // No domains yet — this is NOT an error, just empty
                    _uiState.value = GraphUiState(
                        isLoading = false,
                        error = null  // null error + empty domains → triggers "暂无知识图谱" EmptyState
                    )
                }
            } catch (e: Exception) {
                android.util.Log.e("KGViewModel", "loadGraph error", e)
                _uiState.value = GraphUiState(error = e.message ?: "获取图谱失败", isLoading = false)
            }
        }
    }

    fun selectDomain(domainId: Long) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, selectedNode = null)
            try {
                val response = api.getDomainGraph(domainId)
                if (response.isSuccess && response.data != null) {
                    val domainDetails = response.data
                    // graphData comes from the backend as a raw JSON Object (LinkedTreeMap).
                    // We serialize whatever it is back to a JSON string for the WebView.
                    val graphDataRaw = domainDetails.graphData
                    val graphJson = if (graphDataRaw != null) {
                        gson.toJson(graphDataRaw)
                    } else {
                        """{"nodes":[],"edges":[]}"""
                    }

                    android.util.Log.d("KGViewModel", "graphJson length=${graphJson.length}, preview=${graphJson.take(200)}")

                    _uiState.value = _uiState.value.copy(
                        selectedDomain = domainDetails,
                        graphJson = graphJson,
                        isLoading = false,
                        error = null
                    )
                } else {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = if (response.message.isNotBlank()) response.message else "加载域图谱失败"
                    )
                }
            } catch (e: Exception) {
                android.util.Log.e("KGViewModel", "selectDomain error", e)
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "加载域图谱失败"
                )
            }
        }
    }

    fun selectNode(nodeId: String) {
        // Parse nodes from graphJson since graphData may be a LinkedTreeMap
        try {
            val jsonObj = com.google.gson.JsonParser.parseString(_uiState.value.graphJson).asJsonObject
            val nodesArr = jsonObj.getAsJsonArray("nodes")
            nodesArr?.forEach { elem ->
                val obj = elem.asJsonObject
                if (obj.get("id")?.asString == nodeId) {
                    val node = KnowledgeGraphNode(
                        id = obj.get("id")?.asString ?: "",
                        name = obj.get("name")?.asString ?: "",
                        description = obj.get("description")?.asString,
                        masteryLevel = obj.get("mastery_level")?.asFloat,
                        importance = obj.get("importance")?.asFloat
                    )
                    _uiState.value = _uiState.value.copy(selectedNode = node)
                    return
                }
            }
        } catch (e: Exception) {
            android.util.Log.e("KGViewModel", "selectNode parse error", e)
        }
    }

    fun clearSelectedNode() {
        _uiState.value = _uiState.value.copy(selectedNode = null)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun KnowledgeGraphScreen(
    userId: Long,
    onBack: () -> Unit,
    onNavigateToNote: (Long) -> Unit,
    onNavigateToQuiz: (Long) -> Unit,
    viewModel: KnowledgeGraphViewModel = hiltViewModel()
) {
    val isDark = isSystemInDarkTheme()
    
    LaunchedEffect(userId) {
        viewModel.loadGraph(userId)
    }
    
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = { TopAppBar("知识图谱", onBack = onBack) }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .background(MaterialTheme.colorScheme.background)
        ) {
            Column(modifier = Modifier.fillMaxSize()) {
                // Domain Tabs if multiple domains are present
                if (uiState.domains.size > 1) {
                    ScrollableTabRow(
                        selectedTabIndex = uiState.domains.indexOfFirst { it.id == uiState.selectedDomain?.id }.coerceAtLeast(0),
                        edgePadding = 16.dp,
                        containerColor = MaterialTheme.colorScheme.surface,
                        contentColor = MaterialTheme.colorScheme.primary
                    ) {
                        uiState.domains.forEach { domain ->
                            Tab(
                                selected = uiState.selectedDomain?.id == domain.id,
                                onClick = { viewModel.selectDomain(domain.id) },
                                text = { 
                                    Text(
                                        text = domain.domainName, 
                                        fontWeight = FontWeight.Medium,
                                        style = MaterialTheme.typography.titleSmall
                                    ) 
                                }
                            )
                        }
                    }
                }

                // ─── State-based rendering ───
                when {
                    // 1. Loading state
                    uiState.isLoading -> {
                        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            LoadingIndicator(modifier = Modifier.fillMaxSize())
                        }
                    }
                    // 2. Error state
                    uiState.error != null -> {
                        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            com.aura.mas.ui.common.EmptyState(
                                icon = Icons.Filled.Folder,
                                title = "加载失败",
                                subtitle = uiState.error ?: "未知错误"
                            )
                        }
                    }
                    // 3. Empty state (no domains, or domains with no graph data)
                    uiState.domains.isEmpty() || uiState.graphJson.let { json ->
                        json.isBlank() || json == """{"nodes":[],"edges":[]}""" || !json.contains("\"nodes\"")
                    } -> {
                        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            com.aura.mas.ui.common.EmptyState(
                                icon = Icons.Filled.Hub,
                                title = "暂无知识图谱",
                                subtitle = "完成更多学习计划后将自动生成知识图谱"
                            )
                        }
                    }
                    // 4. Graph data ready - render ECharts WebView
                    else -> {
                        Box(modifier = Modifier.fillMaxSize()) {
                            KnowledgeGraphView(
                                jsonData = uiState.graphJson,
                                onNodeClick = { nodeId ->
                                    viewModel.selectNode(nodeId)
                                },
                                modifier = Modifier.fillMaxSize(),
                                isDarkTheme = isDark
                            )
                        }
                    }
                }
            }

            // Bottom detail overlay Card when a node is selected
            AnimatedVisibility(
                visible = uiState.selectedNode != null,
                enter = slideInVertically(initialOffsetY = { it }) + fadeIn(),
                exit = slideOutVertically(targetOffsetY = { it }) + fadeOut(),
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(16.dp)
            ) {
                uiState.selectedNode?.let { node ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .wrapContentHeight(),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surface
                        ),
                        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp)
                        ) {
                            // Header
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = node.name,
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onSurface,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                    modifier = Modifier.weight(1f)
                                )
                                IconButton(
                                    onClick = { viewModel.clearSelectedNode() },
                                    modifier = Modifier.size(24.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Close,
                                        contentDescription = "关闭",
                                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(12.dp))

                            // Dual statistics bars
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(16.dp)
                            ) {
                                // Mastery level
                                Column(modifier = Modifier.weight(1f)) {
                                    val masteryVal = node.masteryLevel ?: 0f
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Text("掌握度", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        Text("${(masteryVal * 100).toInt()}%", style = MaterialTheme.typography.labelSmall, color = Sage500, fontWeight = FontWeight.Bold)
                                    }
                                    Spacer(modifier = Modifier.height(4.dp))
                                    LinearProgressIndicator(
                                        progress = { masteryVal },
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .height(6.dp)
                                            .clip(RoundedCornerShape(3.dp)),
                                        color = Sage500,
                                        trackColor = MaterialTheme.colorScheme.primaryContainer
                                    )
                                }

                                // Importance level
                                Column(modifier = Modifier.weight(1f)) {
                                    val importanceVal = node.importance ?: 0.5f
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Text("重要度", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        Text("${(importanceVal * 100).toInt()}%", style = MaterialTheme.typography.labelSmall, color = Amber500, fontWeight = FontWeight.Bold)
                                    }
                                    Spacer(modifier = Modifier.height(4.dp))
                                    LinearProgressIndicator(
                                        progress = { importanceVal },
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .height(6.dp)
                                            .clip(RoundedCornerShape(3.dp)),
                                        color = Amber500,
                                        trackColor = MaterialTheme.colorScheme.secondaryContainer
                                    )
                                }
                            }

                            // Description block
                            if (!node.description.isNullOrBlank()) {
                                Spacer(modifier = Modifier.height(12.dp))
                                Text(
                                    text = "节点描述",
                                    style = MaterialTheme.typography.labelMedium,
                                    fontWeight = FontWeight.SemiBold,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .heightIn(max = 80.dp)
                                        .verticalScroll(rememberScrollState())
                                ) {
                                    Text(
                                        text = node.description,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        lineHeight = 16.sp
                                    )
                                }
                            }

                            // Associated learning resources links
                            if (!node.resourceIds.isNullOrEmpty()) {
                                Spacer(modifier = Modifier.height(12.dp))
                                Text(
                                    text = "关联学习资源",
                                    style = MaterialTheme.typography.labelMedium,
                                    fontWeight = FontWeight.SemiBold,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                                Spacer(modifier = Modifier.height(6.dp))
                                FlowRow(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    verticalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    node.resourceIds.forEach { resourceId ->
                                        SuggestionChip(
                                            onClick = {
                                                // Check context or default to opening as note
                                                onNavigateToNote(resourceId)
                                            },
                                            label = {
                                                Text(
                                                    "资源 #${resourceId}",
                                                    maxLines = 1,
                                                    overflow = TextOverflow.Ellipsis
                                                )
                                            },
                                            icon = {
                                                Icon(
                                                    imageVector = Icons.Default.MenuBook,
                                                    contentDescription = null,
                                                    modifier = Modifier.size(16.dp)
                                                )
                                            }
                                        )
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
