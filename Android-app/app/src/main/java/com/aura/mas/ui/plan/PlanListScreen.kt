package com.aura.mas.ui.plan

import androidx.compose.foundation.clickable
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import com.aura.mas.ui.components.SvgIcon
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.model.*
import com.aura.mas.data.repository.PlanRepository
import com.aura.mas.data.api.ApiService
import com.aura.mas.ui.common.*
import com.aura.mas.ui.theme.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PlanListUiState(
    val isLoading: Boolean = true,
    val plans: List<LearningPlan> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class PlanListViewModel @Inject constructor(
    private val planRepo: PlanRepository,
    private val api: ApiService
) : ViewModel() {
    private val _uiState = MutableStateFlow(PlanListUiState())
    val uiState: StateFlow<PlanListUiState> = _uiState.asStateFlow()

    init { loadPlans() }

    fun loadPlans() {
        viewModelScope.launch {
            _uiState.value = PlanListUiState(isLoading = true)
            try {
                api.getPlans(size = 50).let { result ->
                    if (result.code == 0 && result.data != null) {
                        val plans = result.data.records
                        // Calculate progress for each plan
                        val plansWithProgress = plans.map { plan ->
                            try {
                                val resourcesResult = api.getResourcesByPlan(plan.id)
                                val progressResult = planRepo.getProgress(plan.id)
                                val resources = resourcesResult.data ?: emptyList()
                                val progress = progressResult.data ?: emptyList()
                                val validResourceIds = resources.filter { it.status >= LearningResource.STATUS_READY }.map { it.id }.toSet()
                                val completed = progress.count { it.completed && it.resourceId in validResourceIds }
                                val total = validResourceIds.size
                                val progressPercent = if (total > 0) (completed * 100 / total).coerceIn(0, 100) else 0
                                plan.copy(progress = progressPercent.toDouble())
                            } catch (e: Exception) {
                                plan
                            }
                        }
                        _uiState.value = PlanListUiState(plans = plansWithProgress, isLoading = false)
                    } else {
                        _uiState.value = PlanListUiState(error = result.message, isLoading = false)
                    }
                }
            } catch (e: Exception) {
                _uiState.value = PlanListUiState(error = e.message, isLoading = false)
            }
        }
    }

    fun deletePlan(planId: Long) {
        viewModelScope.launch {
            api.deletePlan(planId)
            loadPlans()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlanListScreen(
    onPlanClick: (Long) -> Unit,
    onCreatePlan: () -> Unit,
    viewModel: PlanListViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("学习计划", fontWeight = FontWeight.SemiBold) },
                windowInsets = WindowInsets(0.dp),
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        },
        contentWindowInsets = WindowInsets(0.dp),
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onCreatePlan,
                icon = { Icon(Icons.Default.Add, null) },
                text = { Text("创建计划") },
                shape = RoundedCornerShape(16.dp)
            )
        }
    ) { padding ->
        if (uiState.isLoading) {
            LoadingIndicator(Modifier.padding(padding))
            return@Scaffold
        }

        if (uiState.error != null) {
            ErrorState(
                message = uiState.error ?: "未知错误",
                onRetry = { viewModel.loadPlans() },
                modifier = Modifier.padding(padding)
            )
            return@Scaffold
        }

        if (uiState.plans.isEmpty()) {
            EmptyState(
                Icons.Outlined.MenuBook,
                "暂无学习计划",
                "点击右下角按钮创建你的第一个学习计划",
                Modifier.padding(padding)
            )
            return@Scaffold
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(uiState.plans, key = { it.id }) { plan ->
                var showMenu by remember { mutableStateOf(false) }
                Card(
                    modifier = Modifier.fillMaxWidth().clickable { onPlanClick(plan.id) },
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Plan icon - prefer SVG from planConfig, fall back to Material icon
                        val iconSvg = plan.getIconSvg()
                        Box(
                            modifier = Modifier
                                .size(44.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(
                                    if (plan.getEffectiveStatus() == LearningPlan.STATUS_COMPLETED)
                                        MaterialTheme.colorScheme.secondaryContainer
                                    else MaterialTheme.colorScheme.primaryContainer
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            if (!iconSvg.isNullOrBlank()) {
                                SvgIcon(svgString = iconSvg, modifier = Modifier.size(40.dp))
                            } else {
                                Icon(
                                    when (plan.getEffectiveStatus()) {
                                        LearningPlan.STATUS_COMPLETED -> Icons.Default.CheckCircle
                                        LearningPlan.STATUS_GENERATING -> Icons.Default.Sync
                                        else -> Icons.Default.MenuBook
                                    },
                                    null,
                                    tint = when (plan.getEffectiveStatus()) {
                                        LearningPlan.STATUS_COMPLETED -> MaterialTheme.colorScheme.secondary
                                        LearningPlan.STATUS_GENERATING -> MaterialTheme.colorScheme.tertiary
                                        else -> MaterialTheme.colorScheme.primary
                                    },
                                    modifier = Modifier.size(24.dp)
                                )
                            }
                        }
                        Spacer(Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(plan.title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                            Spacer(Modifier.height(4.dp))
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                // Status chip
                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = when (plan.getEffectiveStatus()) {
                                        LearningPlan.STATUS_COMPLETED -> MaterialTheme.colorScheme.secondary.copy(alpha = 0.12f)
                                        LearningPlan.STATUS_GENERATING -> MaterialTheme.colorScheme.tertiary.copy(alpha = 0.12f)
                                        else -> MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)
                                    }
                                ) {
                                    Text(
                                        plan.getStatusText(),
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                                        style = MaterialTheme.typography.labelSmall,
                                        color = when (plan.getEffectiveStatus()) {
                                            LearningPlan.STATUS_COMPLETED -> MaterialTheme.colorScheme.secondary
                                            LearningPlan.STATUS_GENERATING -> MaterialTheme.colorScheme.tertiary
                                            else -> MaterialTheme.colorScheme.primary
                                        }
                                    )
                                }
                                plan.createdAt?.let {
                                    Spacer(Modifier.width(8.dp))
                                    Text(it.take(10), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                            // Progress bar
                            if (plan.getPercentProgress() > 0) {
                                Spacer(Modifier.height(6.dp))
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Box(modifier = Modifier.weight(1f).height(4.dp)) {
                                        Box(modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(2.dp)).background(MaterialTheme.colorScheme.surfaceVariant))
                                        Box(modifier = Modifier.fillMaxHeight().fillMaxWidth(fraction = plan.getPercentProgress() / 100f).clip(RoundedCornerShape(2.dp)).background(MaterialTheme.colorScheme.primary))
                                    }
                                    Spacer(Modifier.width(8.dp))
                                    Text("${plan.getPercentProgress()}%", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                                }
                            }
                        }
                        Box {
                            IconButton(onClick = { showMenu = true }) {
                                Icon(Icons.Default.MoreVert, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            DropdownMenu(expanded = showMenu, onDismissRequest = { showMenu = false }) {
                                DropdownMenuItem(
                                    text = { Text("删除") },
                                    onClick = { showMenu = false; viewModel.deletePlan(plan.id) },
                                    leadingIcon = { Icon(Icons.Default.Delete, null) }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
