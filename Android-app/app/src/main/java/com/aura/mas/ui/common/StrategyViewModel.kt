package com.aura.mas.ui.common

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.api.ApiService
import com.aura.mas.data.model.LearningStrategy
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class StrategyViewModel @Inject constructor(
    private val apiService: ApiService
) : ViewModel() {

    private val _pendingCount = MutableStateFlow(0)
    val pendingCount = _pendingCount.asStateFlow()

    private val _strategies = MutableStateFlow<List<LearningStrategy>>(emptyList())
    val strategies = _strategies.asStateFlow()

    private val _loading = MutableStateFlow(false)
    val loading = _loading.asStateFlow()

    init {
        startPolling()
    }

    private fun startPolling() {
        viewModelScope.launch {
            while (true) {
                try {
                    _pendingCount.value = apiService.getPendingStrategyCount().data ?: 0
                } catch (_: Exception) { }
                delay(60_000)
            }
        }
    }

    fun loadStrategies() {
        viewModelScope.launch {
            _loading.value = true
            try {
                _strategies.value = apiService.getPendingStrategies().data ?: emptyList()
            } catch (_: Exception) { }
            _loading.value = false
        }
    }

    fun acceptStrategy(strategyId: Long) {
        viewModelScope.launch {
            try {
                apiService.acceptStrategy(strategyId)
                _strategies.value = _strategies.value.filter { it.id != strategyId }
                _pendingCount.value = maxOf(0, _pendingCount.value - 1)
            } catch (_: Exception) { }
        }
    }

    fun rejectStrategy(strategyId: Long) {
        viewModelScope.launch {
            try {
                apiService.rejectStrategy(strategyId)
                _strategies.value = _strategies.value.filter { it.id != strategyId }
                _pendingCount.value = maxOf(0, _pendingCount.value - 1)
            } catch (_: Exception) { }
        }
    }
}
