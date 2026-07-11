package com.aura.mas.data.offline
 
import com.aura.mas.data.local.dao.*
import com.aura.mas.data.local.entity.*
import com.aura.mas.data.model.*
import kotlinx.coroutines.flow.first
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Centralized offline cache manager.
 * Provides cached data conversion for all entity types.
 * Used by ViewModels as fallback when API calls fail.
 */
@Singleton
class OfflineCacheManager @Inject constructor(
    private val planDao: PlanDao,
    private val resourceDao: ResourceDao,
    private val noteDao: NoteDao,
    private val flashcardDao: FlashcardDao,
    private val userDao: UserDao
) {
    // ── Plans ─────────────────────────────────────────────────

    suspend fun getCachedPlans(): List<LearningPlan> {
        return planDao.getAllPlansSync().map { it.toDomain() }
    }

    suspend fun getCachedPlan(planId: Long): LearningPlan? {
        return planDao.getPlanById(planId)?.toDomain()
    }

    suspend fun cachePlans(plans: List<LearningPlan>) {
        planDao.insertAll(plans.map { it.toCached() })
    }

    suspend fun cachePlan(plan: LearningPlan) {
        planDao.insert(plan.toCached())
    }

    // ── Resources ─────────────────────────────────────────────

    suspend fun getCachedResources(planId: Long): List<LearningResource> {
        return resourceDao.getResourcesByPlanSync(planId).map { it.toDomain() }
    }

    suspend fun cacheResources(resources: List<LearningResource>) {
        resourceDao.insertAll(resources.map { it.toCached() })
    }

    // ── Notes ─────────────────────────────────────────────────

    suspend fun getCachedNotes(): List<Note> {
        return noteDao.getAllNotesSync().map { it.toDomain() }
    }

    suspend fun getCachedNote(noteId: Long): Note? {
        return noteDao.getNoteById(noteId)?.toDomain()
    }

    suspend fun cacheNotes(notes: List<Note>) {
        noteDao.insertAll(notes.map { it.toCached() })
    }

    suspend fun cacheNote(note: Note) {
        noteDao.insert(note.toCached())
    }

    // ── Flashcards ────────────────────────────────────────────

    suspend fun getCachedFlashcards(noteId: Long): List<Flashcard> {
        return flashcardDao.getFlashcardsByNote(noteId).first().map { it.toDomain() }
    }

    suspend fun cacheFlashcards(cards: List<Flashcard>) {
        flashcardDao.insertAll(cards.map { it.toCached() })
    }

    // ── User ──────────────────────────────────────────────────

    suspend fun getCachedUser(): User? {
        return userDao.getCachedUser()?.toDomain()
    }

    suspend fun cacheUser(user: User) {
        userDao.insert(user.toCached())
    }

    // ── Mappers ───────────────────────────────────────────────

    private fun CachedPlan.toDomain() = LearningPlan(
        id = id, userId = userId, title = title,
        learningGoal = learningGoal, planConfig = planConfig,
        status = status, createdAt = createdAt, updatedAt = updatedAt
    )

    private fun LearningPlan.toCached() = CachedPlan(
        id = id, userId = userId, title = title,
        learningGoal = learningGoal, planConfig = planConfig,
        status = status, createdAt = createdAt, updatedAt = updatedAt
    )

    private fun CachedResource.toDomain() = LearningResource(
        id = id, planId = planId, moduleType = moduleType,
        moduleOrder = moduleOrder, status = status,
        storagePath = storagePath, version = version,
        moduleData = moduleDataJson ?: ""
    )

    private fun LearningResource.toCached() = CachedResource(
        id = id, planId = planId, moduleType = moduleType,
        moduleOrder = moduleOrder, moduleName = getModuleName(),
        resourceTitle = getResourceTitle(), resourceType = getResourceType(),
        moduleDataJson = try { com.google.gson.Gson().toJson(moduleData) } catch (_: Exception) { null },
        status = status, storagePath = storagePath, version = version
    )

    private fun CachedNote.toDomain() = Note(
        id = id, userId = userId, noteName = noteName,
        content = content, tags = tags, isPinned = isPinned,
        createdAt = createdAt, updatedAt = updatedAt
    )

    private fun Note.toCached() = CachedNote(
        id = id, userId = userId, noteName = noteName,
        content = content, tags = tags, isPinned = isPinned,
        createdAt = createdAt, updatedAt = updatedAt
    )

    private fun CachedFlashcard.toDomain() = Flashcard(
        id = id, userId = userId, noteId = noteId,
        question = question, answer = answer, difficulty = difficulty,
        nextReviewAt = nextReviewAt, easeFactor = easeFactor, interval = interval
    )

    private fun Flashcard.toCached() = CachedFlashcard(
        id = id, userId = userId, noteId = noteId,
        question = question, answer = answer, difficulty = difficulty,
        nextReviewAt = nextReviewAt, easeFactor = easeFactor, interval = interval,
        reviewCount = 0  // not exposed in Android model, default 0
    )

    private fun CachedUser.toDomain() = User(
        id = id, loginName = loginName, nickname = nickname,
        email = email, role = role, avatarUrl = avatarUrl
    )

    private fun User.toCached() = CachedUser(
        id = id, loginName = loginName, nickname = nickname,
        email = email, role = role, avatarUrl = avatarUrl
    )
}
