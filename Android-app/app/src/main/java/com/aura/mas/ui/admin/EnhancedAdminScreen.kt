package com.aura.mas.ui.admin

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.*
import com.aura.mas.data.repository.AdminRepository
import com.aura.mas.ui.common.*
import com.aura.mas.ui.theme.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AdminUsersUiState(
    val isLoading: Boolean = true,
    val users: List<User> = emptyList(),
    val total: Long = 0,
    val page: Int = 1,
    val error: String? = null
)

data class AdminLogsUiState(
    val isLoading: Boolean = true,
    val logs: List<SystemLog> = emptyList(),
    val total: Long = 0,
    val page: Int = 1,
    val error: String? = null
)

@HiltViewModel
class AdminUsersViewModel @Inject constructor(
    private val adminRepo: AdminRepository,
    private val networkUtil: com.aura.mas.util.NetworkUtil
) : ViewModel() {
    private val _uiState = MutableStateFlow(AdminUsersUiState())
    val uiState: StateFlow<AdminUsersUiState> = _uiState.asStateFlow()

    init { loadUsers() }

    fun loadUsers(page: Int = 1) {
        viewModelScope.launch {
            _uiState.value = AdminUsersUiState(isLoading = true)
            try {
                val result = adminRepo.getUsers(page)
                if (result.isSuccess) {
                    _uiState.value = AdminUsersUiState(
                        isLoading = false,
                        users = result.data?.records ?: emptyList(),
                        total = result.data?.total ?: 0,
                        page = page
                    )
                } else {
                    _uiState.value = AdminUsersUiState(isLoading = false, error = result.message.ifEmpty { "获取失败" })
                }
            } catch (e: Exception) {
                _uiState.value = AdminUsersUiState(isLoading = false, error = e.message)
            }
        }
    }

    fun toggleStatus(userId: Long, currentStatus: Int) {
        if (!networkUtil.isOnline()) {
            _uiState.value = _uiState.value.copy(error = "离线状态，无法操作")
            return
        }
        viewModelScope.launch {
            adminRepo.toggleUserStatus(userId, if (currentStatus == 1) 0 else 1)
            loadUsers(_uiState.value.page)
        }
    }
}

@HiltViewModel
class AdminLogsViewModel @Inject constructor(
    private val adminRepo: AdminRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(AdminLogsUiState())
    val uiState: StateFlow<AdminLogsUiState> = _uiState.asStateFlow()

    init { loadLogs() }

    fun loadLogs(page: Int = 1) {
        viewModelScope.launch {
            _uiState.value = AdminLogsUiState(isLoading = true)
            try {
                val result = adminRepo.getLogs(page)
                if (result.isSuccess) {
                    _uiState.value = AdminLogsUiState(
                        isLoading = false,
                        logs = result.data?.records ?: emptyList(),
                        total = result.data?.total ?: 0,
                        page = page
                    )
                } else {
                    _uiState.value = AdminLogsUiState(isLoading = false, error = result.message.ifEmpty { "获取失败" })
                }
            } catch (e: Exception) {
                _uiState.value = AdminLogsUiState(isLoading = false, error = e.message)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EnhancedAdminUsersScreen(
    onBack: () -> Unit,
    viewModel: AdminUsersViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("用户管理", fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "返回") }
                }
            )
        }
    ) { padding ->
        if (uiState.isLoading) {
            LoadingIndicator(Modifier.padding(padding))
            return@Scaffold
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            item {
                Text("共 ${uiState.total} 位用户", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
            }

            items(uiState.users, key = { it.id }) { user ->
                Card(
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        UserAvatar(user.avatarUrl, user.nickname, 40)
                        Spacer(Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(user.nickname.ifEmpty { user.loginName }, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                            Text(user.email.ifEmpty { user.loginName }, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Row {
                                Surface(
                                    shape = RoundedCornerShape(4.dp),
                                    color = if (user.role == "admin") MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.surfaceVariant
                                ) {
                                    Text(
                                        if (user.role == "admin") "管理员" else "学生",
                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                        style = MaterialTheme.typography.labelSmall
                                    )
                                }
                                Spacer(Modifier.width(4.dp))
                                Surface(
                                    shape = RoundedCornerShape(4.dp),
                                    color = if (user.status == 1) Emerald50.copy(alpha = 0.5f) else Red50
                                ) {
                                    Text(
                                        if (user.status == 1) "正常" else "禁用",
                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                        style = MaterialTheme.typography.labelSmall,
                                        color = if (user.status == 1) Emerald500 else Red500
                                    )
                                }
                            }
                        }
                        Switch(
                            checked = user.status == 1,
                            onCheckedChange = { viewModel.toggleStatus(user.id, user.status) }
                        )
                    }
                }
            }

            // Pagination
            if (uiState.total > 20) {
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center
                    ) {
                        TextButton(
                            onClick = { viewModel.loadUsers(uiState.page - 1) },
                            enabled = uiState.page > 1
                        ) { Text("上一页") }
                        Spacer(Modifier.width(16.dp))
                        Text("第 ${uiState.page} 页", style = MaterialTheme.typography.bodySmall, modifier = Modifier.align(Alignment.CenterVertically))
                        Spacer(Modifier.width(16.dp))
                        TextButton(
                            onClick = { viewModel.loadUsers(uiState.page + 1) },
                            enabled = uiState.page * 20 < uiState.total
                        ) { Text("下一页") }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EnhancedAdminLogsScreen(
    onBack: () -> Unit,
    viewModel: AdminLogsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("系统日志", fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "返回") }
                }
            )
        }
    ) { padding ->
        if (uiState.isLoading) {
            LoadingIndicator(Modifier.padding(padding))
            return@Scaffold
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            item {
                Text("共 ${uiState.total} 条日志", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
            }

            items(uiState.logs, key = { it.id }) { log ->
                Card(
                    shape = RoundedCornerShape(10.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(Modifier.padding(12.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Surface(
                                shape = RoundedCornerShape(4.dp),
                                color = when (log.status) {
                                    1 -> Emerald50.copy(alpha = 0.5f)
                                    else -> Red50
                                }
                            ) {
                                Text(
                                    log.operationType,
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = if (log.status == 1) Emerald500 else Red500
                                )
                            }
                            Spacer(Modifier.width(8.dp))
                            Text(log.module, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Spacer(Modifier.weight(1f))
                            Text(log.createdAt.take(16), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                        }
                        Spacer(Modifier.height(4.dp))
                        Text(log.operationDesc, style = MaterialTheme.typography.bodySmall)
                        if (log.errorMsg != null) {
                            Text(log.errorMsg, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                        }
                    }
                }
            }

            if (uiState.total > 20) {
                item {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                        TextButton(onClick = { viewModel.loadLogs(uiState.page - 1) }, enabled = uiState.page > 1) { Text("上一页") }
                        Spacer(Modifier.width(16.dp))
                        Text("第 ${uiState.page} 页", style = MaterialTheme.typography.bodySmall, modifier = Modifier.align(Alignment.CenterVertically))
                        Spacer(Modifier.width(16.dp))
                        TextButton(onClick = { viewModel.loadLogs(uiState.page + 1) }, enabled = uiState.page * 20 < uiState.total) { Text("下一页") }
                    }
                }
            }
        }
    }
}
