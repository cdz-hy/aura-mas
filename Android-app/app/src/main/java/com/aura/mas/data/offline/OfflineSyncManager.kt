package com.aura.mas.data.offline

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.*
import com.aura.mas.data.api.ApiService
import com.aura.mas.data.local.dao.*
import com.aura.mas.data.local.entity.*
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

@HiltWorker
class OfflineSyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val api: ApiService,
    private val planDao: PlanDao,
    private val resourceDao: ResourceDao,
    private val noteDao: NoteDao,
    private val flashcardDao: FlashcardDao
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            // Sync plans
            val plans = api.getPlans(size = 100)
            if (plans.isSuccess && plans.data != null) {
                planDao.deleteAll()
                planDao.insertAll(plans.data.records.map {
                    CachedPlan(it.id, it.userId, it.title, it.learningGoal, it.status, it.createdAt, it.updatedAt)
                })
            }

            // Sync notes
            val notes = api.getNotes(size = 100)
            if (notes.isSuccess && notes.data != null) {
                noteDao.deleteAll()
                noteDao.insertAll(notes.data.records.map {
                    CachedNote(it.id, it.userId, it.noteName, it.content, it.createdAt, it.updatedAt)
                })
            }

            // Sync resources for each plan
            plans.data?.records?.forEach { plan ->
                val resources = api.getResourcesByPlan(plan.id)
                if (resources.isSuccess && resources.data != null) {
                    resourceDao.deleteByPlan(plan.id)
                    resourceDao.insertAll(resources.data.map {
                        CachedResource(it.id, it.planId, it.moduleType, it.moduleOrder, it.getModuleName(), it.getResourceTitle(), it.getResourceType(), it.getContent(), it.status)
                    })
                }
            }

            Result.success()
        } catch (e: Exception) {
            if (runAttemptCount < 3) Result.retry() else Result.failure()
        }
    }
}

object OfflineSyncScheduler {
    private const val SYNC_WORK_NAME = "aura_offline_sync"

    fun schedule(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val syncRequest = PeriodicWorkRequestBuilder<OfflineSyncWorker>(
            6, TimeUnit.HOURS,
            30, TimeUnit.MINUTES
        )
            .setConstraints(constraints)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 10, TimeUnit.MINUTES)
            .build()

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            SYNC_WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            syncRequest
        )
    }

    fun triggerImmediateSync(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val syncRequest = OneTimeWorkRequestBuilder<OfflineSyncWorker>()
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(context).enqueue(syncRequest)
    }

    fun cancel(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(SYNC_WORK_NAME)
    }
}
