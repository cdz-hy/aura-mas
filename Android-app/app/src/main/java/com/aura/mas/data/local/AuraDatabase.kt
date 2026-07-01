package com.aura.mas.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.aura.mas.data.local.dao.*
import com.aura.mas.data.local.entity.*

@Database(
    entities = [
        CachedPlan::class,
        CachedResource::class,
        CachedNote::class,
        CachedFlashcard::class,
        CachedUser::class
    ],
    version = 1,
    exportSchema = false
)
abstract class AuraDatabase : RoomDatabase() {
    abstract fun planDao(): PlanDao
    abstract fun resourceDao(): ResourceDao
    abstract fun noteDao(): NoteDao
    abstract fun flashcardDao(): FlashcardDao
    abstract fun userDao(): UserDao
}
