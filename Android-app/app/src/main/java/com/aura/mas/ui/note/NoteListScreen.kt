package com.aura.mas.ui.note

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.Note
import com.aura.mas.data.model.NoteCreateRequest
import com.aura.mas.data.repository.NoteRepository
import com.aura.mas.ui.common.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class NoteListUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val notes: List<Note> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class NoteListViewModel @Inject constructor(
    private val noteRepo: NoteRepository,
    private val api: com.aura.mas.data.api.ApiService,
    private val offlineCache: com.aura.mas.data.offline.OfflineCacheManager,
    private val networkUtil: com.aura.mas.util.NetworkUtil
) : ViewModel() {
    private val _uiState = MutableStateFlow(NoteListUiState())
    val uiState: StateFlow<NoteListUiState> = _uiState.asStateFlow()

    init { loadNotes() }

    fun loadNotes() {
        viewModelScope.launch {
            // Step 1: Show cached data immediately (sorted by id desc = newest first)
            val cached = offlineCache.getCachedNotes().sortedByDescending { it.id }
            if (cached.isNotEmpty()) {
                _uiState.value = NoteListUiState(notes = cached, isLoading = false, isRefreshing = true)
            } else {
                _uiState.value = NoteListUiState(isLoading = true)
            }

            // Step 2: Fetch fresh data in background
            try {
                val result = kotlinx.coroutines.withTimeout(15_000L) { api.getNotes(size = 50) }
                if (result.isSuccess && result.data != null) {
                    val notes = result.data.records.sortedByDescending { it.id }
                    offlineCache.cacheNotes(notes)
                    // Only update if data changed
                    val currentIds = _uiState.value.notes.map { it.id }.toSet()
                    val newIds = notes.map { it.id }.toSet()
                    if (currentIds != newIds || _uiState.value.notes.size != notes.size) {
                        _uiState.value = _uiState.value.copy(notes = notes, isRefreshing = false, isLoading = false)
                    } else {
                        _uiState.value = _uiState.value.copy(isRefreshing = false, isLoading = false)
                    }
                } else {
                    _uiState.value = _uiState.value.copy(isRefreshing = false)
                }
            } catch (e: Exception) {
                // Silent fail - cached data is already shown
                _uiState.value = _uiState.value.copy(isRefreshing = false, isLoading = false)
            }
        }
    }

    fun createNote(title: String) {
        if (!networkUtil.isOnline()) {
            _uiState.value = _uiState.value.copy(error = "离线状态，无法创建")
            return
        }
        viewModelScope.launch {
            try {
                val result = noteRepo.createNote(NoteCreateRequest(title))
                if (result.isSuccess) {
                    loadNotes()
                } else {
                    _uiState.value = _uiState.value.copy(error = result.message.ifEmpty { "创建失败" })
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message ?: "创建失败")
            }
        }
    }

    fun deleteNote(noteId: Long) {
        if (!networkUtil.isOnline()) {
            _uiState.value = _uiState.value.copy(error = "离线状态，无法删除")
            return
        }
        viewModelScope.launch {
            val result = noteRepo.deleteNote(noteId)
            if (result.isSuccess) {
                _uiState.value = _uiState.value.copy(
                    notes = _uiState.value.notes.filterNot { it.id == noteId }
                )
            } else {
                _uiState.value = _uiState.value.copy(error = result.message.ifEmpty { "删除失败" })
            }
        }
    }

    fun updateNoteTitle(note: Note, title: String) {
        val newTitle = title.trim().ifBlank { "无标题笔记" }
        viewModelScope.launch {
            try {
                val result = noteRepo.updateNote(
                    note.id,
                    NoteCreateRequest(noteName = newTitle, content = note.content.ifBlank { " " })
                )
                if (result.isSuccess) {
                    _uiState.value = _uiState.value.copy(
                        notes = _uiState.value.notes.map { if (it.id == note.id) it.copy(noteName = newTitle) else it }
                    )
                } else {
                    _uiState.value = _uiState.value.copy(error = result.message.ifEmpty { "更新失败" })
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message ?: "更新失败")
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NoteListScreen(
    onNoteClick: (Long) -> Unit,
    viewModel: NoteListViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.loadNotes()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("笔记", fontWeight = FontWeight.SemiBold) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface),
                windowInsets = WindowInsets(0.dp)
            )
        },
        contentWindowInsets = WindowInsets(0.dp),
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = { onNoteClick(-1L) },
                icon = { Icon(Icons.Default.Add, null) },
                text = { Text("新建笔记") },
                shape = RoundedCornerShape(16.dp)
            )
        }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            if (uiState.isRefreshing) {
                LinearProgressIndicator(
                    modifier = Modifier.fillMaxWidth().height(2.dp),
                    trackColor = Color.Transparent
                )
            }
            Box(Modifier.fillMaxSize()) {
                when {
            uiState.isLoading -> {
                LoadingIndicator()
            }
            uiState.error != null -> {
                ErrorState(
                    message = uiState.error ?: "加载失败",
                    onRetry = { viewModel.loadNotes() }
                )
            }
            uiState.notes.isEmpty() -> {
                EmptyState(
                    Icons.Outlined.Description,
                    "暂无笔记",
                    "点击右下角按钮创建你的第一篇笔记"
                )
            }
            else -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(uiState.notes, key = { it.id }) { note ->
                        NoteCard(
                            note = note,
                            onClick = { onNoteClick(note.id) },
                            onDelete = { viewModel.deleteNote(note.id) },
                            onRename = { title -> viewModel.updateNoteTitle(note, title) }
                        )
                    }
                }
            }
        }
    }
}
}
}

@Composable
private fun NoteCard(note: Note, onClick: () -> Unit, onDelete: () -> Unit, onRename: (String) -> Unit) {
    var showMenu by remember { mutableStateOf(false) }
    var showDeleteConfirm by remember { mutableStateOf(false) }
    var isEditingTitle by remember { mutableStateOf(false) }
    var editingTitle by remember(note.id, note.noteName) { mutableStateOf(note.noteName) }
    val focusRequester = remember { FocusRequester() }
    val focusManager = LocalFocusManager.current

    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            title = { Text("删除笔记") },
            text = { Text("确定要删除笔记「${note.noteName.ifBlank { "无标题笔记" }}」吗？此操作不可恢复。") },
            confirmButton = {
                TextButton(
                    onClick = {
                        showDeleteConfirm = false
                        onDelete()
                    }
                ) { Text("确认删除", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteConfirm = false }) { Text("取消") }
            }
        )
    }

    LaunchedEffect(isEditingTitle) {
        if (isEditingTitle) focusRequester.requestFocus()
    }

    Card(
        modifier = Modifier.fillMaxWidth().clickable(enabled = !isEditingTitle, onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
    ) {
        Column(Modifier.padding(16.dp)) {
            // Header row
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Default.Description,
                    null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(Modifier.width(10.dp))
                if (isEditingTitle) {
                    OutlinedTextField(
                        value = editingTitle,
                        onValueChange = { editingTitle = it },
                        singleLine = true,
                        textStyle = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
                        modifier = Modifier.weight(1f).focusRequester(focusRequester),
                        keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(imeAction = ImeAction.Done),
                        keyboardActions = androidx.compose.foundation.text.KeyboardActions(
                            onDone = {
                                focusManager.clearFocus()
                                isEditingTitle = false
                                onRename(editingTitle)
                            }
                        ),
                        trailingIcon = {
                            Row {
                                IconButton(
                                    onClick = {
                                        focusManager.clearFocus()
                                        isEditingTitle = false
                                        onRename(editingTitle)
                                    },
                                    modifier = Modifier.size(32.dp)
                                ) { Icon(Icons.Default.Check, null, modifier = Modifier.size(18.dp)) }
                                IconButton(
                                    onClick = {
                                        focusManager.clearFocus()
                                        editingTitle = note.noteName
                                        isEditingTitle = false
                                    },
                                    modifier = Modifier.size(32.dp)
                                ) { Icon(Icons.Default.Close, null, modifier = Modifier.size(18.dp)) }
                            }
                        }
                    )
                } else {
                    Text(
                        note.noteName.ifBlank { "无标题笔记" },
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f)
                    )
                }
                Box {
                    IconButton(onClick = { showMenu = true }, modifier = Modifier.size(24.dp)) {
                        Icon(Icons.Default.MoreVert, null, modifier = Modifier.size(16.dp))
                    }
                    DropdownMenu(expanded = showMenu, onDismissRequest = { showMenu = false }) {
                        DropdownMenuItem(
                            text = { Text("编辑") },
                            onClick = {
                                showMenu = false
                                editingTitle = note.noteName
                                isEditingTitle = true
                            },
                            leadingIcon = { Icon(Icons.Default.Edit, null) }
                        )
                        DropdownMenuItem(
                            text = { Text("删除") },
                            onClick = {
                                showMenu = false
                                showDeleteConfirm = true
                            },
                            leadingIcon = { Icon(Icons.Default.Delete, null) }
                        )
                    }
                }
            }

            // Content preview
            if (note.content.isNotBlank()) {
                Spacer(Modifier.height(8.dp))
                Text(
                    note.content.take(150).replace(Regex("[#*`>\\[\\]()!]"), ""),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis
                )
            }

            // Timestamp
            note.updatedAt?.let {
                Spacer(Modifier.height(8.dp))
                Text(
                    it.take(16).replace("T", " "),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.outline
                )
            }
        }
    }
}
