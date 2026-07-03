package com.aura.mas.ui.components.resource

import androidx.compose.foundation.BorderStroke
import android.webkit.ConsoleMessage
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.aura.mas.data.model.LearningResource
import androidx.compose.foundation.clickable
import androidx.compose.ui.platform.LocalContext
import com.aura.mas.ui.theme.*
import com.aura.mas.util.Constants
import com.google.gson.Gson
import com.google.gson.JsonArray
import com.google.gson.JsonElement
import com.google.gson.JsonObject

/**
 * Main resource viewer - dispatches to type-specific renderers.
 * Matches Vue's PlanDetailView.vue resource type switch.
 */
@Composable
fun ResourceViewer(
    resource: LearningResource,
    onNavigateToQuiz: (Long) -> Unit,
    modifier: Modifier = Modifier
) {
    val moduleData = remember(resource.moduleData) { resource.getParsedModuleData() }

    Column(modifier = modifier.fillMaxSize()) {
        // Type badge
        Surface(shape = RoundedCornerShape(20.dp), color = MaterialTheme.colorScheme.primaryContainer) {
            Row(Modifier.padding(horizontal = 12.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(getResourceIcon(resource.moduleType), null, modifier = Modifier.size(14.dp), tint = MaterialTheme.colorScheme.onPrimaryContainer)
                Spacer(Modifier.width(6.dp))
                Text(getResourceTypeName(resource.moduleType), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onPrimaryContainer)
            }
        }
        Spacer(Modifier.height(16.dp))

        // Title
        val title = moduleData["module_title"]?.toString()
            ?: moduleData["title"]?.toString()
            ?: resource.getResourceTitle()
        if (title.isNotBlank()) {
            Text(title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(16.dp))
        }

        // Content by type (matching Vue's v-if chain)
        when (resource.moduleType) {
            "quiz" -> QuizContent(resource.id, moduleData, onNavigateToQuiz)
            "text", "document", "reading" -> MarkdownContent(moduleData)
            "code" -> CodeContent(moduleData)
            "mindmap" -> MindmapContent(moduleData)
            "video" -> VideoContent(moduleData)
            "animation" -> AnimationContent(moduleData)
            "podcast" -> PodcastContent(moduleData)
            "pptx" -> PptxContent(moduleData)
            else -> MarkdownContent(moduleData) // summary, image, diagram, etc.
        }
    }
}

// ── Quiz ──────────────────────────────────────────────────────

@Composable
private fun QuizContent(
    resourceId: Long,
    moduleData: Map<String, Any>,
    onNavigateToQuiz: (Long) -> Unit
) {
    val questions = remember(moduleData) { parseQuizQuestions(moduleData) }

    if (questions.isEmpty()) {
        EmptyContentCard("测验", Icons.Outlined.Quiz, "暂无测验题目")
        return
    }

    val latestResult = remember(moduleData) { moduleData["latestResult"] as? Map<*, *> }

    Column {
        if (latestResult != null) {
            val score = (latestResult["score"] as? Number)?.toInt() ?: 0
            val total = (latestResult["total"] as? Number)?.toInt() ?: 0
            val correct = (latestResult["correct"] as? Number)?.toInt() ?: 0

            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("答题结果报告", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSecondaryContainer)
                        Spacer(Modifier.height(4.dp))
                        Text("得分: $score / $total 分 (答对 $correct 题)", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.9f))
                    }
                    Button(
                        onClick = { onNavigateToQuiz(resourceId) },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
                    ) {
                        Icon(Icons.Default.Refresh, null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("重新测试")
                    }
                }
            }
        } else {
            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("智能测验题目已就绪", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onPrimaryContainer)
                        Spacer(Modifier.height(4.dp))
                        Text("共 ${questions.size} 题 · 支持 AI 实时判分", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f))
                    }
                    Button(
                        onClick = { onNavigateToQuiz(resourceId) },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                    ) {
                        Icon(Icons.Default.PlayArrow, null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("开始答题")
                    }
                }
            }
        }

        Text("题目列表回顾:", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(vertical = 4.dp))
        Spacer(Modifier.height(4.dp))
        Text("共 ${questions.size} 题", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(12.dp))
        questions.forEachIndexed { index, q ->
            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)
            ) {
                Column(Modifier.padding(12.dp)) {
                    // Type badge
                    Surface(shape = RoundedCornerShape(6.dp), color = MaterialTheme.colorScheme.tertiaryContainer) {
                        Text(
                            getQuestionTypeName(q["type"]?.toString() ?: "short_answer"),
                            Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onTertiaryContainer
                        )
                    }
                    Spacer(Modifier.height(8.dp))
                    Text("${index + 1}. ${q["question"] ?: q["question_text"] ?: ""}", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                    val options = q["options"] as? List<*>
                    if (options != null) {
                        Spacer(Modifier.height(4.dp))
                        options.forEachIndexed { i, opt ->
                            val label = ('A' + i)
                            Text("  $label. $opt", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }
    }
}

// ── Markdown (text/document/reading/code) ─────────────────────

@Composable
private fun MarkdownContent(moduleData: Map<String, Any>) {
    val content = extractTextContent(moduleData)
    if (content.isBlank()) {
        EmptyContentCard("文档", Icons.Outlined.Description, "暂无内容")
        return
    }
    val cleanContent = remember(content) { stripCitationSection(content) }
    MarkdownRenderer(content = cleanContent, modifier = Modifier.fillMaxWidth())
}

@Composable
private fun CodeContent(moduleData: Map<String, Any>) {
    val content = extractTextContent(moduleData)
    if (content.isBlank()) {
        EmptyContentCard("代码", Icons.Outlined.Code, "暂无代码内容")
        return
    }
    // Render as markdown (code blocks will be syntax-highlighted)
    MarkdownRenderer(content = content, modifier = Modifier.fillMaxWidth())
}

// ── Mindmap ───────────────────────────────────────────────────

@Composable
private fun MindmapContent(moduleData: Map<String, Any>) {
    val nodeData = remember(moduleData) { extractMindmapData(moduleData) }

    if (nodeData == null) {
        EmptyContentCard("思维导图", Icons.Filled.Folder, "思维导图数据加载中")
        return
    }

    val root = remember(nodeData) { normalizeMindmapRoot(nodeData, moduleData) }
    var useFallback by remember(nodeData) { mutableStateOf(false) }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("思维导图", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                if (!useFallback) {
                    TextButton(onClick = { useFallback = true }) { Text("兼容视图") }
                }
            }
            Spacer(Modifier.height(12.dp))
            if (useFallback) {
                MindmapFallback(root)
            } else {
                MindElixirWebView(
                    nodeData = nodeData,
                    onFallback = { useFallback = true },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(520.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .border(1.dp, Navy100, RoundedCornerShape(14.dp))
                )
            }
        }
    }
}

// ── Video ─────────────────────────────────────────────────────

@Composable
private fun VideoContent(moduleData: Map<String, Any>) {
    val videos = remember(moduleData) { extractVideoList(moduleData) }

    if (videos.isEmpty()) {
        EmptyContentCard("视频", Icons.Filled.PlayCircle, "暂无视频资源")
        return
    }

    val context = LocalContext.current

    Column {
        videos.forEach { video ->
            val title = video["title"]?.toString() ?: "视频"
            val url = video["url"]?.toString() ?: ""
            val embedUrl = remember(url) { getVideoEmbedUrl(url) }

            Card(
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column {
                    // Header title area (clickable to jump to app/web)
                    Column(
                        Modifier.fillMaxWidth()
                            .clickable {
                                launchVideoApp(context, url)
                            }
                            .padding(16.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                title,
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.weight(1f)
                            )
                            Icon(
                                Icons.Default.OpenInNew,
                                null,
                                modifier = Modifier.size(16.dp),
                                tint = MaterialTheme.colorScheme.primary
                            )
                        }
                    }

                    if (embedUrl != null) {
                        // Embedded video via WebView
                        AndroidView(
                            factory = { ctx ->
                                WebView(ctx).apply {
                                    applyResourceWebSettings()
                                    webChromeClient = android.webkit.WebChromeClient()
                                    webViewClient = object : android.webkit.WebViewClient() {
                                        override fun shouldOverrideUrlLoading(view: WebView?, request: android.webkit.WebResourceRequest?): Boolean {
                                            val reqUrl = request?.url?.toString() ?: ""
                                            // Handle redirection to apps if user interacts/clicks logo inside WebView
                                            if (reqUrl.startsWith("bilibili://") || reqUrl.startsWith("vnd.youtube:") || reqUrl.contains("bilibili.com/video") || reqUrl.contains("youtube.com/watch")) {
                                                try {
                                                    launchVideoApp(ctx, reqUrl)
                                                    return true
                                                } catch (_: Exception) {}
                                            }
                                            return false
                                        }
                                    }
                                    setOnTouchListener { v, event ->
                                        when (event.action) {
                                            android.view.MotionEvent.ACTION_DOWN, android.view.MotionEvent.ACTION_MOVE -> {
                                                v.parent?.requestDisallowInterceptTouchEvent(true)
                                            }
                                            android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> {
                                                v.parent?.requestDisallowInterceptTouchEvent(false)
                                            }
                                        }
                                        false
                                    }
                                }
                            },
                            update = { webView ->
                                val html = """
                                    <!DOCTYPE html>
                                    <html>
                                    <head>
                                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                    <style>
                                    body, html { margin:0; padding:0; width:100%; height:100%; overflow:hidden; background:#000; }
                                    iframe { width:100%; height:100%; border:none; }
                                    </style>
                                    </head>
                                    <body>
                                    <iframe src="$embedUrl" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
                                    </body>
                                    </html>
                                """.trimIndent()
                                val baseUrl = if (embedUrl.contains("bilibili")) {
                                    "https://www.bilibili.com"
                                } else {
                                    "https://www.youtube.com"
                                }
                                webView.loadDataWithBaseURL(baseUrl, html, "text/html", "UTF-8", null)
                            },
                            modifier = Modifier.fillMaxWidth().height(220.dp)
                        )
                    } else {
                        // Fallback banner
                        Surface(
                            modifier = Modifier.fillMaxWidth().clickable {
                                launchVideoApp(context, url)
                            },
                            color = MaterialTheme.colorScheme.surfaceVariant
                        ) {
                            Row(
                                Modifier.padding(16.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(Icons.Default.PlayCircle, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(24.dp))
                                Spacer(Modifier.width(12.dp))
                                Column {
                                    Text("外部视频资源", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                                    Text("点击跳转并在外部应用或浏览器中播放", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// ── Animation ─────────────────────────────────────────────────

@Composable
private fun AnimationContent(moduleData: Map<String, Any>) {
    // Vue: moduleData.html || moduleData.content, rendered in iframe with sandbox="allow-scripts"
    val html = moduleData["html"]?.toString()
        ?: moduleData["content"]?.toString()
        ?: moduleData["animation_html"]?.toString()
        ?: moduleData["animationHtml"]?.toString()
        ?: ""

    if (html.isBlank()) {
        EmptyContentCard("动画", Icons.Filled.Animation, "暂无动画内容")
        return
    }

    val fullHtml = remember(html) { normalizeAnimationHtmlForAndroid(html) }
    var debugInfo by remember(html) { mutableStateOf("") }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.primaryContainer
            ) {
                Row(Modifier.padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Filled.Animation, null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onPrimaryContainer)
                    Spacer(Modifier.width(8.dp))
                    Text("动画资源", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onPrimaryContainer)
                }
            }
            AndroidView(
                factory = { ctx ->
                    WebView(ctx).apply {
                        setBackgroundColor(android.graphics.Color.argb(255, 5, 5, 5))
                        applyResourceWebSettings(allowFileAccess = true)
                        webChromeClient = DiagnosticWebChromeClient { message ->
                            if (message.contains("ERROR", ignoreCase = true)) debugInfo = message
                        }
                        webViewClient = object : WebViewClient() {
                            override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                                if (request?.isForMainFrame == true) {
                                    debugInfo = "页面加载失败: ${error?.description}"
                                }
                            }
                        }
                        setOnTouchListener { v, event ->
                            when (event.action) {
                                android.view.MotionEvent.ACTION_DOWN, android.view.MotionEvent.ACTION_MOVE -> v.parent?.requestDisallowInterceptTouchEvent(true)
                                android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> v.parent?.requestDisallowInterceptTouchEvent(false)
                            }
                            false
                        }
                    }
                },
                update = { webView ->
                    webView.loadDataWithBaseURL("file:///android_asset/", fullHtml, "text/html", "UTF-8", null)
                },
                modifier = Modifier.fillMaxWidth().height(520.dp).clip(RoundedCornerShape(bottomStart = 16.dp, bottomEnd = 16.dp))
            )
            if (debugInfo.isNotBlank()) {
                Surface(
                    color = MaterialTheme.colorScheme.errorContainer,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = debugInfo,
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(12.dp)
                    )
                }
            }
        }
    }
}

// ── Podcast ───────────────────────────────────────────────────

@Composable
private fun PodcastContent(moduleData: Map<String, Any>) {
    val content = moduleData["content"]?.toString()
        ?: moduleData["html"]?.toString()
        ?: ""

    val audioUrl = moduleData["audio_url"]?.toString()
        ?: moduleData["audioUrl"]?.toString()
        ?: moduleData["url"]?.toString()

    val filename = moduleData["audio_filename"]?.toString()
        ?: moduleData["audioFilename"]?.toString()
        ?: moduleData["filename"]?.toString()

    if (content.isBlank() && audioUrl.isNullOrBlank()) {
        EmptyContentCard("播客", Icons.Filled.Headphones, "暂无播客内容")
        return
    }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.secondaryContainer
            ) {
                Row(Modifier.padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Filled.Headphones, null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSecondaryContainer)
                    Spacer(Modifier.width(8.dp))
                    Text("播客音频", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onSecondaryContainer)
                }
            }

            if (content.contains("<") && (content.contains("<audio") || content.contains("<iframe") || content.contains("<html"))) {
                AndroidView(
                    factory = { ctx ->
                        WebView(ctx).apply {
                            applyResourceWebSettings()
                            setBackgroundColor(android.graphics.Color.TRANSPARENT)
                            setOnTouchListener { v, event ->
                                when (event.action) {
                                    android.view.MotionEvent.ACTION_DOWN, android.view.MotionEvent.ACTION_MOVE -> {
                                        v.parent?.requestDisallowInterceptTouchEvent(true)
                                    }
                                    android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> {
                                        v.parent?.requestDisallowInterceptTouchEvent(false)
                                    }
                                }
                                false
                            }
                        }
                    },
                    update = { webView ->
                        val fullHtml = if (content.contains("<html")) content
                        else """
                            <!DOCTYPE html>
                            <html><head>
                            <meta name="viewport" content="width=device-width,initial-scale=1.0">
                            <style>*{margin:0;padding:8px}body{background:transparent;font-family:system-ui;display:flex;align-items:center;justify-content:center}audio{width:100%;max-width:400px;border-radius:8px}</style>
                            </head><body>$content</body></html>
                        """.trimIndent()
                        webView.loadHtml(fullHtml, Constants.PYTHON_BASE_URL)
                    },
                    modifier = Modifier.fillMaxWidth().height(450.dp)
                )
            } else if (!audioUrl.isNullOrBlank()) {
                val audioHtml = """
                    <!DOCTYPE html>
                    <html><head>
                    <meta name="viewport" content="width=device-width,initial-scale=1.0">
                    <style>
                    *{margin:0;padding:0}
                    body{background:#f8f9fa;display:flex;align-items:center;justify-content:center;height:100%;font-family:system-ui}
                    .player{width:100%;max-width:400px;padding:20px}
                    audio{width:100%;border-radius:8px}
                    </style>
                    </head><body>
                    <div class="player">
                    <audio controls preload="metadata" style="width:100%">
                    <source src="$audioUrl">
                    </audio>
                    </div>
                    </body></html>
                """.trimIndent()
                AndroidView(
                    factory = { ctx ->
                        WebView(ctx).apply {
                            applyResourceWebSettings()
                            setOnTouchListener { v, event ->
                                when (event.action) {
                                    android.view.MotionEvent.ACTION_DOWN, android.view.MotionEvent.ACTION_MOVE -> {
                                        v.parent?.requestDisallowInterceptTouchEvent(true)
                                    }
                                    android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> {
                                        v.parent?.requestDisallowInterceptTouchEvent(false)
                                    }
                                }
                                false
                            }
                        }
                    },
                    update = { webView ->
                        webView.loadHtml(audioHtml, Constants.PYTHON_BASE_URL)
                    },
                    modifier = Modifier.fillMaxWidth().height(220.dp)
                )
            } else {
                Column(Modifier.fillMaxWidth().padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Default.Headphones, null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.primary)
                    Spacer(Modifier.height(12.dp))
                    Text("播客音频", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    if (content.isNotBlank()) {
                        Spacer(Modifier.height(8.dp))
                        Text(content.take(200), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }

            // Download link if filename available
            if (filename != null && audioUrl != null) {
                val context = LocalContext.current
                Surface(
                    modifier = Modifier.fillMaxWidth().clickable {
                        try {
                            val intent = android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(audioUrl))
                            context.startActivity(intent)
                        } catch (e: Exception) {
                            android.widget.Toast.makeText(context, "无法打开链接", android.widget.Toast.LENGTH_SHORT).show()
                        }
                    },
                    color = MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Row(
                        Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Download, null, modifier = Modifier.size(16.dp), tint = MaterialTheme.colorScheme.primary)
                        Spacer(Modifier.width(8.dp))
                        Text(
                            filename,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }
        }
    }
}

// ── PPTX ──────────────────────────────────────────────────────

@Composable
private fun PptxContent(moduleData: Map<String, Any>) {
    val rawPptxUrl = moduleData["pptx_url"]?.toString()
        ?: moduleData["pptxUrl"]?.toString()
        ?: moduleData["url"]?.toString()
        ?: moduleData["file_url"]?.toString()
        ?: moduleData["fileUrl"]?.toString()
    val html = moduleData["html"]?.toString()
    val content = moduleData["content"]?.toString()
    val slideCount = (moduleData["slide_count"] as? Number)?.toInt()
        ?: (moduleData["slideCount"] as? Number)?.toInt()
    val filename = moduleData["pptx_filename"]?.toString()
        ?: moduleData["pptxFilename"]?.toString()
        ?: moduleData["filename"]?.toString()
    val pptxUrl = remember(rawPptxUrl, filename) {
        resolvePptxUrl(rawPptxUrl, filename)
    }

    val hasOfficeUrl = !pptxUrl.isNullOrBlank()
    val hasHtml = !html.isNullOrBlank() && html.contains("<")
    val hasContent = !content.isNullOrBlank() && content.contains("<")

    if (!hasOfficeUrl && !hasHtml && !hasContent && content.isNullOrBlank()) {
        EmptyContentCard("演示文稿", Icons.Filled.Slideshow, "暂无演示文稿内容")
        return
    }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.tertiaryContainer
            ) {
                Row(
                    Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.Slideshow, null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onTertiaryContainer)
                        Spacer(Modifier.width(8.dp))
                        Text("演示文稿", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onTertiaryContainer)
                    }
                    if (slideCount != null) {
                        Surface(shape = RoundedCornerShape(8.dp), color = MaterialTheme.colorScheme.tertiary.copy(alpha = 0.2f)) {
                            Text(
                                "$slideCount 页",
                                Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.tertiary
                            )
                        }
                    }
                }
            }

            var viewMode by remember(moduleData) { mutableStateOf(if (hasOfficeUrl) "office" else "html") }

            if (hasOfficeUrl && (hasHtml || hasContent)) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    val isHtml = viewMode == "html"
                    Button(
                        onClick = { viewMode = "html" },
                        colors = if (isHtml) ButtonDefaults.buttonColors() else ButtonDefaults.outlinedButtonColors(),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("网页版 slides", style = MaterialTheme.typography.labelMedium)
                    }
                    Button(
                        onClick = { viewMode = "office" },
                        colors = if (!isHtml) ButtonDefaults.buttonColors() else ButtonDefaults.outlinedButtonColors(),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Office 在线预览", style = MaterialTheme.typography.labelMedium)
                    }
                }
            }

            Box(modifier = Modifier.fillMaxWidth().height(580.dp)) {
                if (viewMode == "office" && hasOfficeUrl) {
                    val viewerUrl = "https://view.officeapps.live.com/op/embed.aspx?src=${java.net.URLEncoder.encode(pptxUrl!!, "UTF-8")}"
                    AndroidView(
                        factory = { ctx ->
                            WebView(ctx).apply {
                                applyResourceWebSettings()
                                webChromeClient = WebChromeClient()
                                webViewClient = ResourceWebViewClient(ctx)
                                setOnTouchListener { v, event ->
                                    when (event.action) {
                                        android.view.MotionEvent.ACTION_DOWN, android.view.MotionEvent.ACTION_MOVE -> {
                                            v.parent?.requestDisallowInterceptTouchEvent(true)
                                        }
                                        android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> {
                                            v.parent?.requestDisallowInterceptTouchEvent(false)
                                        }
                                    }
                                    false
                                }
                            }
                        },
                        update = { webView ->
                            webView.loadUrl(viewerUrl)
                        },
                        modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(bottomStart = 16.dp, bottomEnd = 16.dp))
                    )
                } else {
                    val slidesHtml = if (hasHtml) html else content
                    if (!slidesHtml.isNullOrBlank() && (hasHtml || hasContent)) {
                        AndroidView(
                            factory = { ctx ->
                                WebView(ctx).apply {
                                    applyResourceWebSettings()
                                    webChromeClient = WebChromeClient()
                                    webViewClient = ResourceWebViewClient(ctx)
                                    setOnTouchListener { v, event ->
                                        when (event.action) {
                                            android.view.MotionEvent.ACTION_DOWN, android.view.MotionEvent.ACTION_MOVE -> {
                                                v.parent?.requestDisallowInterceptTouchEvent(true)
                                            }
                                            android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> {
                                                v.parent?.requestDisallowInterceptTouchEvent(false)
                                            }
                                        }
                                        false
                                    }
                                }
                            },
                            update = { webView ->
                                val fullHtml = if (slidesHtml.contains("<html")) slidesHtml
                                else """
                                    <!DOCTYPE html>
                                    <html><head>
                                    <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=3.0,user-scalable=yes">
                                    <style>*{margin:0;padding:0}body{background:#fff;overflow-x:hidden}</style>
                                    </head><body>$slidesHtml</body></html>
                                """.trimIndent()
                                webView.loadHtml(fullHtml, Constants.PYTHON_BASE_URL)
                            },
                            modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(bottomStart = 16.dp, bottomEnd = 16.dp))
                        )
                    } else {
                        // Plain text content fallback
                        Column(Modifier.fillMaxSize().padding(16.dp)) {
                            MarkdownRenderer(content = content ?: "", modifier = Modifier.fillMaxWidth())
                        }
                    }
                }
            }

            // Download link if filename available
            if (filename != null && pptxUrl != null) {
                val context = LocalContext.current
                Surface(
                    modifier = Modifier.fillMaxWidth().clickable {
                        try {
                            val intent = android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(pptxUrl))
                            context.startActivity(intent)
                        } catch (e: Exception) {
                            android.widget.Toast.makeText(context, "无法打开链接", android.widget.Toast.LENGTH_SHORT).show()
                        }
                    },
                    color = MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Row(
                        Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Download, null, modifier = Modifier.size(16.dp), tint = MaterialTheme.colorScheme.primary)
                        Spacer(Modifier.width(8.dp))
                        Text(
                            filename,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }
        }
    }
}

// ── Helpers ───────────────────────────────────────────────────

private data class MindmapNode(
    val topic: String,
    val children: List<MindmapNode> = emptyList()
)

@Composable
private fun MindElixirWebView(
    nodeData: Map<String, Any>,
    onFallback: () -> Unit,
    modifier: Modifier = Modifier
) {
    val mindmapHtml = remember(nodeData) { buildMindElixirHtml(nodeData) }
    var errorMsg by remember(nodeData) { mutableStateOf("") }
    Column(modifier = modifier) {
        AndroidView(
            modifier = Modifier.fillMaxWidth().weight(1f),
            factory = { ctx ->
                WebView(ctx).apply {
                    setBackgroundColor(android.graphics.Color.WHITE)
                    applyResourceWebSettings(allowFileAccess = false)
                    webChromeClient = DiagnosticWebChromeClient { message ->
                        if (message.contains("ERROR", ignoreCase = true)) errorMsg = message
                    }
                    webViewClient = object : WebViewClient() {
                        override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                            if (request?.isForMainFrame == true) {
                                errorMsg = "加载失败: ${error?.description}"
                                onFallback()
                            }
                        }
                    }
                    setOnTouchListener { v, event ->
                        when (event.action) {
                            android.view.MotionEvent.ACTION_DOWN, android.view.MotionEvent.ACTION_MOVE -> v.parent?.requestDisallowInterceptTouchEvent(true)
                            android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> v.parent?.requestDisallowInterceptTouchEvent(false)
                        }
                        false
                    }
                }
            },
            update = { webView -> webView.loadDataWithBaseURL("file:///android_asset/", mindmapHtml, "text/html", "UTF-8", null) }
        )
        if (errorMsg.isNotBlank()) {
            Surface(color = MaterialTheme.colorScheme.errorContainer, modifier = Modifier.fillMaxWidth()) {
                Text(errorMsg, color = MaterialTheme.colorScheme.onErrorContainer, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(8.dp))
            }
        }
    }
}

@Composable
private fun MindmapFallback(root: MindmapNode) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 420.dp, max = 620.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(Navy50)
            .border(1.dp, Navy100, RoundedCornerShape(14.dp))
            .horizontalScroll(rememberScrollState())
            .verticalScroll(rememberScrollState())
            .padding(24.dp)
    ) {
        MindmapNodeView(root, depth = 0)
    }
}

@Composable
private fun MindmapNodeView(node: MindmapNode, depth: Int) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Surface(
            shape = RoundedCornerShape(if (depth == 0) 12.dp else 10.dp),
            color = when (depth) {
                0 -> Navy600
                1 -> MaterialTheme.colorScheme.surface
                else -> Navy50
            },
            border = if (depth == 0) null else BorderStroke(1.dp, if (depth == 1) Navy200 else Navy100),
            tonalElevation = if (depth <= 1) 1.dp else 0.dp,
            shadowElevation = if (depth == 0) 3.dp else 0.dp,
            modifier = Modifier.widthIn(min = if (depth == 0) 150.dp else 132.dp, max = 260.dp)
        ) {
            Text(
                node.topic.ifBlank { "未命名节点" },
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                style = if (depth == 0) MaterialTheme.typography.titleSmall else MaterialTheme.typography.bodySmall,
                fontWeight = if (depth <= 1) FontWeight.SemiBold else FontWeight.Normal,
                color = if (depth == 0) androidx.compose.ui.graphics.Color.White else MaterialTheme.colorScheme.onSurface,
                maxLines = 5,
                overflow = TextOverflow.Ellipsis
            )
        }

        if (node.children.isNotEmpty()) {
            Box(Modifier.width(28.dp), contentAlignment = Alignment.Center) {
                Box(Modifier.fillMaxWidth().height(1.dp).background(Navy200))
            }
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                node.children.forEachIndexed { index, child ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        MindmapNodeView(child, depth + 1)
                    }
                }
            }
        }
    }
}

private fun buildMindElixirHtml(data: Map<String, Any>): String {
    val rawJson = Gson().toJson(data)
    return """
        <!doctype html>
        <html lang="zh-CN">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=4.0,user-scalable=yes">
          <link rel="stylesheet" href="mind-elixir.css">
          <style>
            html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#fff;font-family:system-ui,-apple-system,sans-serif}
            #map{width:100vw;height:100vh;background:#fff}
            .topic{border-radius:8px!important;padding:6px 12px!important;font-size:14px!important}
            .root>.topic{background:linear-gradient(135deg,#34508e,#4164b2)!important;color:#fff!important;font-weight:600!important;border-radius:10px!important;padding:8px 16px!important;box-shadow:0 2px 8px rgba(52,80,142,.3)!important}
            .lines path{stroke:#b3c1e0!important;stroke-width:2!important}
          </style>
        </head>
        <body>
          <div id="map"></div>
          <script src="MindElixirLite.iife.js"></script>
          <script>
            (function(){
              try {
                var rawData = $rawJson;
                var mindData = rawData && rawData.nodeData ? rawData : { nodeData: rawData, direction: 2 };
                if (!mindData.nodeData) throw new Error('missing nodeData');
                function expandAll(node){ if(!node)return; node.expanded=true; (node.children||[]).forEach(expandAll); }
                expandAll(mindData.nodeData);
                var Mind = window.MindElixirLite;
                if (!Mind) throw new Error('MindElixirLite not loaded');
                var MindConstructor = Mind.default || Mind;
                if (typeof MindConstructor !== 'function') throw new Error('MindElixirLite constructor not found');
                var direction = Mind.SIDE || 2;
                var mind = new MindConstructor({
                  el: document.getElementById('map'),
                  direction: direction,
                  editable: false,
                  contextMenu: false,
                  toolBar: false,
                  keypress: false,
                  overflowHidden: false,
                  theme: {
                    name: 'navy', type: 'light',
                    palette: ['#34508e','#4164b2','#6783c1','#8da2d1','#649b64','#c9873b','#83af83','#507c50'],
                    cssVar: {
                      '--node-gap-x': '80px', '--node-gap-y': '12px', '--main-gap-x': '100px', '--main-gap-y': '20px',
                      '--main-color': '#273c6b', '--main-bgcolor': '#f0f3f9', '--color': '#1a2847', '--bgcolor': '#ffffff',
                      '--root-color': '#ffffff', '--root-bgcolor': '#34508e', '--root-border-color': '#273c6b'
                    }
                  }
                });
                mindData.direction = direction;
                mind.init(mindData);
                setTimeout(function(){ try { mind.scaleFit(); mind.toCenter(); } catch(e){} }, 180);
              } catch(e) {
                console.error('MindElixir init error: ' + e.message + ' stack: ' + (e.stack||''));
                document.body.innerHTML = '<div style="padding:20px;color:#b91c1c;font:14px system-ui">MindElixir 加载失败：' + e.message + '</div>';
              }
            })();
          </script>
        </body>
        </html>
    """.trimIndent()
}

private fun normalizeMindmapRoot(data: Map<String, Any>, moduleData: Map<String, Any>): MindmapNode {
    val root = (data["nodeData"] as? Map<*, *>) ?: data
    return mapToMindmapNode(root, moduleData["module_title"]?.toString() ?: moduleData["title"]?.toString() ?: "思维导图")
}

private fun mapToMindmapNode(raw: Map<*, *>, fallbackTopic: String): MindmapNode {
    val topic = raw["topic"]?.toString()
        ?: raw["title"]?.toString()
        ?: raw["name"]?.toString()
        ?: fallbackTopic
    val children = (raw["children"] as? List<*>)
        ?.mapNotNull { child ->
            when (child) {
                is Map<*, *> -> mapToMindmapNode(child, "子节点")
                is String -> MindmapNode(child)
                else -> null
            }
        }
        ?: emptyList()
    return MindmapNode(topic, children)
}

private fun normalizeAnimationHtmlForAndroid(raw: String): String {
    val rawWithLocalGsap = raw.replace(
        "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js",
        "gsap.min.js"
    )
    val baseTag = "<base href=\"file:///android_asset/\">"
    val inner = if (rawWithLocalGsap.contains("<html", ignoreCase = true) || rawWithLocalGsap.contains("<!DOCTYPE", ignoreCase = true)) {
        rawWithLocalGsap
    } else {
        """
        <!DOCTYPE html>
        <html><head><meta charset="UTF-8"></head><body>$rawWithLocalGsap</body></html>
        """.trimIndent()
    }

    return if (inner.contains("<head", ignoreCase = true)) {
        inner.replace(Regex("<head[^>]*>", RegexOption.IGNORE_CASE)) {
            it.value + baseTag + "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no\">"
        }
    } else {
        inner.replace("<html>", "<html><head>$baseTag<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no\"></head>", ignoreCase = true)
    }
}

private class DiagnosticWebChromeClient(
    private val onMessage: (String) -> Unit
) : WebChromeClient() {
    override fun onConsoleMessage(consoleMessage: ConsoleMessage?): Boolean {
        val message = consoleMessage ?: return false
        val text = "WebView ${message.messageLevel()}: ${message.message()} (${message.sourceId()}:${message.lineNumber()})"
        if (message.messageLevel() == ConsoleMessage.MessageLevel.ERROR || message.message().contains("animation", ignoreCase = true)) {
            onMessage(text)
        }
        return false
    }
}

private fun WebView.applyResourceWebSettings(allowFileAccess: Boolean = true) {
    settings.javaScriptEnabled = true
    settings.domStorageEnabled = true
    settings.databaseEnabled = true
    settings.allowFileAccess = allowFileAccess
    settings.allowContentAccess = true
    settings.allowFileAccessFromFileURLs = true
    settings.allowUniversalAccessFromFileURLs = true
    settings.mediaPlaybackRequiresUserGesture = false
    settings.setSupportZoom(true)
    settings.builtInZoomControls = true
    settings.displayZoomControls = false
    settings.loadWithOverviewMode = true
    settings.useWideViewPort = true
    settings.cacheMode = WebSettings.LOAD_DEFAULT
    settings.userAgentString = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"
    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
    }
}

private fun WebView.loadHtml(html: String, baseUrl: String = Constants.PYTHON_BASE_URL) {
    loadDataWithBaseURL(baseUrl, html, "text/html", "UTF-8", null)
}

private class ResourceWebViewClient(
    private val context: android.content.Context
) : WebViewClient() {
    override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
        val url = request?.url?.toString().orEmpty()
        if (url.startsWith("http://") || url.startsWith("https://")) return false
        return try {
            context.startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, request?.url))
            true
        } catch (_: Exception) {
            false
        }
    }
}

private fun resolvePptxUrl(rawUrl: String?, filename: String?): String? {
    rawUrl?.takeIf { it.isNotBlank() }?.let { return resolveResourceUrl(it) }
    return filename?.takeIf { it.isNotBlank() }?.let {
        Constants.PYTHON_BASE_URL.trimEnd('/') + "/api/ai/resource/pptx/download/" + it
    }
}

private fun resolveResourceUrl(url: String): String {
    if (url.startsWith("http://") || url.startsWith("https://")) return url
    return Constants.PYTHON_BASE_URL.trimEnd('/') + "/" + url.trimStart('/')
}

@Composable
private fun EmptyContentCard(title: String, icon: androidx.compose.ui.graphics.vector.ImageVector, message: String) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(Modifier.fillMaxWidth().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(icon, null, modifier = Modifier.size(40.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f))
            Spacer(Modifier.height(8.dp))
            Text(message, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

private fun extractTextContent(moduleData: Map<String, Any>): String {
    // Priority: content > html > text
    val content = moduleData["content"]?.toString() ?: ""
    if (content.isNotBlank() && !content.startsWith("{") && !content.startsWith("[")) return content

    // Try parsing content as JSON
    if (content.isNotBlank()) {
        try {
            val json = Gson().fromJson(content, JsonObject::class.java)
            json.get("content")?.asString?.let { if (it.isNotBlank()) return it }
            json.get("text")?.asString?.let { if (it.isNotBlank()) return it }
        } catch (_: Exception) {}
    }

    // Try generated_content nested
    val generated = moduleData["generated_content"] as? Map<*, *>
    if (generated != null) {
        generated["content"]?.toString()?.let { if (it.isNotBlank()) return it }
        generated["text"]?.toString()?.let { if (it.isNotBlank()) return it }
    }

    return moduleData["html"]?.toString() ?: moduleData["text"]?.toString() ?: content
}

private fun extractMindmapData(moduleData: Map<String, Any>): Map<String, Any>? {
    // Vue: md.nodeData || md.node_data || md.content
    val raw = moduleData["nodeData"] ?: moduleData["node_data"] ?: moduleData["mindmap"] ?: moduleData["content"]
    return when (raw) {
        is Map<*, *> -> {
            @Suppress("UNCHECKED_CAST")
            raw as Map<String, Any>
        }
        is String -> {
            try {
                val json = Gson().fromJson(raw, JsonObject::class.java)
                jsonObjectToMap(json)
            } catch (_: Exception) {
                // Fallback: split text into child nodes
                val lines = raw.split("\n").filter { it.isNotBlank() }
                if (lines.isNotEmpty()) {
                    mapOf(
                        "topic" to (moduleData["module_title"]?.toString() ?: "思维导图"),
                        "children" to lines.map { mapOf("topic" to it.trim()) }
                    )
                } else null
            }
        }
        else -> null
    }
}

private fun extractVideoList(moduleData: Map<String, Any>): List<Map<String, Any>> {
    val videos = moduleData["videos"]
    if (videos is List<*>) {
        return videos.mapNotNull { item ->
            when (item) {
                is Map<*, *> -> {
                    @Suppress("UNCHECKED_CAST")
                    item as Map<String, Any>
                }
                is String -> mapOf("url" to item, "title" to "视频")
                else -> null
            }
        }
    }
    // Fallback: try content as JSON array
    val content = moduleData["content"]?.toString() ?: ""
    if (content.startsWith("[")) {
        try {
            val arr = Gson().fromJson(content, JsonArray::class.java)
            return arr.mapNotNull { el ->
                if (el.isJsonObject) jsonObjectToMap(el.asJsonObject) else null
            }
        } catch (_: Exception) {}
    }
    return emptyList()
}

private fun getVideoEmbedUrl(url: String): String? {
    // YouTube
    if (url.contains("youtube.com") || url.contains("youtu.be")) {
        val videoId = if (url.contains("youtu.be/")) {
            url.split("youtu.be/")[1].split("?")[0]
        } else if (url.contains("v=")) {
            try { java.net.URI(url).query?.split("&")?.find { it.startsWith("v=") }?.substring(2) } catch (_: Exception) { null }
        } else null
        if (videoId != null) return "https://www.youtube.com/embed/$videoId?rel=0"
    }
    // Bilibili
    val bvMatch = Regex("(BV[A-Za-z0-9]+)").find(url)
    if (bvMatch != null) {
        return "https://player.bilibili.com/player.html?bvid=${bvMatch.value}&page=1&high_quality=1&high_wide=1&as_wide=1&autoplay=0"
    }
    return null
}

private fun parseQuizQuestions(moduleData: Map<String, Any>): List<Map<String, Any>> {
    // Vue: check moduleData.questions, then parse content as JSON
    val questionsRaw = moduleData["questions"]
    if (questionsRaw is List<*>) {
        return questionsRaw.mapNotNull { item ->
            when (item) {
                is Map<*, *> -> {
                    @Suppress("UNCHECKED_CAST")
                    normalizeQuizQuestion(item as Map<String, Any>)
                }
                else -> null
            }
        }
    }

    // Try content as JSON
    val content = moduleData["content"]?.toString() ?: ""
    if (content.startsWith("{") || content.startsWith("[")) {
        try {
            val json = Gson().fromJson(content, JsonElement::class.java)
            val questionsArray = when {
                json.isJsonObject -> json.asJsonObject.getAsJsonArray("questions")
                json.isJsonArray -> json.asJsonArray
                else -> null
            }
            if (questionsArray != null) {
                return questionsArray.mapNotNull { el ->
                    if (el.isJsonObject) normalizeQuizQuestion(jsonObjectToMap(el.asJsonObject)) else null
                }
            }
        } catch (_: Exception) {}
    }

    return emptyList()
}

private fun normalizeQuizQuestion(q: Map<String, Any>): Map<String, Any> {
    return mapOf(
        "type" to (q["type"]?.toString() ?: q["question_type"]?.toString() ?: "short_answer"),
        "question" to (q["question"]?.toString() ?: q["question_text"]?.toString() ?: ""),
        "options" to (q["options"] as? List<*> ?: emptyList<String>()),
        "correctAnswer" to (q["correctAnswer"]?.toString() ?: q["correct_answer"]?.toString() ?: ""),
        "explanation" to (q["explanation"]?.toString() ?: ""),
        "difficulty" to ((q["difficulty"] as? Number)?.toInt() ?: 3)
    )
}

private fun jsonObjectToMap(json: JsonObject): Map<String, Any> {
    val map = mutableMapOf<String, Any>()
    json.entrySet().forEach { (key, value) ->
        map[key] = jsonElementToAny(value)
    }
    return map
}

private fun jsonElementToAny(element: JsonElement): Any {
    return when {
        element.isJsonPrimitive -> {
            val p = element.asJsonPrimitive
            when {
                p.isBoolean -> p.asBoolean
                p.isNumber -> p.asNumber
                else -> p.asString
            }
        }
        element.isJsonObject -> jsonObjectToMap(element.asJsonObject)
        element.isJsonArray -> element.asJsonArray.map { jsonElementToAny(it) }
        else -> element.toString()
    }
}

private fun stripCitationSection(content: String): String {
    val headers = listOf("## 参考文献", "### 参考文献", "## 参考资料", "### 参考资料", "## 引用文献", "### 引用文献")
    for (header in headers) {
        val idx = content.indexOf(header)
        if (idx != -1) return content.substring(0, idx).trim()
    }
    return content
}

private fun getResourceIcon(type: String) = when (type) {
    "document" -> Icons.Outlined.Description
    "text" -> Icons.Outlined.Article
    "reading" -> Icons.Outlined.MenuBook
    "summary" -> Icons.Outlined.Summarize
    "mindmap" -> Icons.Filled.Folder
    "quiz" -> Icons.Outlined.Quiz
    "code" -> Icons.Outlined.Code
    "video" -> Icons.Filled.PlayCircle
    "image" -> Icons.Outlined.Image
    "diagram" -> Icons.Outlined.BarChart
    "animation" -> Icons.Filled.Animation
    "podcast" -> Icons.Filled.Headphones
    "pptx" -> Icons.Filled.Slideshow
    else -> Icons.Outlined.Description
}

private fun getResourceTypeName(type: String) = when (type) {
    "document" -> "文档"
    "text" -> "图文"
    "reading" -> "阅读"
    "summary" -> "总结"
    "mindmap" -> "导图"
    "quiz" -> "题目"
    "code" -> "代码"
    "video" -> "视频"
    "image" -> "图片"
    "diagram" -> "图表"
    "animation" -> "动画"
    "podcast" -> "播客"
    "pptx" -> "PPT"
    else -> "资源"
}

private fun getQuestionTypeName(type: String) = when (type) {
    "single_choice" -> "单选题"
    "multiple_choice" -> "多选题"
    "true_false" -> "判断题"
    "fill_blank" -> "填空题"
    "short_answer" -> "简答题"
    "code_output" -> "代码输出"
    else -> "题目"
}

private fun launchVideoApp(context: android.content.Context, url: String) {
    val uri = android.net.Uri.parse(url)
    val host = uri.host?.lowercase() ?: ""
    
    // YouTube
    if (host.contains("youtube.com") || host.contains("youtu.be")) {
        val videoId = if (url.contains("youtu.be/")) {
            url.split("youtu.be/")[1].split("?")[0]
        } else if (url.contains("v=")) {
            uri.getQueryParameter("v")
        } else null
        
        if (videoId != null) {
            try {
                val intent = android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("vnd.youtube:$videoId"))
                context.startActivity(intent)
                return
            } catch (_: Exception) {}
        }
    }
    
    // Bilibili
    val bvMatch = Regex("(BV[A-Za-z0-9]+)").find(url)
    if (bvMatch != null) {
        val bvid = bvMatch.value
        try {
            val intent = android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("bilibili://video/$bvid"))
            context.startActivity(intent)
            return
        } catch (_: Exception) {}
    }
    
    // Fallback: Open in Web Browser
    try {
        val intent = android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(url))
        context.startActivity(intent)
    } catch (e: Exception) {
        android.widget.Toast.makeText(context, "无法打开视频链接", android.widget.Toast.LENGTH_SHORT).show()
    }
}
