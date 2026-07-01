package com.aura.mas.ui.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.aura.mas.data.model.ProfileDimensions
import com.aura.mas.ui.components.charts.RadarChart
import com.aura.mas.ui.components.charts.RadarData
import kotlin.math.abs
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LearningProfileScreen(
    onNavigateBack: () -> Unit,
    viewModel: ProfileViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    
    // Automatically load profile if it's missing (though it might already be loaded by ProfileScreen)
    LaunchedEffect(Unit) {
        if (uiState.profile == null && !uiState.isLoading) {
            viewModel.loadProfile()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("我的学习画像", fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface
                )
            )
        }
    ) { paddingValues ->
        if (uiState.isLoading) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else if (uiState.error != null) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text(text = "加载失败: ${uiState.error}", color = MaterialTheme.colorScheme.error)
            }
        } else {
            val dimensions = uiState.profile?.learningBehavior
            if (dimensions != null) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues)
                        .verticalScroll(rememberScrollState())
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    RadarChartCard(dimensions)
                    FelderSilvermanDetailsCard(dimensions)
                    AuxiliaryDimensionsCard(dimensions)
                    
                    Spacer(modifier = Modifier.height(32.dp))
                }
            } else {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("暂无画像数据", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
private fun RadarChartCard(dims: ProfileDimensions) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(Modifier.padding(20.dp)) {
            Text("Felder-Silverman 学习风格", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(16.dp))
            RadarChart(
                data = listOf(
                    RadarData("感知 ↔ 直觉", ((dims.sensingIntuitive + 1) / 2).toFloat()),
                    RadarData("视觉 ↔ 言语", ((dims.visualVerbal + 1) / 2).toFloat()),
                    RadarData("活跃 ↔ 沉思", ((dims.activeReflective + 1) / 2).toFloat()),
                    RadarData("循序 ↔ 全局", ((dims.sequentialGlobal + 1) / 2).toFloat())
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(240.dp)
            )
        }
    }
}

@Composable
private fun FelderSilvermanDetailsCard(dims: ProfileDimensions) {
    val axes = listOf(
        AxisDef("感知-直觉", "感知型", "直觉型", dims.sensingIntuitive),
        AxisDef("视觉-言语", "视觉型", "言语型", dims.visualVerbal),
        AxisDef("活跃-沉思", "活跃型", "沉思型", dims.activeReflective),
        AxisDef("循序-全局", "循序型", "全局型", dims.sequentialGlobal)
    )

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(Modifier.padding(20.dp)) {
            Text("学习风格维度", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(20.dp))
            
            axes.forEachIndexed { index, axis ->
                DimensionBar(axis)
                if (index < axes.size - 1) {
                    Spacer(Modifier.height(16.dp))
                }
            }
        }
    }
}

private data class AxisDef(val title: String, val negLabel: String, val posLabel: String, val value: Double)

@Composable
private fun DimensionBar(axis: AxisDef) {
    val normalizedValue = axis.value // assuming range [-1, 1], adjust if it's [0, 1] mapped to [-1, 1]
    
    // For visual representation, we assume value is between -1.0 and 1.0. 
    // If it's 0 to 1, then mappedValue = (value - 0.5) * 2
    // Wait, the python backend often uses -1 to 1 for these dimensions. Let's assume -1 to 1 based on Vue logic.
    // If the data is actually 0 to 1, we can adjust here. Let's just use it as -1 to 1.
    val isPositive = normalizedValue >= 0
    val absValue = abs(normalizedValue)
    
    // Vue uses thresholds >= 0.2, etc.
    val tagText = when {
        normalizedValue <= -0.2 -> axis.negLabel
        normalizedValue >= 0.2 -> axis.posLabel
        else -> "相对均衡"
    }
    
    val tagBgColor = if (absValue >= 0.2) Color(0xFFE2E8F0) else Color(0xFFF1F5F9)
    val tagTextColor = if (absValue >= 0.2) Color(0xFF334155) else Color(0xFF64748B)

    Column {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text(axis.title, fontSize = 14.sp, fontWeight = FontWeight.Medium, color = MaterialTheme.colorScheme.onSurface)
            Surface(color = tagBgColor, shape = RoundedCornerShape(12.dp)) {
                Text(
                    text = tagText,
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                    fontSize = 11.sp,
                    color = tagTextColor
                )
            }
        }
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(axis.negLabel, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.width(42.dp))
            
            // The Bar
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(8.dp)
                    .clip(CircleShape)
                    .background(Color(0xFFF1F5F9))
            ) {
                // Center line
                Box(
                    modifier = Modifier
                        .align(Alignment.Center)
                        .width(2.dp)
                        .fillMaxHeight()
                        .background(Color(0xFFCBD5E1).copy(alpha = 0.5f))
                )
                
                // Active bar
                val widthFraction = (absValue / 1.0).toFloat().coerceIn(0.001f, 1f) * 0.5f
                val color = if (isPositive) Color(0xFF60A5FA) else Color(0xFFFBBF24)
                
                Row(modifier = Modifier.fillMaxSize()) {
                    if (!isPositive) {
                        Spacer(Modifier.weight((0.5f - widthFraction).coerceAtLeast(0.001f)))
                        Box(Modifier.weight(widthFraction).fillMaxHeight().background(color))
                        Spacer(Modifier.weight(0.5f))
                    } else {
                        Spacer(Modifier.weight(0.5f))
                        Box(Modifier.weight(widthFraction).fillMaxHeight().background(color))
                        Spacer(Modifier.weight((0.5f - widthFraction).coerceAtLeast(0.001f)))
                    }
                }
            }
            
            Text(axis.posLabel, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.width(42.dp))
        }
    }
}

@Composable
private fun AuxiliaryDimensionsCard(dims: ProfileDimensions) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(Modifier.padding(20.dp)) {
            Text("辅助维度", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(16.dp))
            
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                // We show two per row if possible, or just a column. A column of cards is simpler.
                val kbStr = dims.knowledgeBase.joinToString("、")
                AuxiliaryItem("知识基础", dims.knowledgeBase.isNotEmpty(), if (kbStr.isNotEmpty()) kbStr else null)
                val itStr = dims.interestTags.joinToString("、")
                AuxiliaryItem("兴趣标签", dims.interestTags.isNotEmpty(), if (itStr.isNotEmpty()) itStr else null)
                
                val goalStr = when(dims.goalOrientation) {
                    "exam" -> "应试通关"
                    "interview" -> "求职面试"
                    "work" -> "工作实战"
                    "interest" -> "兴趣拓展"
                    "research" -> "学术研究"
                    else -> null
                }
                AuxiliaryItem("目标导向", !goalStr.isNullOrEmpty(), goalStr)
                
                val waStr = dims.weakAreas.joinToString("、")
                AuxiliaryItem("薄弱环节", dims.weakAreas.isNotEmpty(), if (waStr.isNotEmpty()) waStr else null)
                val prStr = dims.preferredResourceTypes.joinToString("、")
                AuxiliaryItem("偏好资源", dims.preferredResourceTypes.isNotEmpty(), if (prStr.isNotEmpty()) prStr else null)
                
                val qPref = dims.preferredQuizPreference
                val qPrefStr = if (qPref != null && (qPref.types.isNotEmpty() || qPref.count != null || qPref.difficulty.isNotEmpty())) {
                    val t = if (qPref.types.isNotEmpty()) qPref.types.joinToString("、") else ""
                    val c = if (qPref.count != null) "${qPref.count}题" else ""
                    val d = if (qPref.difficulty.isNotEmpty()) qPref.difficulty else ""
                    listOf(t, c, d).filter { it.isNotEmpty() }.joinToString(" | ")
                } else null
                
                AuxiliaryItem("偏好题目配置", qPrefStr != null, qPrefStr)
            }
        }
    }
}

@Composable
private fun AuxiliaryItem(title: String, isFilled: Boolean, content: String?) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFF1F5F9), RoundedCornerShape(12.dp))
            .background(Color(0xFFF8FAFC), RoundedCornerShape(12.dp))
            .padding(12.dp)
    ) {
        Column {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text(title, fontSize = 14.sp, fontWeight = FontWeight.Medium, color = Color(0xFF334155))
                Surface(
                    color = if (isFilled) Color(0xFFDCFCE7) else Color(0xFFF1F5F9),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text(
                        text = if (isFilled) "已完善" else "待完善",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                        fontSize = 11.sp,
                        color = if (isFilled) Color(0xFF166534) else Color(0xFF64748B)
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(
                text = content ?: "暂未收集",
                fontSize = 12.sp,
                color = if (content != null) Color(0xFF475569) else Color(0xFF94A3B8),
                lineHeight = 18.sp
            )
        }
    }
}
