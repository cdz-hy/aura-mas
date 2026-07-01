package com.aura.mas.ui.components.resource

import androidx.compose.animation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aura.mas.data.model.LearningResource
import com.aura.mas.ui.theme.*
import com.google.gson.Gson
import com.google.gson.JsonObject

@Composable
fun ResourceViewer(
    resource: LearningResource,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.fillMaxSize()) {
        // Resource type badge
        Surface(
            shape = RoundedCornerShape(20.dp),
            color = MaterialTheme.colorScheme.primaryContainer
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    getResourceIcon(resource.getResourceType()),
                    null,
                    modifier = Modifier.size(14.dp),
                    tint = MaterialTheme.colorScheme.onPrimaryContainer
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    getResourceTypeName(resource.getResourceType()),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
        }

        Spacer(Modifier.height(16.dp))

        // Title
        Text(
            resource.getResourceTitle().ifEmpty { resource.getModuleName() },
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold
        )

        Spacer(Modifier.height(16.dp))

        // Content based on type
        val content = resource.getContent()
        when (resource.getResourceType()) {
            "document", "reading", "summary" -> DocumentContent(content)
            "code" -> CodeContent(content)
            "quiz" -> QuizContent(content)
            "mindmap" -> MindmapContent(content)
            "video" -> VideoContent(content)
            "podcast" -> PodcastContent(content)
            "pptx" -> PptxContent(content)
            "animation" -> AnimationContent(content)
            else -> DocumentContent(content)
        }
    }
}

@Composable
private fun DocumentContent(content: String) {
    val parsed = parseContent(content)
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState())
    ) {
        // Tag
        Surface(
            shape = RoundedCornerShape(20.dp),
            color = MaterialTheme.colorScheme.surfaceVariant
        ) {
            Text(
                "阅读文档",
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Spacer(Modifier.height(12.dp))

        // Markdown content
        if (parsed.isNotBlank()) {
            MarkdownRenderer(
                content = parsed,
                modifier = Modifier.fillMaxWidth()
            )
        } else {
            Text(
                "暂无内容",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun CodeContent(content: String) {
    val parsed = parseContent(content)
    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        Surface(
            shape = RoundedCornerShape(20.dp),
            color = MaterialTheme.colorScheme.tertiaryContainer
        ) {
            Text(
                "代码示例",
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onTertiaryContainer
            )
        }
        Spacer(Modifier.height(12.dp))

        // Code block
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = MaterialTheme.colorScheme.inverseSurface,
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    parsed,
                    style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace),
                    color = MaterialTheme.colorScheme.inverseOnSurface
                )
            }
        }
    }
}

@Composable
private fun QuizContent(content: String) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
    ) {
        Column(Modifier.padding(20.dp)) {
            Icon(Icons.Filled.Quiz, null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(32.dp))
            Spacer(Modifier.height(12.dp))
            Text("测验资源", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text("点击开始答题", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.7f))
        }
    }
}

@Composable
private fun MindmapContent(content: String) {
    val parsed = parseJsonObject(content)
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer)
    ) {
        Column(Modifier.padding(20.dp)) {
            Icon(Icons.Filled.Folder, null, tint = MaterialTheme.colorScheme.tertiary, modifier = Modifier.size(32.dp))
            Spacer(Modifier.height(12.dp))
            Text("思维导图", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(8.dp))
            // Render tree structure
            if (parsed != null) {
                MindmapTree(parsed, depth = 0)
            } else if (content.isNotBlank()) {
                MarkdownRenderer(content)
            } else {
                Text("暂无内容", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onTertiaryContainer.copy(alpha = 0.7f))
            }
        }
    }
}

@Composable
private fun MindmapTree(json: JsonObject, depth: Int) {
    val title = json.get("title")?.asString ?: json.get("label")?.asString ?: json.get("name")?.asString ?: ""
    if (title.isNotBlank()) {
        Row(modifier = Modifier.padding(start = (depth * 16).dp, top = 2.dp, bottom = 2.dp)) {
            if (depth > 0) {
                Text("├─ ", style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace), color = MaterialTheme.colorScheme.onTertiaryContainer.copy(alpha = 0.5f))
            }
            Text(
                title,
                style = if (depth == 0) MaterialTheme.typography.titleSmall else MaterialTheme.typography.bodySmall,
                fontWeight = if (depth == 0) FontWeight.SemiBold else FontWeight.Normal,
                color = MaterialTheme.colorScheme.onTertiaryContainer
            )
        }
    }
    val children = json.getAsJsonArray("children") ?: json.getAsJsonArray("nodes") ?: json.getAsJsonArray("items")
    children?.forEach { child ->
        if (child.isJsonObject) {
            MindmapTree(child.asJsonObject, depth + 1)
        }
    }
}

@Composable
private fun VideoContent(content: String) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier.size(80.dp),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Filled.PlayCircle,
                    null,
                    modifier = Modifier.size(64.dp),
                    tint = MaterialTheme.colorScheme.primary
                )
            }
            Spacer(Modifier.height(12.dp))
            Text("视频资源", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text("点击播放视频内容", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(12.dp))
            Button(onClick = { /* TODO: Open video player */ }, shape = RoundedCornerShape(12.dp)) {
                Icon(Icons.Default.PlayArrow, null)
                Spacer(Modifier.width(8.dp))
                Text("播放视频")
            }
        }
    }
}

@Composable
private fun PodcastContent(content: String) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(Icons.Filled.Headphones, null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(12.dp))
            Text("播客音频", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(8.dp))
            // Audio controls
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = { }) {
                    Icon(Icons.Default.SkipPrevious, null)
                }
                FilledIconButton(onClick = { }, modifier = Modifier.size(56.dp)) {
                    Icon(Icons.Default.PlayArrow, null, modifier = Modifier.size(32.dp))
                }
                IconButton(onClick = { }) {
                    Icon(Icons.Default.SkipNext, null)
                }
            }
            Spacer(Modifier.height(8.dp))
            LinearProgressIndicator(progress = { 0.3f }, modifier = Modifier.fillMaxWidth())
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("5:23", style = MaterialTheme.typography.labelSmall)
                Text("15:47", style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@Composable
private fun PptxContent(content: String) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(Icons.Filled.Slideshow, null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(12.dp))
            Text("演示文稿", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text("点击查看 PPT 内容", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(12.dp))
            // Render slides as cards
            val parsed = parseJsonObject(content)
            if (parsed != null) {
                val slides = parsed.getAsJsonArray("slides")
                slides?.forEachIndexed { index, slide ->
                    if (slide.isJsonObject) {
                        SlidePreviewCard(slide.asJsonObject, index + 1)
                        Spacer(Modifier.height(8.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun SlidePreviewCard(slide: JsonObject, index: Int) {
    Card(
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(Modifier.padding(12.dp)) {
            Text("幻灯片 $index", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(4.dp))
            val title = slide.get("title")?.asString
            if (title != null) {
                Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            }
            val body = slide.get("content")?.asString ?: slide.get("body")?.asString
            if (body != null) {
                Spacer(Modifier.height(4.dp))
                Text(body, style = MaterialTheme.typography.bodySmall, maxLines = 3, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun AnimationContent(content: String) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(Icons.Filled.Animation, null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(12.dp))
            Text("动画资源", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text("交互式动画内容", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

private fun parseContent(content: String): String {
    return try {
        val json = Gson().fromJson(content, JsonObject::class.java)
        json.get("content")?.asString ?: json.get("text")?.asString ?: json.get("markdown")?.asString ?: content
    } catch (e: Exception) {
        content
    }
}

private fun parseJsonObject(content: String): JsonObject? {
    return try {
        Gson().fromJson(content, JsonObject::class.java)
    } catch (e: Exception) {
        null
    }
}

private fun getResourceIcon(type: String) = when (type) {
    "document", "reading" -> Icons.Filled.Description
    "summary" -> Icons.Filled.Summarize
    "mindmap" -> Icons.Filled.Folder
    "quiz" -> Icons.Filled.Quiz
    "code" -> Icons.Filled.Code
    "video" -> Icons.Filled.PlayCircle
    "podcast" -> Icons.Filled.Headphones
    "pptx" -> Icons.Filled.Slideshow
    "animation" -> Icons.Filled.Animation
    else -> Icons.Filled.Article
}

private fun getResourceTypeName(type: String) = when (type) {
    "document" -> "文档"
    "reading" -> "阅读材料"
    "summary" -> "摘要"
    "mindmap" -> "思维导图"
    "quiz" -> "测验"
    "code" -> "代码"
    "video" -> "视频"
    "podcast" -> "播客"
    "pptx" -> "演示文稿"
    "animation" -> "动画"
    else -> "资源"
}
