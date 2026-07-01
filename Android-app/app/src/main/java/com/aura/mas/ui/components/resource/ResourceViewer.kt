package com.aura.mas.ui.components.resource

import android.webkit.WebView
import androidx.compose.foundation.background
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.aura.mas.data.model.LearningResource
import androidx.compose.foundation.clickable
import androidx.compose.ui.platform.LocalContext
import com.aura.mas.ui.theme.*
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
            "quiz" -> QuizContent(moduleData)
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
private fun QuizContent(moduleData: Map<String, Any>) {
    val questions = remember(moduleData) { parseQuizQuestions(moduleData) }

    if (questions.isEmpty()) {
        EmptyContentCard("测验", Icons.Outlined.Quiz, "暂无测验题目")
        return
    }

    Column {
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
    val isDark = androidx.compose.foundation.isSystemInDarkTheme()

    if (nodeData == null) {
        EmptyContentCard("思维导图", Icons.Filled.Folder, "思维导图数据加载中")
        return
    }

    val json = remember(nodeData) { Gson().toJson(nodeData) }

    AndroidView(
        modifier = Modifier.fillMaxWidth().height(450.dp),
        factory = { ctx ->
            android.webkit.WebView(ctx).apply {
                setBackgroundColor(android.graphics.Color.WHITE)
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                settings.allowFileAccess = false
                settings.setSupportZoom(true)
                settings.builtInZoomControls = true
                settings.displayZoomControls = false
                setOnTouchListener { v, _ ->
                    v.parent?.requestDisallowInterceptTouchEvent(true)
                    false
                }
            }
        },
        update = { webView ->
            val html = """
                <!DOCTYPE html>
                <html><head>
                <meta name="viewport" content="width=device-width,initial-scale=1.0">
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/mind-elixir/dist/style.css">
                <style>
                *{margin:0;padding:0;box-sizing:border-box}
                body, html{width:100%;height:100%;background:#ffffff;overflow:hidden}
                #map{width:100%;height:100%}
                /* Custom styles to match App theme */
                .topic {
                    border-radius: 8px !important;
                    padding: 6px 12px !important;
                    font-family: system-ui, -apple-system, sans-serif !important;
                    font-size: 14px !important;
                }
                .root > .topic {
                    background: linear-gradient(135deg, #34508e, #4164b2) !important;
                    color: #ffffff !important;
                    font-weight: 600 !important;
                    font-size: 15px !important;
                    border-radius: 10px !important;
                    padding: 8px 16px !important;
                    box-shadow: 0 2px 8px rgba(52, 80, 142, 0.3) !important;
                }
                .lines path {
                    stroke: #b3c1e0 !important;
                    stroke-width: 2 !important;
                }
                </style>
                <script src="https://cdn.jsdelivr.net/npm/mind-elixir"></script>
                </head><body>
                <div id="map"></div>
                <script>
                try {
                    var rawNode = $json;
                    // Ensure all nodes are expanded by default
                    function expandAll(node) {
                        node.expanded = true;
                        if (node.children && node.children.length > 0) {
                            node.children.forEach(expandAll);
                        }
                    }
                    expandAll(rawNode);

                    var mind = new MindElixir({
                        el: document.getElementById('map'),
                        direction: 2, // SIDE
                        editable: false,
                        contextMenu: false,
                        toolBar: false,
                        keypress: false,
                        overflowHidden: false,
                        theme: {
                            name: 'navy',
                            type: 'light',
                            palette: [
                                '#34508e', '#4164b2', '#6783c1', '#8da2d1',
                                '#649b64', '#c9873b', '#83af83', '#507c50'
                            ]
                        }
                    });

                    mind.init({
                        nodeData: rawNode,
                        direction: 2
                    });

                    setTimeout(function() {
                        mind.scaleFit();
                        mind.toCenter();
                    }, 200);
                } catch(e) {
                    document.body.innerHTML = "<div style='padding:20px;color:red'>加载思维导图出错: " + e.message + "</div>";
                }
                </script>
                </body></html>
            """.trimIndent()
            webView.loadDataWithBaseURL("http://localhost/", html, "text/html", "UTF-8", null)
        }
    )
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
                                    settings.javaScriptEnabled = true
                                    settings.domStorageEnabled = true
                                    settings.databaseEnabled = true
                                    settings.mediaPlaybackRequiresUserGesture = false
                                    // Force a Mobile User-Agent to render HTML5 player controls correctly
                                    settings.userAgentString = "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36"
                                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                                        settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
                                    }
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
                                val headers = mutableMapOf<String, String>()
                                if (embedUrl.contains("bilibili")) {
                                    headers["Referer"] = "https://www.bilibili.com"
                                } else if (embedUrl.contains("youtube")) {
                                    headers["Referer"] = "https://www.youtube.com"
                                }
                                webView.loadUrl(embedUrl, headers)
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
        ?: ""

    if (html.isBlank()) {
        EmptyContentCard("动画", Icons.Filled.Animation, "暂无动画内容")
        return
    }

    // Wrap in proper HTML if not already wrapped
    val fullHtml = if (html.contains("<html") || html.contains("<!DOCTYPE")) html
    else """
        <!DOCTYPE html>
        <html><head>
        <meta name="viewport" content="width=device-width,initial-scale=1.0">
        <style>*{margin:0;padding:0}body{background:#fff;overflow:hidden}</style>
        </head><body>$html</body></html>
    """.trimIndent()

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
                        setBackgroundColor(android.graphics.Color.WHITE)
                        settings.javaScriptEnabled = true
                        settings.domStorageEnabled = true
                        settings.allowFileAccess = true
                        settings.mediaPlaybackRequiresUserGesture = false
                        settings.setSupportZoom(true)
                        settings.builtInZoomControls = true
                        settings.displayZoomControls = false
                        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                            settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
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
                    webView.loadDataWithBaseURL("http://localhost/", fullHtml, "text/html", "UTF-8", null)
                },
                modifier = Modifier.fillMaxWidth().height(480.dp).clip(RoundedCornerShape(bottomStart = 16.dp, bottomEnd = 16.dp))
            )
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
                            settings.javaScriptEnabled = true
                            settings.domStorageEnabled = true
                            settings.mediaPlaybackRequiresUserGesture = false
                            setBackgroundColor(android.graphics.Color.TRANSPARENT)
                            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                                settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
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
                        val fullHtml = if (content.contains("<html")) content
                        else """
                            <!DOCTYPE html>
                            <html><head>
                            <meta name="viewport" content="width=device-width,initial-scale=1.0">
                            <style>*{margin:0;padding:8px}body{background:transparent;font-family:system-ui;display:flex;align-items:center;justify-content:center}audio{width:100%;max-width:400px;border-radius:8px}</style>
                            </head><body>$content</body></html>
                        """.trimIndent()
                        webView.loadDataWithBaseURL("http://localhost/", fullHtml, "text/html", "UTF-8", null)
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
                            settings.javaScriptEnabled = true
                            settings.domStorageEnabled = true
                            settings.mediaPlaybackRequiresUserGesture = false
                            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                                settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
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
                        webView.loadDataWithBaseURL("http://localhost/", audioHtml, "text/html", "UTF-8", null)
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
    val pptxUrl = moduleData["pptx_url"]?.toString()
        ?: moduleData["pptxUrl"]?.toString()
        ?: moduleData["url"]?.toString()
    val html = moduleData["html"]?.toString()
    val content = moduleData["content"]?.toString()
    val slideCount = (moduleData["slide_count"] as? Number)?.toInt()
        ?: (moduleData["slideCount"] as? Number)?.toInt()
    val filename = moduleData["pptx_filename"]?.toString()
        ?: moduleData["pptxFilename"]?.toString()

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

            var viewMode by remember { mutableStateOf(if (hasHtml || hasContent) "html" else "office") }

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
                                settings.javaScriptEnabled = true
                                settings.domStorageEnabled = true
                                settings.setSupportZoom(true)
                                settings.builtInZoomControls = true
                                settings.displayZoomControls = false
                                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                                    settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
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
                                    settings.javaScriptEnabled = true
                                    settings.domStorageEnabled = true
                                    settings.setSupportZoom(true)
                                    settings.builtInZoomControls = true
                                    settings.displayZoomControls = false
                                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                                        settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
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
                                val fullHtml = if (slidesHtml.contains("<html")) slidesHtml
                                else """
                                    <!DOCTYPE html>
                                    <html><head>
                                    <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=3.0,user-scalable=yes">
                                    <style>*{margin:0;padding:0}body{background:#fff;overflow-x:hidden}</style>
                                    </head><body>$slidesHtml</body></html>
                                """.trimIndent()
                                webView.loadDataWithBaseURL("http://localhost/", fullHtml, "text/html", "UTF-8", null)
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
    val raw = moduleData["nodeData"] ?: moduleData["node_data"] ?: moduleData["content"]
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
    "document", "reading" -> Icons.Outlined.Description
    "summary" -> Icons.Outlined.Summarize
    "mindmap" -> Icons.Filled.Folder
    "quiz" -> Icons.Outlined.Quiz
    "code" -> Icons.Outlined.Code
    "video" -> Icons.Filled.PlayCircle
    "podcast" -> Icons.Filled.Headphones
    "pptx" -> Icons.Filled.Slideshow
    "animation" -> Icons.Filled.Animation
    else -> Icons.Outlined.Article
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

