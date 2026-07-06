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

    private val _sessionExpired = MutableStateFlow(false)
    val sessionExpired: StateFlow<Boolean> = _sessionExpired.asStateFlow()

    companion object {
        private val TOKEN_KEY = stringPreferencesKey("auth_token")
        private val USER_KEY = stringPreferencesKey("user_data")
        private val LOGIN_NAME_KEY = stringPreferencesKey("login_name")
        private val PASSWORD_KEY = stringPreferencesKey("saved_password")
        private val REMEMBER_KEY = stringPreferencesKey("remember_password")
    }

    suspend fun saveSession(token: String, user: User, loginName: String = "", password: String = "", remember: Boolean = false) {
        dataStore.edit { prefs ->
            prefs[TOKEN_KEY] = token
            prefs[USER_KEY] = gson.toJson(user)
            if (remember) {
                prefs[LOGIN_NAME_KEY] = loginName
                prefs[PASSWORD_KEY] = password
                prefs[REMEMBER_KEY] = "true"
            } else {
                prefs.remove(LOGIN_NAME_KEY)
                prefs.remove(PASSWORD_KEY)
                prefs.remove(REMEMBER_KEY)
            }
        }
        tokenFlow.value = token
        _currentUser.value = user
        _isLoggedIn.value = true
    }

    suspend fun getSavedCredentials(): Triple<String, String, Boolean> {
        val prefs = dataStore.data.first()
        val remember = prefs[REMEMBER_KEY] == "true"
        return Triple(
            if (remember) prefs[LOGIN_NAME_KEY] ?: "" else "",
            if (remember) prefs[PASSWORD_KEY] ?: "" else "",
            remember
        )
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

    suspend fun clearSession(expired: Boolean = false) {
        dataStore.edit { prefs ->
            prefs.remove(TOKEN_KEY)
            prefs.remove(USER_KEY)
        }
        tokenFlow.value = null
        _currentUser.value = null
        _isLoggedIn.value = false
        if (expired) _sessionExpired.value = true
    }

    fun resetSessionExpired() {
        _sessionExpired.value = false
    }

    suspend fun updateCurrentUser(user: User) {
        _currentUser.value = user
        dataStore.edit { prefs ->
            prefs[USER_KEY] = gson.toJson(user)
        }
    }

    suspend fun getToken(): String? {
        val prefs = dataStore.data.first()
        return prefs[TOKEN_KEY]
    }

    fun getTokenSync(): String? = tokenFlow.value
}
