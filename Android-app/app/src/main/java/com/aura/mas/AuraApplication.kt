package com.aura.mas

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.aura.mas.data.offline.OfflineSyncScheduler
import com.aura.mas.service.NotificationHelper
import com.aura.mas.service.ReminderScheduler
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

@HiltAndroidApp
class AuraApplication : Application(), Configuration.Provider {

    @Inject
    lateinit var workerFactory: HiltWorkerFactory

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()

    override fun onCreate() {
        super.onCreate()
        NotificationHelper(this)
        OfflineSyncScheduler.schedule(this)
        ReminderScheduler.schedule(this)
    }
}
