package com.aura.mas.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "cached_plans")
data class CachedPlan(
    @PrimaryKey val id: Long,
    val userId: Long,
    val title: String,
    val learningGoal: String?,
    val status: Int,
    val createdAt: String?,
    val updatedAt: String?,
    val cachedAt: Long = System.currentTimeMillis()
)

@Entity(
    tableName = "cached_resources",
    indices = [androidx.room.Index(value = ["planId"])]
)
data class CachedResource(
    @PrimaryKey val id: Long,
    val planId: Long,
    val moduleType: String,
    val moduleOrder: Int,
    val moduleName: String,
    val resourceTitle: String,
    val resourceType: String,
    /** Full JSON string of the resource's moduleData – stored intact for lossless offline display */
    val moduleDataJson: String?,
    val status: Int,
    val storagePath: String? = null,  // mirrors Java entity
    val version: Int = 0,             // mirrors Java entity
    val cachedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "cached_notes")
data class CachedNote(
    @PrimaryKey val id: Long,
    val userId: Long,
    val noteName: String,
    val content: String,
    val tags: String? = null,         // mirrors Java Note.tags
    val isPinned: Int = 0,            // mirrors Java Note.isPinned
    val createdAt: String?,
    val updatedAt: String?,
    val cachedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "cached_flashcards")
data class CachedFlashcard(
    @PrimaryKey val id: Long,
    val userId: Long,
    val noteId: Long,
    val question: String,
    val answer: String,
    val difficulty: Int,
    val nextReviewAt: String?,
    val easeFactor: Double,
    val interval: Int,
    val reviewCount: Int = 0,         // mirrors Java Flashcard.reviewCount
    val cachedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "cached_user")
data class CachedUser(
    @PrimaryKey val id: Long,
    val loginName: String,
    val nickname: String,
    val email: String,
    val role: String,
    val avatarUrl: String?,
    val cachedAt: Long = System.currentTimeMillis()
)
