package com.aura.mas.data.repository

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.aura.mas.util.Constants
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Runtime-configurable server URLs.
 * Loaded from DataStore on app start, can be changed from the settings screen.
 */
@Singleton
class ServerConfig @Inject constructor(
    private val dataStore: DataStore<Preferences>
) {
    companion object {
        private val JAVA_URL_KEY = stringPreferencesKey("server_java_url")
        private val PYTHON_URL_KEY = stringPreferencesKey("server_python_url")
    }

    private val _javaUrl = MutableStateFlow(Constants.JAVA_BASE_URL)
    val javaUrl: StateFlow<String> = _javaUrl.asStateFlow()

    private val _pythonUrl = MutableStateFlow(Constants.PYTHON_BASE_URL)
    val pythonUrl: StateFlow<String> = _pythonUrl.asStateFlow()

    /**
     * Load saved URLs from DataStore. Call on app startup.
     */
    suspend fun load() {
        val prefs = dataStore.data.first()
        val savedJava = prefs[JAVA_URL_KEY]
        val savedPython = prefs[PYTHON_URL_KEY]
        if (!savedJava.isNullOrBlank()) _javaUrl.value = savedJava
        if (!savedPython.isNullOrBlank()) _pythonUrl.value = savedPython
    }

    /**
     * Save new URLs to DataStore and update runtime state.
     */
    suspend fun save(javaUrl: String, pythonUrl: String) {
        val j = javaUrl.trim().trimEnd('/')
        val p = pythonUrl.trim().trimEnd('/')
        dataStore.edit { prefs ->
            prefs[JAVA_URL_KEY] = "$j/"
            prefs[PYTHON_URL_KEY] = "$p/"
        }
        _javaUrl.value = "$j/"
        _pythonUrl.value = "$p/"
    }

    /**
     * Reset to default values from Constants.
     */
    suspend fun resetToDefaults() {
        dataStore.edit { prefs ->
            prefs.remove(JAVA_URL_KEY)
            prefs.remove(PYTHON_URL_KEY)
        }
        _javaUrl.value = Constants.JAVA_BASE_URL
        _pythonUrl.value = Constants.PYTHON_BASE_URL
    }
}
