package com.aura.mas.ui.note

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.Note
import com.aura.mas.data.model.NoteCreateRequest
import com.aura.mas.data.repository.NoteRepository
import com.aura.mas.ui.common.LoadingIndicator
import com.aura.mas.ui.common.TopAppBar
import com.aura.mas.ui.components.resource.MarkdownRenderer
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class NoteDetailUiState(
    val isLoading: Boolean = true,
    val note: Note? = null,
    val isEditing: Boolean = false,
    val editTitle: String = "",
    val editContent: String = "",
    val isSaving: Boolean = false,
    val resources: List<com.aura.mas.data.model.NoteResourceRel> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class NoteDetailViewModel @Inject constructor(
    private val noteRepo: NoteRepository,
    private val api: com.aura.mas.data.api.ApiService,
    private val offlineCache: com.aura.mas.data.offline.OfflineCacheManager,
    private val networkUtil: com.aura.mas.util.NetworkUtil
) : ViewModel() {
    private val _uiState = MutableStateFlow(NoteDetailUiState())
    val uiState: StateFlow<NoteDetailUiState> = _uiState.asStateFlow()

    fun loadNote(noteId: Long) {
        if (noteId == -1L) {
            _uiState.value = NoteDetailUiState(
                isLoading = false,
                isEditing = true,
                editTitle = "",
                editContent = "",
                note = Note(id = -1L, noteName = "", content = "")
            )
            return
        }

        viewModelScope.launch {
            _uiState.value = NoteDetailUiState(isLoading = true)
            try {
                val result = noteRepo.getNote(noteId)
                val resourcesResult = try {
                    api.getNoteResources(noteId)
                } catch (_: Exception) {
                    com.aura.mas.data.model.ApiResponse(data = emptyList())
                }

                if (result.isSuccess && result.data != null) {
                    val note = result.data
                    _uiState.value = NoteDetailUiState(
                        isLoading = false,
                        note = note,
                        editTitle = note.noteName,
                        editContent = note.content,
                        resources = resourcesResult.data ?: emptyList()
                    )
                } else {
                    _uiState.value = NoteDetailUiState(isLoading = false, error = result.message)
                }
            } catch (e: Exception) {
                // Offline fallback
                val cached = offlineCache.getCachedNote(noteId)
                if (cached != null) {
                    _uiState.value = NoteDetailUiState(
                        isLoading = false,
                        note = cached,
                        editTitle = cached.noteName,
                        editContent = cached.content,
                        error = "离线模式"
                    )
                } else {
                    _uiState.value = NoteDetailUiState(isLoading = false, error = e.message)
                }
            }
        }
    }

    fun toggleEdit() {
        val current = _uiState.value
        _uiState.value = current.copy(
            isEditing = !current.isEditing,
            editTitle = current.note?.noteName ?: "",
            editContent = current.note?.content ?: ""
        )
    }

    fun updateTitle(title: String) {
        _uiState.value = _uiState.value.copy(editTitle = title)
    }

    fun updateContent(content: String) {
        _uiState.value = _uiState.value.copy(editContent = content)
    }

    fun save(noteId: Long) {
        val state = _uiState.value
        val note = state.note ?: return
        viewModelScope.launch {
            _uiState.value = state.copy(isSaving = true)
            try {
                val content = state.editContent.ifBlank { " " }
                val title = state.editTitle.ifBlank { "无标题笔记" }
                
                if (note.id == -1L) {
                    val result = noteRepo.createNote(NoteCreateRequest(noteName = title, content = content))
                    if (result.isSuccess && result.data != null) {
                        _uiState.value = state.copy(
                            note = result.data,
                            editContent = result.data.content,
                            editTitle = result.data.noteName,
                            isEditing = false,
                            isSaving = false
                        )
                    } else {
                        _uiState.value = state.copy(isSaving = false, error = result.message)
                    }
                } else {
                    noteRepo.updateNote(noteId, NoteCreateRequest(noteName = title, content = content))
                    _uiState.value = state.copy(
                        note = note.copy(noteName = title, content = content),
                        editContent = content,
                        isEditing = false,
                        isSaving = false
                    )
                }
            } catch (e: Exception) {
                _uiState.value = state.copy(isSaving = false, error = e.message)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NoteDetailScreen(
    noteId: Long,
    onBack: () -> Unit,
    onNavigateToPlan: (Long) -> Unit = {},
    onNavigateToFlashcards: (Long) -> Unit = {},
    viewModel: NoteDetailViewModel = hiltViewModel()
) {
    LaunchedEffect(noteId) { viewModel.loadNote(noteId) }
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = uiState.note?.noteName ?: "笔记详情",
                onBack = onBack,
                actions = {
                    if (uiState.isEditing) {
                        TextButton(
                            onClick = { viewModel.save(noteId) },
                            enabled = !uiState.isSaving
                        ) {
                            if (uiState.isSaving) {
                                CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                            } else {
                                Text("保存")
                            }
                        }
                    } else {
                        IconButton(onClick = { viewModel.toggleEdit() }) {
                            Icon(Icons.Default.Edit, "编辑")
                        }
                    }
                }
            )
        }
    ) { padding ->
        if (uiState.isLoading) {
            LoadingIndicator(Modifier.padding(padding))
            return@Scaffold
        }

        val note = uiState.note
        if (note == null) {
            Box(Modifier.fillMaxSize().padding(padding)) {
                com.aura.mas.ui.common.EmptyState(Icons.Default.Error, "笔记不存在", uiState.error ?: "")
            }
            return@Scaffold
        }

        Column(modifier = Modifier.padding(padding).fillMaxSize()) {
            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                if (uiState.isEditing) {
                    EditMode(
                        title = uiState.editTitle,
                        content = uiState.editContent,
                        onTitleChange = { viewModel.updateTitle(it) },
                        onContentChange = { viewModel.updateContent(it) },
                        modifier = Modifier.fillMaxSize()
                    )
                } else {
                    ViewMode(
                        note = note,
                        resources = uiState.resources,
                        onNavigateToPlan = onNavigateToPlan,
                        onNavigateToFlashcards = { onNavigateToFlashcards(noteId) },
                        modifier = Modifier.fillMaxSize()
                    )
                }
            }
        }
    }
}

@Composable
private fun ViewMode(
    note: Note,
    resources: List<com.aura.mas.data.model.NoteResourceRel>,
    onNavigateToPlan: (Long) -> Unit,
    onNavigateToFlashcards: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp)
    ) {
        // Title
        Text(
            note.noteName.ifBlank { "无标题笔记" },
            style = MaterialTheme.typography.headlineLarge,
            fontWeight = FontWeight.ExtraBold,
            color = MaterialTheme.colorScheme.onSurface
        )

        // Timestamp
        note.updatedAt?.let {
            Spacer(Modifier.height(8.dp))
            Text(
                "最后编辑于 ${it.take(16).replace("T", " ")}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        // Associated Resources
        if (resources.isNotEmpty()) {
            Spacer(Modifier.height(16.dp))
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                items(resources) { rel ->
                    AssistChip(
                        onClick = { rel.planId?.let { onNavigateToPlan(it) } },
                        label = {
                            val title = rel.resourceTitle.ifBlank { "资源 #${rel.resourceId}" }
                            Text(
                                if (rel.moduleName.isNotBlank()) "${rel.moduleName} · $title" else title,
                                maxLines = 1,
                                style = MaterialTheme.typography.labelMedium
                            )
                        },
                        leadingIcon = {
                            Icon(
                                Icons.Default.Link,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp)
                            )
                        },
                        shape = RoundedCornerShape(12.dp),
                        colors = AssistChipDefaults.assistChipColors(
                            containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f),
                            labelColor = MaterialTheme.colorScheme.onPrimaryContainer,
                            leadingIconContentColor = MaterialTheme.colorScheme.onPrimaryContainer
                        ),
                        border = null
                    )
                }
            }
        }

        Spacer(Modifier.height(24.dp))
        Button(
            onClick = onNavigateToFlashcards,
            modifier = Modifier.fillMaxWidth().height(56.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.secondaryContainer,
                contentColor = MaterialTheme.colorScheme.onSecondaryContainer
            ),
            shape = RoundedCornerShape(16.dp)
        ) {
            Icon(Icons.Default.School, contentDescription = null)
            Spacer(Modifier.width(12.dp))
            Text("复习这篇笔记的闪卡", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        }

        Spacer(Modifier.height(24.dp))
        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
        Spacer(Modifier.height(24.dp))

        // Rendered markdown content
        if (note.content.isBlank()) {
            Box(Modifier.fillMaxWidth().padding(vertical = 40.dp), contentAlignment = Alignment.Center) {
                Text("暂无内容", style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        } else {
            MarkdownRenderer(content = note.content, modifier = Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun EditMode(
    title: String,
    content: String,
    onTitleChange: (String) -> Unit,
    onContentChange: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.fillMaxSize()) {
        // Title Input
        TextField(
            value = title,
            onValueChange = onTitleChange,
            placeholder = { Text("笔记标题...", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)) },
            modifier = Modifier.fillMaxWidth(),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = androidx.compose.ui.graphics.Color.Transparent,
                unfocusedContainerColor = androidx.compose.ui.graphics.Color.Transparent,
                focusedIndicatorColor = androidx.compose.ui.graphics.Color.Transparent,
                unfocusedIndicatorColor = androidx.compose.ui.graphics.Color.Transparent
            ),
            textStyle = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
            singleLine = true
        )
        
        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))

        // Content Input
        TextField(
            value = content,
            onValueChange = onContentChange,
            placeholder = { Text("开始书写你的笔记...\n\n支持 Markdown 语法\n# 标题\n**粗体** *斜体*\n- 列表\n> 引用\n```代码```", color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)) },
            modifier = Modifier.fillMaxWidth().weight(1f),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = androidx.compose.ui.graphics.Color.Transparent,
                unfocusedContainerColor = androidx.compose.ui.graphics.Color.Transparent,
                focusedIndicatorColor = androidx.compose.ui.graphics.Color.Transparent,
                unfocusedIndicatorColor = androidx.compose.ui.graphics.Color.Transparent
            ),
            textStyle = MaterialTheme.typography.bodyLarge.copy(fontFamily = FontFamily.Monospace)
        )
        
        Surface(
            color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(
                "Markdown: **加粗** *斜体* # 标题 - 列表 > 引用 ```代码```",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)
            )
        }
    }
}
