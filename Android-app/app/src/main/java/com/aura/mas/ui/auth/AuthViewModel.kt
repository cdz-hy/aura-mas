package com.aura.mas.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.api.ApiService
import com.aura.mas.data.model.LoginRequest
import com.aura.mas.data.model.RegisterRequest
import com.aura.mas.data.repository.AuthStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val success: Boolean = false
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    val authStore: AuthStore,
    private val api: ApiService
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            authStore.restoreSession()
        }
    }

    fun login(loginName: String, password: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            try {
                val response = api.login(LoginRequest(loginName, password))
                if (response.code == 0 && response.data != null) {
                    authStore.saveSession(response.data.token, response.data.user)
                    _uiState.value = AuthUiState(success = true)
                } else {
                    _uiState.value = AuthUiState(error = response.message.ifEmpty { "登录失败" })
                }
            } catch (e: Exception) {
                _uiState.value = AuthUiState(error = e.message ?: "网络错误")
            }
        }
    }

    fun register(loginName: String, password: String, nickname: String, email: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            try {
                val response = api.register(RegisterRequest(loginName, password, nickname, email))
                if (response.code == 0) {
                    _uiState.value = AuthUiState(success = true)
                } else {
                    _uiState.value = AuthUiState(error = response.message.ifEmpty { "注册失败" })
                }
            } catch (e: Exception) {
                _uiState.value = AuthUiState(error = e.message ?: "网络错误")
            }
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
