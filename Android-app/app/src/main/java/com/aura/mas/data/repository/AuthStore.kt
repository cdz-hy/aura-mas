package com.aura.mas.data.repository

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.aura.mas.data.model.User
import com.google.gson.Gson
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import javax.inject.Inject
import javax.inject.Named
import javax.inject.Singleton

@Singleton
class AuthStore @Inject constructor(
    private val dataStore: DataStore<Preferences>,
    private val gson: Gson,
    @Named("token_datastore") private val tokenFlow: MutableStateFlow<String?>
) {
    private val _currentUser = MutableStateFlow<User?>(null)
    val currentUser: StateFlow<User?> = _currentUser.asStateFlow()

    private val _isLoggedIn = MutableStateFlow(false)
    val isLoggedIn: StateFlow<Boolean> = _isLoggedIn.asStateFlow()

    companion object {
        private val TOKEN_KEY = stringPreferencesKey("auth_token")
        private val USER_KEY = stringPreferencesKey("user_data")
    }

    suspend fun saveSession(token: String, user: User) {
        dataStore.edit { prefs ->
            prefs[TOKEN_KEY] = token
            prefs[USER_KEY] = gson.toJson(user)
        }
        tokenFlow.value = token
        _currentUser.value = user
        _isLoggedIn.value = true
    }

    suspend fun restoreSession(): Boolean {
        return try {
            val prefs = dataStore.data.first()
            val token = prefs[TOKEN_KEY]
            val userJson = prefs[USER_KEY]
            if (!token.isNullOrBlank() && !userJson.isNullOrBlank()) {
                tokenFlow.value = token
                _currentUser.value = gson.fromJson(userJson, User::class.java)
                _isLoggedIn.value = true
                true
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }

    suspend fun clearSession() {
        dataStore.edit { prefs ->
            prefs.remove(TOKEN_KEY)
            prefs.remove(USER_KEY)
        }
        tokenFlow.value = null
        _currentUser.value = null
        _isLoggedIn.value = false
    }

    suspend fun getToken(): String? {
        val prefs = dataStore.data.first()
        return prefs[TOKEN_KEY]
    }

    fun getTokenSync(): String? = tokenFlow.value
}
