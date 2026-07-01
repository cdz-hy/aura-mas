package com.aura.mas.ui.admin

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.AdminStats
import com.aura.mas.data.repository.AdminRepository
import com.aura.mas.ui.common.*
import com.aura.mas.ui.theme.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AdminUiState(
    val isLoading: Boolean = true,
    val stats: AdminStats? = null,
    val error: String? = null
)

@HiltViewModel
class AdminViewModel @Inject constructor(
    private val adminRepo: AdminRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(AdminUiState())
    val uiState: StateFlow<AdminUiState> = _uiState.asStateFlow()

    init { loadStats() }

    fun loadStats() {
        viewModelScope.launch {
            _uiState.value = AdminUiState(isLoading = true)
            try {
                val result = adminRepo.getStats()
                _uiState.value = AdminUiState(stats = result.data)
            } catch (e: Exception) {
                _uiState.value = AdminUiState(error = e.message)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminDashboardScreen(
    onUsersClick: () -> Unit = {},
    onLogsClick: () -> Unit = {},
    onBack: () -> Unit = {},
    viewModel: AdminViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = { TopAppBar("管理后台", onBack = onBack) }
    ) { padding ->
        if (uiState.isLoading) {
            LoadingIndicator(Modifier.padding(padding))
            return@Scaffold
        }

        val stats = uiState.stats
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Text("管理概览", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(8.dp))
            }

            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    StatCard(Icons.Default.People, "用户数", "${stats?.userCount ?: 0}", Blue50, Blue500, Modifier.weight(1f))
                    StatCard(Icons.Default.MenuBook, "计划数", "${stats?.planCount ?: 0}", Emerald50, Emerald500, Modifier.weight(1f))
                }
            }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    StatCard(Icons.Default.LibraryBooks, "知识库文档", "${stats?.kbDocCount ?: 0}", Sage100, Sage500, Modifier.weight(1f))
                    StatCard(Icons.Default.SmartToy, "今日AI调用", "${stats?.todayAiCalls ?: 0}",
                        MaterialTheme.colorScheme.tertiaryContainer, MaterialTheme.colorScheme.tertiary, Modifier.weight(1f))
                }
            }

            item {
                Spacer(Modifier.height(8.dp))
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column {
                        TextButton(onClick = onUsersClick, modifier = Modifier.fillMaxWidth()) {
                            Icon(Icons.Default.People, null); Spacer(Modifier.width(12.dp))
                            Text("用户管理", modifier = Modifier.weight(1f))
                            Icon(Icons.Default.ChevronRight, null)
                        }
                        Divider(Modifier.padding(horizontal = 16.dp))
                        TextButton(onClick = onLogsClick, modifier = Modifier.fillMaxWidth()) {
                            Icon(Icons.Default.List, null); Spacer(Modifier.width(12.dp))
                            Text("系统日志", modifier = Modifier.weight(1f))
                            Icon(Icons.Default.ChevronRight, null)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AdminUsersScreen(onBack: () -> Unit, viewModel: AdminViewModel = hiltViewModel()) {
    Scaffold(topBar = { TopAppBar("用户管理", onBack = onBack) }) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            EmptyState(Icons.Default.People, "用户管理", "功能开发中")
        }
    }
}

@Composable
fun AdminLogsScreen(onBack: () -> Unit, viewModel: AdminViewModel = hiltViewModel()) {
    Scaffold(topBar = { TopAppBar("系统日志", onBack = onBack) }) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            EmptyState(Icons.Default.List, "系统日志", "功能开发中")
        }
    }
}
