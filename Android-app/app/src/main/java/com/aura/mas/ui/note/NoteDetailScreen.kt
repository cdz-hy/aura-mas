package com.aura.mas.ui.note

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
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
import com.aura.mas.data.model.Note
import com.aura.mas.data.repository.NoteRepository
import com.aura.mas.ui.common.LoadingIndicator
import com.aura.mas.ui.common.TopAppBar
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
    val editContent: String = "",
    val isSaving: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class NoteDetailViewModel @Inject constructor(
    private val noteRepo: NoteRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(NoteDetailUiState())
    val uiState: StateFlow<NoteDetailUiState> = _uiState.asStateFlow()

    fun loadNote(noteId: Long) {
        viewModelScope.launch {
            _uiState.value = NoteDetailUiState(isLoading = true)
            try {
                val result = noteRepo.getNote(noteId)
                if (result.code == 0 && result.data != null) {
                    _uiState.value = NoteDetailUiState(
                        note = result.data,
                        editContent = result.data.content,
                        isLoading = false
                    )
                } else {
                    _uiState.value = NoteDetailUiState(isLoading = false, error = result.message)
                }
            } catch (e: Exception) {
                _uiState.value = NoteDetailUiState(isLoading = false, error = e.message)
            }
        }
    }

    fun toggleEdit() {
        _uiState.value = _uiState.value.copy(isEditing = !_uiState.value.isEditing)
    }

    fun updateContent(content: String) {
        _uiState.value = _uiState.value.copy(editContent = content)
    }

    fun save(noteId: Long) {
        viewModelScope.launch {
            val note = _uiState.value.note ?: return@launch
            _uiState.value = _uiState.value.copy(isSaving = true)
            try {
                noteRepo.updateNote(noteId, note.copy(content = _uiState.value.editContent))
                _uiState.value = _uiState.value.copy(
                    note = note.copy(content = _uiState.value.editContent),
                    isEditing = false,
                    isSaving = false
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isSaving = false, error = e.message)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NoteDetailScreen(
    noteId: Long,
    onBack: () -> Unit,
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
                        TextButton(onClick = { viewModel.save(noteId) }, enabled = !uiState.isSaving) {
                            Text("保存")
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
            Text("笔记不存在", modifier = Modifier.padding(padding).padding(16.dp))
            return@Scaffold
        }

        if (uiState.isEditing) {
            OutlinedTextField(
                value = uiState.editContent,
                onValueChange = { viewModel.updateContent(it) },
                modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
                shape = RoundedCornerShape(12.dp)
            )
        } else {
            Column(
                modifier = Modifier.fillMaxSize().padding(padding)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp)
            ) {
                Text(note.noteName, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(8.dp))
                note.updatedAt?.let {
                    Text(it.take(16), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                    Spacer(Modifier.height(16.dp))
                }
                Text(note.content, style = MaterialTheme.typography.bodyLarge)
            }
        }
    }
}
