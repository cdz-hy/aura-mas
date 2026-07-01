package com.aura.mas.ui.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.aura.mas.ui.common.TopAppBar
import com.aura.mas.ui.theme.AppTheme
import com.aura.mas.ui.theme.ThemeManager
import javax.inject.Inject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBack: () -> Unit,
    onLogout: () -> Unit,
    viewModel: ProfileViewModel = hiltViewModel()
) {
    var showLogoutDialog by remember { mutableStateOf(false) }
    var showThemeDialog by remember { mutableStateOf(false) }
    var showAboutDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = { TopAppBar("设置", onBack = onBack) }
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            Card(shape = RoundedCornerShape(16.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column {
                    SettingsItem(Icons.Default.Person, "个人信息", "编辑昵称、邮箱") { }
                    HorizontalDivider(Modifier.padding(horizontal = 16.dp))
                    SettingsItem(Icons.Default.Security, "账号安全", "修改密码") { }
                    HorizontalDivider(Modifier.padding(horizontal = 16.dp))
                    SettingsItem(Icons.Default.Notifications, "通知设置", "闪卡复习提醒") { }
                    HorizontalDivider(Modifier.padding(horizontal = 16.dp))
                    SettingsItem(Icons.Default.Palette, "主题设置", "切换界面主题") { showThemeDialog = true }
                    HorizontalDivider(Modifier.padding(horizontal = 16.dp))
                    SettingsItem(Icons.Default.Language, "语言设置", "简体中文") { }
                }
            }

            Spacer(Modifier.height(16.dp))

            Card(shape = RoundedCornerShape(16.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column {
                    SettingsItem(Icons.Default.Info, "关于", "AURA MAS v1.0.0") { showAboutDialog = true }
                    HorizontalDivider(Modifier.padding(horizontal = 16.dp))
                    SettingsItem(Icons.Default.PrivacyTip, "隐私政策", "") { }
                    HorizontalDivider(Modifier.padding(horizontal = 16.dp))
                    SettingsItem(Icons.Default.Description, "用户协议", "") { }
                }
            }

            Spacer(Modifier.height(24.dp))

            OutlinedButton(
                onClick = { showLogoutDialog = true },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
            ) {
                Icon(Icons.Default.Logout, null)
                Spacer(Modifier.width(8.dp))
                Text("退出登录")
            }
        }
    }

    if (showLogoutDialog) {
        AlertDialog(
            onDismissRequest = { showLogoutDialog = false },
            title = { Text("退出登录") },
            text = { Text("确定要退出登录吗？") },
            confirmButton = {
                TextButton(onClick = { showLogoutDialog = false; viewModel.logout(onLogout) }) {
                    Text("确定", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = { TextButton(onClick = { showLogoutDialog = false }) { Text("取消") } }
        )
    }

    if (showThemeDialog) {
        ThemeSelectionDialog(onDismiss = { showThemeDialog = false })
    }

    if (showAboutDialog) {
        AlertDialog(
            onDismissRequest = { showAboutDialog = false },
            title = { Text("关于 AURA MAS") },
            text = {
                Column {
                    Text("AURA MAS - 智能自适应学习平台", fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(8.dp))
                    Text("版本: 1.0.0", style = MaterialTheme.typography.bodySmall)
                    Text("基于 AI 的个性化学习系统", style = MaterialTheme.typography.bodySmall)
                    Spacer(Modifier.height(8.dp))
                    Text("支持功能:", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
                    Text("• AI 对话式学习计划创建", style = MaterialTheme.typography.bodySmall)
                    Text("• 多类型资源学习 (文档/视频/播客/测验/闪卡)", style = MaterialTheme.typography.bodySmall)
                    Text("• 知识树 & 知识图谱", style = MaterialTheme.typography.bodySmall)
                    Text("• 学习分析 & 进度追踪", style = MaterialTheme.typography.bodySmall)
                    Text("• 离线阅读 & 桌面小组件", style = MaterialTheme.typography.bodySmall)
                }
            },
            confirmButton = { TextButton(onClick = { showAboutDialog = false }) { Text("确定") } }
        )
    }
}

@Composable
private fun ThemeSelectionDialog(onDismiss: () -> Unit) {
    val context = LocalContext.current
    val themes = listOf(
        AppTheme.LIGHT to "浅色模式",
        AppTheme.DARK to "深色模式",
        AppTheme.OCEAN to "海洋蓝",
        AppTheme.FOREST to "森林绿",
        AppTheme.SUNSET to "日落橙"
    )
    val themeColors = listOf(
        MaterialTheme.colorScheme.primary,
        androidx.compose.ui.graphics.Color(0xFF3d6090),
        androidx.compose.ui.graphics.Color(0xFF2891cc),
        androidx.compose.ui.graphics.Color(0xFF388838),
        androidx.compose.ui.graphics.Color(0xFFd86020)
    )

    // Read current theme
    val currentThemeName = remember {
        context.getSharedPreferences("aura_prefs", android.content.Context.MODE_PRIVATE)
            .getString("app_theme", AppTheme.LIGHT.name) ?: AppTheme.LIGHT.name
    }
    val currentTheme = try { AppTheme.valueOf(currentThemeName) } catch (_: Exception) { AppTheme.LIGHT }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("选择主题") },
        text = {
            Column {
                themes.forEachIndexed { index, (theme, label) ->
                    Row(
                        modifier = Modifier.fillMaxWidth().clickable {
                            // Save theme
                            context.getSharedPreferences("aura_prefs", android.content.Context.MODE_PRIVATE)
                                .edit().putString("app_theme", theme.name).apply()
                            onDismiss()
                        }.padding(vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(modifier = Modifier.size(24.dp).clip(CircleShape).background(themeColors[index]))
                        Spacer(Modifier.width(16.dp))
                        Text(label, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
                        RadioButton(selected = currentTheme == theme, onClick = {
                            context.getSharedPreferences("aura_prefs", android.content.Context.MODE_PRIVATE)
                                .edit().putString("app_theme", theme.name).apply()
                            onDismiss()
                        })
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("取消") } }
    )
}

@Composable
private fun SettingsItem(icon: ImageVector, title: String, subtitle: String, onClick: () -> Unit) {
    TextButton(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp)
    ) {
        Icon(icon, null, tint = MaterialTheme.colorScheme.onSurface)
        Spacer(Modifier.width(16.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(title, color = MaterialTheme.colorScheme.onSurface)
            if (subtitle.isNotEmpty()) {
                Text(subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Icon(Icons.Default.ChevronRight, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
