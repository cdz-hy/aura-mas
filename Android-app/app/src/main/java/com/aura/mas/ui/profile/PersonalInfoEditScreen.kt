package com.aura.mas.ui.profile

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.aura.mas.data.api.ApiService
import com.aura.mas.data.model.StudentProfile
import com.aura.mas.data.model.User
import com.aura.mas.data.repository.AuthStore
import com.aura.mas.ui.common.TopAppBar
import com.aura.mas.ui.common.UserAvatar
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject

// ── UiState ──────────────────────────────────────────────────────

data class PersonalInfoUiState(
    val isLoading: Boolean = true,
    val isSaving: Boolean = false,
    val user: User? = null,
    val profile: StudentProfile? = null,
    val error: String? = null,
    val saveSuccess: Boolean = false,
    val avatarUploading: Boolean = false
)

// ── ViewModel ────────────────────────────────────────────────────

@HiltViewModel
class PersonalInfoViewModel @Inject constructor(
    val authStore: AuthStore,
    private val api: ApiService,
    private val networkUtil: com.aura.mas.util.NetworkUtil
) : ViewModel() {
    private val _uiState = MutableStateFlow(PersonalInfoUiState())
    val uiState: StateFlow<PersonalInfoUiState> = _uiState.asStateFlow()

    init { loadData() }

    fun loadData() {
        viewModelScope.launch {
            _uiState.value = PersonalInfoUiState(isLoading = true)
            try {
                val userResult = api.getCurrentUser()
                val profileResult = api.getUserProfile()
                _uiState.value = PersonalInfoUiState(
                    isLoading = false,
                    user = userResult.data,
                    profile = profileResult.data
                )
            } catch (e: Exception) {
                _uiState.value = PersonalInfoUiState(isLoading = false, error = e.message)
            }
        }
    }

    fun saveUserInfo(nickname: String, email: String, gender: String, age: String, domain: String) {
        if (!networkUtil.isOnline()) {
            _uiState.value = _uiState.value.copy(error = "离线状态，无法保存")
            return
        }
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSaving = true, error = null, saveSuccess = false)
            try {
                val infoMap = mutableMapOf<String, String>()
                if (nickname.isNotBlank()) infoMap["nickname"] = nickname
                if (email.isNotBlank()) infoMap["email"] = email
                if (infoMap.isNotEmpty()) api.updateUserInfo(infoMap)

                val current = _uiState.value.profile
                api.updateProfile(StudentProfile(
                    userId = current?.userId ?: 0L,
                    gender = gender, age = age, domain = domain,
                    learningBehavior = current?.learningBehavior
                ))

                val userResult = api.getCurrentUser()
                val profileResult = api.getUserProfile()
                _uiState.value = _uiState.value.copy(
                    isSaving = false,
                    user = userResult.data,
                    profile = profileResult.data,
                    saveSuccess = true
                )
                userResult.data?.let { authStore.updateCurrentUser(it) }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isSaving = false, error = e.message ?: "保存失败")
            }
        }
    }

    fun uploadAvatar(uri: Uri, context: android.content.Context) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(avatarUploading = true)
            try {
                val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
                    ?: throw Exception("无法读取图片")
                val part = MultipartBody.Part.createFormData(
                    "file", "avatar.jpg",
                    bytes.toRequestBody("image/*".toMediaTypeOrNull())
                )
                api.uploadAvatar(part)
                val userResult = api.getCurrentUser()
                _uiState.value = _uiState.value.copy(avatarUploading = false, user = userResult.data)
                userResult.data?.let { authStore.updateCurrentUser(it) }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(avatarUploading = false, error = e.message ?: "上传失败")
            }
        }
    }

    fun clearAvatar() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(avatarUploading = true)
            try {
                api.clearAvatar()
                val userResult = api.getCurrentUser()
                _uiState.value = _uiState.value.copy(avatarUploading = false, user = userResult.data)
                userResult.data?.let { authStore.updateCurrentUser(it) }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(avatarUploading = false, error = e.message ?: "清除失败")
            }
        }
    }

    fun clearSaveSuccess() { _uiState.value = _uiState.value.copy(saveSuccess = false) }
}

// ── Screen ───────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PersonalInfoEditScreen(
    onBack: () -> Unit,
    viewModel: PersonalInfoViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    var nickname by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var gender by remember { mutableStateOf("") }
    var age by remember { mutableStateOf("") }
    var domain by remember { mutableStateOf("") }
    var initialized by remember { mutableStateOf(false) }
    var showClearAvatarDialog by remember { mutableStateOf(false) }

    LaunchedEffect(uiState.user, uiState.profile) {
        if (!initialized && uiState.user != null) {
            nickname = uiState.user?.nickname ?: ""
            email = uiState.user?.email ?: ""
            gender = uiState.profile?.gender ?: ""
            age = uiState.profile?.age ?: ""
            domain = uiState.profile?.domain ?: ""
            initialized = true
        }
    }

    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(uiState.saveSuccess) {
        if (uiState.saveSuccess) { snackbarHostState.showSnackbar("保存成功"); viewModel.clearSaveSuccess() }
    }
    LaunchedEffect(uiState.error) { uiState.error?.let { snackbarHostState.showSnackbar(it) } }

    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { viewModel.uploadAvatar(it, context) }
    }

    Scaffold(
        topBar = {
            TopAppBar("个人信息", onBack = onBack, actions = {
                TextButton(
                    onClick = { viewModel.saveUserInfo(nickname, email, gender, age, domain) },
                    enabled = !uiState.isSaving
                ) {
                    if (uiState.isSaving) CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                    else Text("保存", fontWeight = FontWeight.SemiBold)
                }
            })
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        containerColor = MaterialTheme.colorScheme.background
    ) { padding ->
        when {
            uiState.isLoading -> Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            else -> Column(
                Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                // ── Avatar Section ───────────────────────────
                AvatarSection(uiState, imagePicker, viewModel, showClearAvatarDialog) { showClearAvatarDialog = it }

                // ── Basic Info Form ──────────────────────────
                FormCard("基本信息") {
                    FormField("昵称", nickname, "输入昵称") { nickname = it }
                    Spacer(Modifier.height(14.dp))
                    FormField("邮箱", email, "输入邮箱") { email = it }
                }

                // ── Profile Form ─────────────────────────────
                FormCard("学习档案") {
                    GenderField(gender) { gender = it }
                    Spacer(Modifier.height(14.dp))
                    AgeField(age) { age = it }
                    Spacer(Modifier.height(14.dp))
                    FormField("学习领域", domain, "如：计算机科学、数学、物理等") { domain = it }
                }

                // ── Save Button (bottom) ─────────────────────
                Button(
                    onClick = { viewModel.saveUserInfo(nickname, email, gender, age, domain) },
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    enabled = !uiState.isSaving,
                    shape = RoundedCornerShape(12.dp)
                ) {
                    if (uiState.isSaving) {
                        CircularProgressIndicator(Modifier.size(20.dp), color = MaterialTheme.colorScheme.onPrimary, strokeWidth = 2.dp)
                    } else {
                        Icon(Icons.Default.Done, null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(8.dp))
                        Text("保存修改", fontWeight = FontWeight.SemiBold)
                    }
                }

                Spacer(Modifier.height(16.dp))
            }
        }
    }

    // Clear avatar dialog
    if (showClearAvatarDialog) {
        AlertDialog(
            onDismissRequest = { showClearAvatarDialog = false },
            title = { Text("清空头像") },
            text = { Text("确定要清空当前头像吗？") },
            confirmButton = {
                TextButton(onClick = { showClearAvatarDialog = false; viewModel.clearAvatar() }) {
                    Text("确定", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = { TextButton(onClick = { showClearAvatarDialog = false }) { Text("取消") } }
        )
    }
}

// ── Avatar Section ───────────────────────────────────────────────

@Composable
private fun AvatarSection(
    uiState: PersonalInfoUiState,
    imagePicker: androidx.activity.result.ActivityResultLauncher<String>,
    viewModel: PersonalInfoViewModel,
    showClearDialog: Boolean,
    onShowClearDialog: (Boolean) -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(
            Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("头像", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.fillMaxWidth())
            Spacer(Modifier.height(16.dp))

            // Avatar with camera badge
            Box(contentAlignment = Alignment.BottomEnd) {
                if (uiState.avatarUploading) {
                    Box(
                        Modifier.size(88.dp).clip(CircleShape).background(MaterialTheme.colorScheme.primaryContainer),
                        contentAlignment = Alignment.Center
                    ) { CircularProgressIndicator(Modifier.size(28.dp), strokeWidth = 2.5.dp) }
                } else {
                    UserAvatar(
                        avatarUrl = uiState.user?.avatarUrl,
                        nickname = uiState.user?.nickname ?: "U",
                        size = 88
                    )
                }
                Surface(
                    Modifier.size(30.dp),
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.primary,
                    shadowElevation = 2.dp
                ) {
                    IconButton(onClick = { imagePicker.launch("image/*") }, Modifier.size(30.dp)) {
                        Icon(Icons.Default.CameraAlt, null, Modifier.size(15.dp), tint = MaterialTheme.colorScheme.onPrimary)
                    }
                }
            }

            Spacer(Modifier.height(6.dp))
            Text("支持 JPG / PNG / WebP", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)

            Spacer(Modifier.height(14.dp))

            // Action buttons
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                AssistChip(
                    onClick = { imagePicker.launch("image/*") },
                    label = { Text("更换头像", fontSize = 12.sp) },
                    leadingIcon = { Icon(Icons.Default.CameraAlt, null, Modifier.size(14.dp)) },
                    shape = RoundedCornerShape(10.dp),
                    border = null,
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f)
                    )
                )
                if (!uiState.user?.avatarUrl.isNullOrBlank()) {
                    AssistChip(
                        onClick = { onShowClearDialog(true) },
                        label = { Text("清空头像", fontSize = 12.sp) },
                        leadingIcon = { Icon(Icons.Default.Delete, null, Modifier.size(14.dp)) },
                        shape = RoundedCornerShape(10.dp),
                        border = null,
                        colors = AssistChipDefaults.assistChipColors(
                            containerColor = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.4f),
                            labelColor = MaterialTheme.colorScheme.error,
                            leadingIconContentColor = MaterialTheme.colorScheme.error
                        )
                    )
                }
            }
        }
    }
}

// ── Form Card ────────────────────────────────────────────────────

@Composable
private fun FormCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(Modifier.padding(20.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface)
            Spacer(Modifier.height(16.dp))
            content()
        }
    }
}

// ── Form Field ───────────────────────────────────────────────────

@Composable
private fun FormField(label: String, value: String, placeholder: String, onValueChange: (String) -> Unit) {
    Column {
        Text(label, fontSize = 13.sp, fontWeight = FontWeight.Medium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(6.dp))
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            placeholder = { Text(placeholder, color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)) },
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(10.dp),
            singleLine = true,
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = MaterialTheme.colorScheme.primary,
                unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant,
                cursorColor = MaterialTheme.colorScheme.primary
            ),
            textStyle = MaterialTheme.typography.bodyMedium
        )
    }
}

// ── Gender Field ─────────────────────────────────────────────────

@Composable
private fun GenderField(selected: String, onSelect: (String) -> Unit) {
    Column {
        Text("性别", fontSize = 13.sp, fontWeight = FontWeight.Medium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("male" to "男", "female" to "女", "other" to "其他").forEach { (value, label) ->
                val isSelected = selected == value
                Surface(
                    modifier = Modifier.clickable { onSelect(value) },
                    shape = RoundedCornerShape(10.dp),
                    color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else Color.Transparent,
                    border = if (isSelected) null else BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                ) {
                    Text(
                        label,
                        Modifier.padding(horizontal = 20.dp, vertical = 8.dp),
                        fontSize = 13.sp,
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                        color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

// ── Age Field ────────────────────────────────────────────────────

@Composable
private fun AgeField(selected: String, onSelect: (String) -> Unit) {
    val options = listOf("18岁以下", "18-22岁", "23-30岁", "31-40岁", "40岁以上")
    Column {
        Text("年龄段", fontSize = 13.sp, fontWeight = FontWeight.Medium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            options.forEach { opt ->
                val isSelected = selected == opt
                Surface(
                    modifier = Modifier.weight(1f).clickable { onSelect(opt) },
                    shape = RoundedCornerShape(10.dp),
                    color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else Color.Transparent,
                    border = if (isSelected) null else BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                ) {
                    Text(
                        opt,
                        Modifier.padding(vertical = 8.dp).fillMaxWidth().wrapContentWidth(Alignment.CenterHorizontally),
                        fontSize = 11.sp,
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                        color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1
                    )
                }
            }
        }
    }
}
