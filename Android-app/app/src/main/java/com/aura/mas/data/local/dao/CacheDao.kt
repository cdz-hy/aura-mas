package com.aura.mas.data.local.dao

import androidx.room.*
import com.aura.mas.data.local.entity.*
import kotlinx.coroutines.flow.Flow

@Dao
interface PlanDao {
    @Query("SELECT * FROM cached_plans ORDER BY id DESC")
    fun getAllPlans(): Flow<List<CachedPlan>>

    @Query("SELECT * FROM cached_plans ORDER BY id DESC")
    suspend fun getAllPlansSync(): List<CachedPlan>

    @Query("SELECT * FROM cached_plans WHERE id = :id")
    suspend fun getPlanById(id: Long): CachedPlan?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(plans: List<CachedPlan>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(plan: CachedPlan)

    @Delete
    suspend fun delete(plan: CachedPlan)

    @Query("DELETE FROM cached_plans")
    suspend fun deleteAll()
}

@Dao
interface ResourceDao {
    @Query("SELECT * FROM cached_resources WHERE planId = :planId ORDER BY moduleOrder")
    fun getResourcesByPlan(planId: Long): Flow<List<CachedResource>>

    @Query("SELECT * FROM cached_resources WHERE planId = :planId ORDER BY moduleOrder")
    suspend fun getResourcesByPlanSync(planId: Long): List<CachedResource>

    @Query("SELECT * FROM cached_resources WHERE id = :id")
    suspend fun getResourceById(id: Long): CachedResource?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(resources: List<CachedResource>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(resource: CachedResource)

    @Delete
    suspend fun delete(resource: CachedResource)

    @Query("DELETE FROM cached_resources WHERE planId = :planId")
    suspend fun deleteByPlan(planId: Long)

    @Query("SELECT * FROM cached_resources")
    suspend fun getAllResourcesSync(): List<CachedResource>

    @Query("DELETE FROM cached_resources")
    suspend fun deleteAll()
}

@Dao
interface NoteDao {
    @Query("SELECT * FROM cached_notes ORDER BY id DESC")
    fun getAllNotes(): Flow<List<CachedNote>>

    @Query("SELECT * FROM cached_notes ORDER BY id DESC")
    suspend fun getAllNotesSync(): List<CachedNote>

    @Query("SELECT * FROM cached_notes WHERE id = :id")
    suspend fun getNoteById(id: Long): CachedNote?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(notes: List<CachedNote>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(note: CachedNote)

    @Delete
    suspend fun delete(note: CachedNote)

    @Query("DELETE FROM cached_notes")
    suspend fun deleteAll()
}

@Dao
interface FlashcardDao {
    @Query("SELECT * FROM cached_flashcards WHERE noteId = :noteId")
    fun getFlashcardsByNote(noteId: Long): Flow<List<CachedFlashcard>>

    @Query("SELECT * FROM cached_flashcards WHERE nextReviewAt <= :now ORDER BY nextReviewAt")
    fun getDueFlashcards(now: String): Flow<List<CachedFlashcard>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(cards: List<CachedFlashcard>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(card: CachedFlashcard)

    @Delete
    suspend fun delete(card: CachedFlashcard)

    @Query("DELETE FROM cached_flashcards")
    suspend fun deleteAll()

    @Query("SELECT * FROM cached_flashcards")
    suspend fun getAllFlashcardsSync(): List<CachedFlashcard>
}

@Dao
interface UserDao {
    @Query("SELECT * FROM cached_user LIMIT 1")
    suspend fun getCachedUser(): CachedUser?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(user: CachedUser)

    @Query("DELETE FROM cached_user")
    suspend fun deleteAll()
}
