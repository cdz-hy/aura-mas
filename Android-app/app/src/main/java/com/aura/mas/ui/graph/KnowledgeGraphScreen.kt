package com.aura.mas.ui.graph

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.api.ApiService
import com.aura.mas.ui.common.LoadingIndicator
import com.aura.mas.ui.common.TopAppBar
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Folder
import com.aura.mas.ui.components.graph.GraphEdge
import com.aura.mas.ui.components.graph.GraphNode
import com.aura.mas.ui.components.graph.KnowledgeGraphView
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class GraphUiState(
    val isLoading: Boolean = true,
    val nodes: List<GraphNode> = emptyList(),
    val edges: List<GraphEdge> = emptyList(),
    val domainName: String = "",
    val error: String? = null
)

@HiltViewModel
class KnowledgeGraphViewModel @Inject constructor(
    private val api: ApiService
) : ViewModel() {
    private val _uiState = MutableStateFlow(GraphUiState())
    val uiState: StateFlow<GraphUiState> = _uiState.asStateFlow()

    fun loadGraph(userId: Long) {
        viewModelScope.launch {
            _uiState.value = GraphUiState(isLoading = true)
            try {
                val domains = api.getKnowledgeDomains(userId)
                // Parse graph data from domains
                _uiState.value = GraphUiState(isLoading = false)
            } catch (e: Exception) {
                _uiState.value = GraphUiState(error = e.message, isLoading = false)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun KnowledgeGraphScreen(
    userId: Long,
    onBack: () -> Unit,
    viewModel: KnowledgeGraphViewModel = hiltViewModel()
) {
    LaunchedEffect(userId) { viewModel.loadGraph(userId) }
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = { TopAppBar("知识图谱", onBack = onBack) }
    ) { padding ->
        if (uiState.isLoading) {
            LoadingIndicator(Modifier.padding(padding))
            return@Scaffold
        }

        if (uiState.nodes.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding)) {
                com.aura.mas.ui.common.EmptyState(
                    Icons.Filled.Folder,
                    "暂无知识图谱",
                    "完成更多学习计划后将自动生成知识图谱"
                )
            }
            return@Scaffold
        }

        KnowledgeGraphView(
            nodes = uiState.nodes,
            edges = uiState.edges,
            modifier = Modifier.fillMaxSize().padding(padding)
        )
    }
}
