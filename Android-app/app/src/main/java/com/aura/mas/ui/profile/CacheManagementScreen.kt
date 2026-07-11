package com.aura.mas.ui.profile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.local.dao.*
import com.aura.mas.ui.common.TopAppBar
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CacheInfo(
    val label: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
    val count: Int = 0,
    val sizeEstimate: String = ""
)

data class CacheUiState(
    val isLoading: Boolean = true,
    val plans: CacheInfo = CacheInfo("学习计划", Icons.Default.MenuBook),
    val resources: CacheInfo = CacheInfo("学习资源", Icons.Default.Description),
    val notes: CacheInfo = CacheInfo("笔记", Icons.Default.StickyNote2),
    val flashcards: CacheInfo = CacheInfo("闪卡", Icons.Default.Style),
    val totalSize: String = ""
)

@HiltViewModel
class CacheViewModel @Inject constructor(
    private val planDao: PlanDao,
    private val resourceDao: ResourceDao,
    private val noteDao: NoteDao,
    private val flashcardDao: FlashcardDao,
    @ApplicationContext private val context: android.content.Context
) : ViewModel() {
    private val _uiState = MutableStateFlow(CacheUiState())
    val uiState: StateFlow<CacheUiState> = _uiState.asStateFlow()

    init { loadCacheInfo() }

    fun loadCacheInfo() {
        viewModelScope.launch {
            _uiState.value = CacheUiState(isLoading = true)
            try {
                val plans = planDao.getAllPlansSync()
                val notes = noteDao.getAllNotesSync()
                val resources = resourceDao.getAllResourcesSync()
                val flashcards = flashcardDao.getAllFlashcardsSync()
                val dbSize = context.getDatabasePath("aura_database").length()

                _uiState.value = CacheUiState(
                    isLoading = false,
                    plans = CacheInfo("学习计划", Icons.Default.MenuBook, plans.size),
                    resources = CacheInfo("学习资源", Icons.Default.Description, resources.size),
                    notes = CacheInfo("笔记", Icons.Default.StickyNote2, notes.size),
                    flashcards = CacheInfo("闪卡", Icons.Default.Style, flashcards.size),
                    totalSize = formatSize(dbSize)
                )
            } catch (e: Exception) {
                _uiState.value = CacheUiState(isLoading = false)
            }
        }
    }

    fun clearPlans() {
        viewModelScope.launch {
            planDao.deleteAll()
            loadCacheInfo()
        }
    }

    fun clearResources() {
        viewModelScope.launch {
            resourceDao.deleteAll()
            loadCacheInfo()
        }
    }

    fun clearNotes() {
        viewModelScope.launch {
            noteDao.deleteAll()
            loadCacheInfo()
        }
    }

    fun clearFlashcards() {
        viewModelScope.launch {
            flashcardDao.deleteAll()
            loadCacheInfo()
        }
    }

    fun clearAll() {
        viewModelScope.launch {
            planDao.deleteAll()
            resourceDao.deleteAll()
            noteDao.deleteAll()
            flashcardDao.deleteAll()
            loadCacheInfo()
        }
    }

    private fun formatSize(bytes: Long): String {
        return when {
            bytes < 1024 -> "$bytes B"
            bytes < 1024 * 1024 -> "${bytes / 1024} KB"
            else -> "${"%.1f".format(bytes / (1024.0 * 1024.0))} MB"
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CacheManagementScreen(
    onBack: () -> Unit,
    viewModel: CacheViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    var showClearAllDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = { TopAppBar("缓存管理", onBack = onBack) }
    ) { padding ->
        if (uiState.isLoading) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            return@Scaffold
        }

        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Total size card
            Card(
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
            ) {
                Row(
                    Modifier.fillMaxWidth().padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.Storage, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(32.dp))
                    Spacer(Modifier.width(12.dp))
                    Column {
                        Text("缓存大小", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f))
                        Text(uiState.totalSize, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    }
                }
            }

            // Cache items
            Text("分类缓存", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)

            CacheItemCard(uiState.plans, "清除", viewModel::clearPlans)
            CacheItemCard(uiState.resources, "清除", viewModel::clearResources)
            CacheItemCard(uiState.notes, "清除", viewModel::clearNotes)
            CacheItemCard(uiState.flashcards, "清除", viewModel::clearFlashcards)

            Spacer(Modifier.weight(1f))

            // Clear all button
            OutlinedButton(
                onClick = { showClearAllDialog = true },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
            ) {
                Icon(Icons.Default.DeleteSweep, null)
                Spacer(Modifier.width(8.dp))
                Text("清除所有缓存")
            }
        }
    }

    if (showClearAllDialog) {
        AlertDialog(
            onDismissRequest = { showClearAllDialog = false },
            title = { Text("清除所有缓存") },
            text = { Text("确定要清除所有缓存数据吗？清除后需要联网重新加载。") },
            confirmButton = {
                TextButton(onClick = {
                    showClearAllDialog = false
                    viewModel.clearAll()
                }) { Text("确定", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = { TextButton(onClick = { showClearAllDialog = false }) { Text("取消") } }
        )
    }
}

@Composable
private fun CacheItemCard(info: CacheInfo, actionText: String, onAction: () -> Unit) {
    Card(
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Row(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(info.icon, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(24.dp))
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(info.label, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                Text("${info.count} 条记录", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            TextButton(onClick = onAction) { Text(actionText) }
        }
    }
}
