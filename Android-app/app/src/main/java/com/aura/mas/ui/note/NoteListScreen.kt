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
import androidx.compose.ui.text.font.FontWeight
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
    val notes: List<Note> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class NoteListViewModel @Inject constructor(
    private val noteRepo: NoteRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(NoteListUiState())
    val uiState: StateFlow<NoteListUiState> = _uiState.asStateFlow()

    init { loadNotes() }

    fun loadNotes() {
        viewModelScope.launch {
            _uiState.value = NoteListUiState(isLoading = true)
            try {
                noteRepo.getNotes().collect { result ->
                    if (result.code == 0) {
                        _uiState.value = NoteListUiState(isLoading = false, notes = result.data?.records ?: emptyList())
                    } else {
                        _uiState.value = NoteListUiState(isLoading = false, error = result.message.ifEmpty { "获取数据失败" })
                    }
                }
            } catch (e: Exception) {
                _uiState.value = NoteListUiState(isLoading = false, error = e.message)
            }
        }
    }

    fun createNote(title: String) {
        viewModelScope.launch {
            noteRepo.createNote(NoteCreateRequest(title))
            loadNotes()
        }
    }

    fun deleteNote(noteId: Long) {
        viewModelScope.launch {
            noteRepo.deleteNote(noteId)
            loadNotes()
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
    var showCreateDialog by remember { mutableStateOf(false) }
    var newNoteTitle by remember { mutableStateOf("") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("笔记", fontWeight = FontWeight.SemiBold) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = { showCreateDialog = true },
                icon = { Icon(Icons.Default.Add, null) },
                text = { Text("新建笔记") },
                shape = RoundedCornerShape(16.dp)
            )
        }
    ) { padding ->
        if (uiState.isLoading) {
            LoadingIndicator(Modifier.padding(padding))
            return@Scaffold
        }

        if (uiState.notes.isEmpty()) {
            EmptyState(Icons.Outlined.Description, "暂无笔记", "点击右下角按钮创建你的第一篇笔记", Modifier.padding(padding))
            return@Scaffold
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(uiState.notes, key = { it.id }) { note ->
                var showMenu by remember { mutableStateOf(false) }
                Card(
                    modifier = Modifier.fillMaxWidth().clickable { onNoteClick(note.id) },
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Description, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                            Spacer(Modifier.width(8.dp))
                            Text(note.noteName, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                            Box {
                                IconButton(onClick = { showMenu = true }, modifier = Modifier.size(24.dp)) {
                                    Icon(Icons.Default.MoreVert, null, modifier = Modifier.size(16.dp))
                                }
                                DropdownMenu(expanded = showMenu, onDismissRequest = { showMenu = false }) {
                                    DropdownMenuItem(text = { Text("删除") }, onClick = { showMenu = false; viewModel.deleteNote(note.id) })
                                }
                            }
                        }
                        if (note.content.isNotBlank()) {
                            Spacer(Modifier.height(4.dp))
                            Text(
                                note.content.take(100),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                        note.updatedAt?.let {
                            Spacer(Modifier.height(4.dp))
                            Text(it.take(16), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                        }
                    }
                }
            }
        }
    }

    if (showCreateDialog) {
        AlertDialog(
            onDismissRequest = { showCreateDialog = false },
            title = { Text("新建笔记") },
            text = {
                OutlinedTextField(
                    value = newNoteTitle, onValueChange = { newNoteTitle = it },
                    label = { Text("笔记标题") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp)
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    if (newNoteTitle.isNotBlank()) {
                        viewModel.createNote(newNoteTitle)
                        newNoteTitle = ""
                        showCreateDialog = false
                    }
                }) { Text("创建") }
            },
            dismissButton = { TextButton(onClick = { showCreateDialog = false }) { Text("取消") } }
        )
    }
}
