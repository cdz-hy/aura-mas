package com.aura.mas.data.repository

import com.aura.mas.data.api.ApiService
import com.aura.mas.data.local.dao.NoteDao
import com.aura.mas.data.local.entity.CachedNote
import com.aura.mas.data.model.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.CancellationException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NoteRepository @Inject constructor(
    private val api: ApiService,
    private val noteDao: NoteDao
) {
    fun getNotes(page: Int = 1, size: Int = 20, keyword: String? = null): Flow<ApiResponse<PaginatedResponse<Note>>> = flow {
        try {
            val response = api.getNotes(page, size, keyword = keyword)
            if (response.isSuccess && response.data != null) {
                val cached = response.data.records.map { it.toCached() }
                if (page == 1) noteDao.deleteAll()
                noteDao.insertAll(cached)
            }
            emit(response)
        } catch (e: Exception) {
            if (e is CancellationException) throw e
            // Try offline cache
            try {
                val cachedNotes = noteDao.getAllNotesSync()
                if (cachedNotes.isNotEmpty()) {
                    val paginated = PaginatedResponse(
                        records = cachedNotes.map { it.toDomain() },
                        total = cachedNotes.size.toLong(),
                        page = 1,
                        size = cachedNotes.size,
                        pages = 1
                    )
                    emit(ApiResponse(data = paginated, message = "离线模式"))
                } else {
                    emit(ApiResponse(code = -1, message = e.message ?: "网络错误"))
                }
            } catch (_: Exception) {
                emit(ApiResponse(code = -1, message = e.message ?: "网络错误"))
            }
        }
    }

    suspend fun getNote(noteId: Long): ApiResponse<Note> {
        return try {
            val response = api.getNote(noteId)
            if (response.isSuccess && response.data != null) {
                noteDao.insert(response.data.toCached())
            }
            response
        } catch (e: Exception) {
            val cached = noteDao.getNoteById(noteId)
            if (cached != null) {
                ApiResponse(data = cached.toDomain())
            } else {
                ApiResponse(message = e.message ?: "Unknown error")
            }
        }
    }

    suspend fun createNote(request: NoteCreateRequest): ApiResponse<Note> {
        return api.createNote(request)
    }

    suspend fun updateNote(noteId: Long, request: NoteCreateRequest): ApiResponse<Unit> {
        val result = api.updateNote(noteId, request)
        if (result.isSuccess) {
            val existing = noteDao.getNoteById(noteId)
            if (existing != null) {
                noteDao.insert(existing.copy(
                    noteName = request.noteName,
                    content = request.content
                ))
            }
        }
        return result
    }

    suspend fun deleteNote(noteId: Long): ApiResponse<Unit> {
        val result = api.deleteNote(noteId)
        if (result.isSuccess) {
            noteDao.getNoteById(noteId)?.let { noteDao.delete(it) }
        }
        return result
    }

    fun getCachedNotes(): Flow<List<CachedNote>> = noteDao.getAllNotes()

    private fun Note.toCached() = CachedNote(
        id = id, userId = userId, noteName = noteName,
        content = content, tags = tags, isPinned = isPinned,
        createdAt = createdAt, updatedAt = updatedAt
    )

    private fun CachedNote.toDomain() = Note(
        id = id, userId = userId, noteName = noteName,
        content = content, tags = tags, isPinned = isPinned,
        createdAt = createdAt, updatedAt = updatedAt
    )
}
