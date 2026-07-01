package com.aura.mas.di

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.aura.mas.data.api.AuthInterceptor
import com.aura.mas.util.SseClient
import com.google.gson.Gson
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.flow.MutableStateFlow
import javax.inject.Named
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "aura_prefs")

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideDataStore(@ApplicationContext context: Context): DataStore<Preferences> {
        return context.dataStore
    }

    @Provides
    @Singleton
    @Named("token_datastore")
    fun provideTokenFlow(): MutableStateFlow<String?> {
        return MutableStateFlow(null)
    }

    @Provides
    @Singleton
    fun provideAuthInterceptor(@Named("token_datastore") tokenFlow: MutableStateFlow<String?>): AuthInterceptor {
        return AuthInterceptor(tokenFlow)
    }
}
