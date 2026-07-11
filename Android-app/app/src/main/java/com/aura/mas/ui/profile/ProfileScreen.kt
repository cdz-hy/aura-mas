package com.aura.mas.ui.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.StudentProfile
import com.aura.mas.data.repository.AuthStore
import com.aura.mas.data.api.ApiService
import com.aura.mas.ui.common.UserAvatar
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(
    val isLoading: Boolean = true,
    val profile: StudentProfile? = null,
    val error: String? = null
)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    val authStore: AuthStore,
    private val api: ApiService
) : ViewModel() {
    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    init { loadProfile() }

    fun loadProfile() {
        viewModelScope.launch {
            _uiState.value = ProfileUiState(isLoading = true)
            try {
                val result = api.getUserProfile()
                _uiState.value = ProfileUiState(isLoading = false, profile = result.data)
            } catch (e: Exception) {
                _uiState.value = ProfileUiState(isLoading = false, error = e.message)
            }
        }
    }

    fun logout(onDone: () -> Unit) {
        viewModelScope.launch {
            authStore.clearSession()
            onDone()
        }
    }
}

@Composable
fun ProfileScreen(
    onLearningProfileClick: () -> Unit,
    onSettingsClick: () -> Unit,
    onAnalyticsClick: () -> Unit,
    onAdminClick: () -> Unit,
    onKnowledgeGraphClick: (Long) -> Unit,
    viewModel: ProfileViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val user by viewModel.authStore.currentUser.collectAsState()

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 32.dp)
    ) {
        // Profile header
        item {
            Box(
                modifier = Modifier.fillMaxWidth()
                    .background(MaterialTheme.colorScheme.primaryContainer)
                    .padding(top = 48.dp, bottom = 24.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    UserAvatar(
                        avatarUrl = user?.avatarUrl,
                        nickname = user?.nickname ?: "U",
                        size = 72
                    )
                    Spacer(Modifier.height(12.dp))
                    Text(
                        user?.nickname ?: "用户",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        user?.email ?: "",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                    )
                    if (user?.role == "admin") {
                        Spacer(Modifier.height(4.dp))
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = MaterialTheme.colorScheme.primary
                        ) {
                            Text("管理员", modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                                style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onPrimary)
                        }
                    }
                }
            }
        }

        // Radar chart
        item {
            val profile = uiState.profile
            if (profile?.learningBehavior != null) {
                Spacer(Modifier.height(16.dp))
                Card(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).clickable(onClick = onLearningProfileClick),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text("学习画像", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                        Spacer(Modifier.height(12.dp))
                        val dims = profile.learningBehavior!!
                        com.aura.mas.ui.components.charts.RadarChart(
                            data = listOf(
                                com.aura.mas.ui.components.charts.RadarData("感知 ↔ 直觉", ((dims.sensingIntuitive + 1) / 2).toFloat()),
                                com.aura.mas.ui.components.charts.RadarData("视觉 ↔ 言语", ((dims.visualVerbal + 1) / 2).toFloat()),
                                com.aura.mas.ui.components.charts.RadarData("活跃 ↔ 沉思", ((dims.activeReflective + 1) / 2).toFloat()),
                                com.aura.mas.ui.components.charts.RadarData("循序 ↔ 全局", ((dims.sequentialGlobal + 1) / 2).toFloat())
                            ),
                            modifier = Modifier.fillMaxWidth().height(200.dp)
                        )
                    }
                }
            }
        }

        // Menu items
        item {
            Spacer(Modifier.height(16.dp))
            ProfileMenuItem(Icons.Default.PersonSearch, "详细学习画像", onLearningProfileClick)
            ProfileMenuItem(Icons.Default.Hub, "知识图谱") {
                onKnowledgeGraphClick(user?.id ?: 0L)
            }
            ProfileMenuItem(Icons.Default.BarChart, "学习分析", onAnalyticsClick)
            ProfileMenuItem(Icons.Default.Settings, "设置", onSettingsClick)
            if (user?.role == "admin") {
                ProfileMenuItem(Icons.Default.AdminPanelSettings, "管理后台", onAdminClick)
            }
        }
    }
}

@Composable
private fun ProfileMenuItem(icon: ImageVector, title: String, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp).clickable(onClick = onClick),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(icon, null, tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.width(16.dp))
            Text(title, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
            Icon(Icons.Default.ChevronRight, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
