package com.aura.mas.di

import android.content.Context
import androidx.room.Room
import com.aura.mas.data.local.AuraDatabase
import com.aura.mas.data.local.dao.*
import com.aura.mas.util.Constants
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AuraDatabase {
        return Room.databaseBuilder(
            context,
            AuraDatabase::class.java,
            Constants.DATABASE_NAME
        ).build()
    }

    @Provides
    fun providePlanDao(db: AuraDatabase): PlanDao = db.planDao()

    @Provides
    fun provideResourceDao(db: AuraDatabase): ResourceDao = db.resourceDao()

    @Provides
    fun provideNoteDao(db: AuraDatabase): NoteDao = db.noteDao()

    @Provides
    fun provideFlashcardDao(db: AuraDatabase): FlashcardDao = db.flashcardDao()

    @Provides
    fun provideUserDao(db: AuraDatabase): UserDao = db.userDao()
}
