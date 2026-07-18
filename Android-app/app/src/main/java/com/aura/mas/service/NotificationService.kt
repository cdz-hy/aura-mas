package com.aura.mas.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.*
import com.aura.mas.MainActivity
import com.aura.mas.data.api.ApiService
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

class NotificationHelper(private val context: Context) {

    companion object {
        const val CHANNEL_FLASHCARD = "flashcard_reminder"
        const val CHANNEL_GENERAL = "general"
    }

    init {
        createChannels()
    }

    private fun createChannels() {
        val flashcardChannel = NotificationChannel(
            CHANNEL_FLASHCARD,
            "闪卡复习提醒",
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = "提醒你复习到期的闪卡"
        }

        val generalChannel = NotificationChannel(
            CHANNEL_GENERAL,
            "一般通知",
            NotificationManager.IMPORTANCE_LOW
        )

        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(flashcardChannel)
        manager.createNotificationChannel(generalChannel)
    }

    fun showFlashcardReminder(dueCount: Int) {
        val intent = Intent(context, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            context, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_FLASHCARD)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("闪卡复习提醒")
            .setContentText("你有 $dueCount 张闪卡需要复习")
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()

        val manager = context.getSystemService(NotificationManager::class.java)
        manager.notify(1001, notification)
    }
}

class FlashcardReminderWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val api: ApiService
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            val result = api.getDueFlashcardCount()
            if (result.isSuccess && result.data != null && result.data > 0) {
                NotificationHelper(applicationContext).showFlashcardReminder(result.data)
            }
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}

object ReminderScheduler {
    fun schedule(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val request = PeriodicWorkRequestBuilder<FlashcardReminderWorker>(
            24, TimeUnit.HOURS
        )
            .setConstraints(constraints)
            .setInitialDelay(1, TimeUnit.HOURS)
            .build()

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            "flashcard_reminder",
            ExistingPeriodicWorkPolicy.KEEP,
            request
        )
    }
}
