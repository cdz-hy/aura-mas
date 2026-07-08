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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
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
    val isRefreshing: Boolean = false,
    val isCreating: Boolean = false,
    val plans: List<LearningPlan> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class PlanListViewModel @Inject constructor(
    private val planRepo: PlanRepository,
    private val api: ApiService,
    private val pythonApi: com.aura.mas.data.api.PythonApiService,
    private val authStore: com.aura.mas.data.repository.AuthStore,
    private val offlineCache: com.aura.mas.data.offline.OfflineCacheManager,
    private val networkUtil: com.aura.mas.util.NetworkUtil
) : ViewModel() {
    private val _uiState = MutableStateFlow(PlanListUiState())
    val uiState: StateFlow<PlanListUiState> = _uiState.asStateFlow()

    init { loadPlans() }

    fun loadPlans() {
        viewModelScope.launch {
            // Step 1: Show cached data immediately
            val cached = offlineCache.getCachedPlans().sortedByDescending { it.id }
            if (cached.isNotEmpty()) {
                _uiState.value = PlanListUiState(plans = cached, isLoading = false, isRefreshing = true)
            } else {
                _uiState.value = PlanListUiState(isLoading = true)
            }

            // Step 2: Fetch plan list only (1 API call, no per-plan calls)
            try {
                val result = kotlinx.coroutines.withTimeout(15_000L) { api.getPlans(size = 50) }
                if (result.isSuccess && result.data != null) {
                    val plans = result.data.records.sortedByDescending { it.id }
                    offlineCache.cachePlans(plans)
                    // Show plans immediately without progress
                    _uiState.value = _uiState.value.copy(plans = plans, isRefreshing = true, isLoading = false)

                    // Step 3: Load progress asynchronously per plan (background)
                    loadProgressForPlans(plans)
                } else {
                    _uiState.value = _uiState.value.copy(isRefreshing = false)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isRefreshing = false, isLoading = false)
            }
        }
    }

    private fun loadProgressForPlans(plans: List<LearningPlan>) {
        viewModelScope.launch {
            try {
                val planIds = plans.map { it.id }
                val progressResult = api.getBatchProgress(planIds)
                val progressMap = progressResult.data ?: emptyMap()
                val updatedPlans = plans.map { plan ->
                    val summary = progressMap[plan.id.toString()]
                    plan.copy(progress = summary?.progress?.toDouble() ?: 0.0)
                }
                _uiState.value = _uiState.value.copy(plans = updatedPlans, isRefreshing = false)
            } catch (_: Exception) {
                _uiState.value = _uiState.value.copy(isRefreshing = false)
            }
        }
    }

    fun deletePlan(planId: Long) {
        if (!networkUtil.isOnline()) {
            _uiState.value = _uiState.value.copy(error = "离线状态，无法删除")
            return
        }
        viewModelScope.launch {
            val result = api.deletePlan(planId)
            if (result.isSuccess) {
                _uiState.value = _uiState.value.copy(
                    plans = _uiState.value.plans.filterNot { it.id == planId }
                )
            } else {
                _uiState.value = _uiState.value.copy(error = result.message.ifEmpty { "删除失败" })
            }
        }
    }

    fun markAllComplete(planId: Long) {
        if (!networkUtil.isOnline()) {
            _uiState.value = _uiState.value.copy(error = "离线状态，无法操作")
            return
        }
        viewModelScope.launch {
            try {
                val result = api.markAllComplete(planId)
                if (result.isSuccess) {
                    // Reload plans to get updated status
                    loadPlans()
                } else {
                    _uiState.value = _uiState.value.copy(error = result.message.ifEmpty { "操作失败" })
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message ?: "操作失败")
            }
        }
    }

    fun updatePlanTitle(plan: LearningPlan, title: String) {
        if (!networkUtil.isOnline()) {
            _uiState.value = _uiState.value.copy(error = "离线状态，无法修改")
            return
        }
        val newTitle = title.trim().ifBlank { "未命名计划" }
        viewModelScope.launch {
            try {
                val updated = plan.copy(title = newTitle)
                val result = api.updatePlan(plan.id, updated)
                if (result.isSuccess) {
                    _uiState.value = _uiState.value.copy(
                        plans = _uiState.value.plans.map { if (it.id == plan.id) updated else it }
                    )
                    // Async: generate AI plan icon based on new title
                    regeneratePlanIcon(plan.id, newTitle)
                } else {
                    _uiState.value = _uiState.value.copy(error = result.message.ifEmpty { "更新失败" })
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message ?: "更新失败")
            }
        }
    }

    private suspend fun regeneratePlanIcon(planId: Long, planTitle: String) {
        try {
            // Get resource titles for icon context
            val resources = api.getResourcesByPlan(planId)
            val resourceTitles = resources.data?.mapNotNull { res ->
                try {
                    val md = res.moduleData
                    if (md == null || md.toString().isBlank()) return@mapNotNull res.title
                    val mdStr = if (md is String) md else md.toString()
                    val json = com.google.gson.Gson().fromJson(mdStr, com.google.gson.JsonObject::class.java)
                    json?.get("title")?.asString ?: res.title
                } catch (_: Exception) { res.title }
            }?.filter { it.isNotBlank() } ?: emptyList()

            val ticketResp = api.issueTicket()
            val ticket = ticketResp.data?.get("ticket") ?: return
            val requestMap = mapOf(
                "plan_id" to planId,
                "plan_title" to planTitle,
                "resource_titles" to resourceTitles
            )
            val response = pythonApi.generatePlanIcon(requestMap, ticket)
            val json = com.google.gson.Gson().fromJson(response.string(), com.google.gson.JsonObject::class.java)
            val svg = json?.get("svg")?.asString
            if (!svg.isNullOrBlank()) {
                // Update local plan with new icon
                val currentPlans = _uiState.value.plans.toMutableList()
                val idx = currentPlans.indexOfFirst { it.id == planId }
                if (idx >= 0) {
                    val oldPlan = currentPlans[idx]
                    val configMap = try {
                        if (oldPlan.planConfig.isNullOrBlank()) mutableMapOf()
                        else com.google.gson.Gson().fromJson(oldPlan.planConfig, com.google.gson.JsonObject::class.java).let { obj ->
                            val map = mutableMapOf<String, Any>()
                            obj.entrySet().forEach { (k, v) -> map[k] = v }
                            map
                        }
                    } catch (_: Exception) { mutableMapOf<String, Any>() }
                    configMap["iconSvg"] = svg
                    json?.get("description")?.asString?.let { configMap["iconDescription"] = it }
                    val newConfig = com.google.gson.Gson().toJson(configMap)
                    currentPlans[idx] = oldPlan.copy(planConfig = newConfig)
                    _uiState.value = _uiState.value.copy(plans = currentPlans)
                    // Persist to backend
                    api.updatePlan(planId, currentPlans[idx])
                }
            }
        } catch (_: Exception) {}
    }

    fun createNewPlan(onSuccess: (Long) -> Unit) {
        if (!networkUtil.isOnline()) {
            _uiState.value = _uiState.value.copy(error = "离线状态，无法创建")
            return
        }
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isCreating = true)
            try {
                val learningGoalJson = com.google.gson.Gson().toJson(mapOf("raw" to ""))
                val result = planRepo.createPlan(PlanCreateRequest(
                    title = "新学习计划",
                    learningGoal = learningGoalJson,
                    planConfig = "{}"
                ))
                if (result.isSuccess && result.data != null) {
                    onSuccess(result.data.id)
                } else {
                    _uiState.value = _uiState.value.copy(error = result.message.ifEmpty { "创建失败" }, isCreating = false)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message ?: "网络错误", isCreating = false)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlanListScreen(
    onPlanClick: (Long) -> Unit,
    onCreatePlan: () -> Unit, // keeping signature but we won't use it directly
    viewModel: PlanListViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.loadPlans()
    }

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
                onClick = { 
                    if (!uiState.isCreating) {
                        viewModel.createNewPlan(onSuccess = onPlanClick)
                    }
                },
                icon = { 
                    if (uiState.isCreating) {
                        CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                    } else {
                        Icon(Icons.Default.Add, null) 
                    }
                },
                text = { Text(if (uiState.isCreating) "创建中..." else "创建计划") },
                shape = RoundedCornerShape(16.dp)
            )
        }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            if (uiState.isRefreshing) {
                LinearProgressIndicator(
                    modifier = Modifier.fillMaxWidth().height(2.dp),
                    trackColor = Color.Transparent
                )
            }
            Box(Modifier.fillMaxSize()) {
                when {
                    uiState.isLoading -> {
                        LoadingIndicator()
                    }
                    uiState.error != null -> {
                        ErrorState(
                            message = uiState.error ?: "未知错误",
                            onRetry = { viewModel.loadPlans() }
                        )
                    }
                    uiState.plans.isEmpty() -> {
                        EmptyState(
                            Icons.Outlined.MenuBook,
                            "暂无学习计划",
                            "点击右下角按钮创建你的第一个学习计划"
                        )
                    }
                    else -> {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(uiState.plans, key = { it.id }) { plan ->
                var showMenu by remember { mutableStateOf(false) }
                var showDeleteConfirm by remember { mutableStateOf(false) }
                var showCompleteConfirm by remember { mutableStateOf(false) }
                var isEditingTitle by remember { mutableStateOf(false) }
                var editingTitle by remember(plan.id, plan.title) { mutableStateOf(plan.title) }
                val focusRequester = remember { FocusRequester() }
                val focusManager = LocalFocusManager.current

                if (showDeleteConfirm) {
                    AlertDialog(
                        onDismissRequest = { showDeleteConfirm = false },
                        title = { Text("删除学习计划") },
                        text = { Text("确定要删除学习计划「${plan.title.ifBlank { "未命名计划" }}」吗？该计划下的所有对话、资源和测验记录将一并删除，此操作不可恢复。") },
                        confirmButton = {
                            TextButton(
                                onClick = {
                                    showDeleteConfirm = false
                                    viewModel.deletePlan(plan.id)
                                }
                            ) { Text("确认删除", color = MaterialTheme.colorScheme.error) }
                        },
                        dismissButton = {
                            TextButton(onClick = { showDeleteConfirm = false }) { Text("取消") }
                        }
                    )
                }

                if (showCompleteConfirm) {
                    AlertDialog(
                        onDismissRequest = { showCompleteConfirm = false },
                        title = { Text("标记为已完成") },
                        text = { Text("确定要将学习计划「${plan.title.ifBlank { "未命名计划" }}」标记为已完成吗？这会将该计划下所有已生成的学习资源均标记为已完成。") },
                        confirmButton = {
                            TextButton(onClick = {
                                showCompleteConfirm = false
                                viewModel.markAllComplete(plan.id)
                            }) { Text("确认完成", color = MaterialTheme.colorScheme.primary) }
                        },
                        dismissButton = {
                            TextButton(onClick = { showCompleteConfirm = false }) { Text("取消") }
                        }
                    )
                }

                LaunchedEffect(isEditingTitle) {
                    if (isEditingTitle) focusRequester.requestFocus()
                }

                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable(enabled = !isEditingTitle) { onPlanClick(plan.id) },
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Plan icon - completed shows checkmark, prefer SVG, fall back to book icon
                        val iconSvg = plan.getIconSvg()
                        val isCompleted = plan.getEffectiveStatus() == LearningPlan.STATUS_COMPLETED
                        Box(
                            modifier = Modifier
                                .size(44.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(if (isCompleted) Emerald50 else MaterialTheme.colorScheme.primaryContainer),
                            contentAlignment = Alignment.Center
                        ) {
                            if (isCompleted && iconSvg.isNullOrBlank()) {
                                Icon(
                                    Icons.Default.CheckCircle,
                                    null,
                                    tint = Emerald500,
                                    modifier = Modifier.size(24.dp)
                                )
                            } else if (!iconSvg.isNullOrBlank()) {
                                SvgIcon(svgString = iconSvg, modifier = Modifier.size(24.dp))
                            } else {
                                Icon(
                                    Icons.Default.MenuBook,
                                    null,
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(24.dp)
                                )
                            }
                        }
                        Spacer(Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            if (isEditingTitle) {
                                OutlinedTextField(
                                    value = editingTitle,
                                    onValueChange = { editingTitle = it },
                                    singleLine = true,
                                    textStyle = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .focusRequester(focusRequester),
                                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(imeAction = ImeAction.Done),
                                    keyboardActions = androidx.compose.foundation.text.KeyboardActions(
                                        onDone = {
                                            focusManager.clearFocus()
                                            isEditingTitle = false
                                            viewModel.updatePlanTitle(plan, editingTitle)
                                        }
                                    ),
                                    trailingIcon = {
                                        Row {
                                            IconButton(
                                                onClick = {
                                                    focusManager.clearFocus()
                                                    isEditingTitle = false
                                                    viewModel.updatePlanTitle(plan, editingTitle)
                                                },
                                                modifier = Modifier.size(32.dp)
                                            ) { Icon(Icons.Default.Check, null, modifier = Modifier.size(18.dp)) }
                                            IconButton(
                                                onClick = {
                                                    focusManager.clearFocus()
                                                    editingTitle = plan.title
                                                    isEditingTitle = false
                                                },
                                                modifier = Modifier.size(32.dp)
                                            ) { Icon(Icons.Default.Close, null, modifier = Modifier.size(18.dp)) }
                                        }
                                    }
                                )
                            } else {
                                Text(
                                    plan.title.ifBlank { "未命名计划" },
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.SemiBold,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                            Spacer(Modifier.height(4.dp))
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                // Status chip
                                val chipColor = when (plan.getEffectiveStatus()) {
                                    LearningPlan.STATUS_COMPLETED -> Emerald700
                                    LearningPlan.STATUS_GENERATING -> Amber700
                                    LearningPlan.STATUS_CONFIRMING -> Sky700
                                    LearningPlan.STATUS_LEARNING -> Teal700
                                    else -> Gray500
                                }
                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = chipColor.copy(alpha = 0.12f)
                                ) {
                                    Text(
                                        plan.getStatusText(),
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                                        style = MaterialTheme.typography.labelSmall,
                                        color = chipColor
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
                                if (plan.getEffectiveStatus() != LearningPlan.STATUS_COMPLETED) {
                                    DropdownMenuItem(
                                        text = { Text("标记为已完成") },
                                        onClick = {
                                            showMenu = false
                                            showCompleteConfirm = true
                                        },
                                        leadingIcon = { Icon(Icons.Default.CheckCircle, null) }
                                    )
                                }
                                DropdownMenuItem(
                                    text = { Text("编辑") },
                                    onClick = {
                                        showMenu = false
                                        editingTitle = plan.title
                                        isEditingTitle = true
                                    },
                                    leadingIcon = { Icon(Icons.Default.Edit, null) }
                                )
                                DropdownMenuItem(
                                    text = { Text("删除") },
                                    onClick = {
                                        showMenu = false
                                        showDeleteConfirm = true
                                    },
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
    }
}
    }
}
