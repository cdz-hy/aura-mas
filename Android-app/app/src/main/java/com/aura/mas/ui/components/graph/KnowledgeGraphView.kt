package com.aura.mas.ui.components.graph

import android.annotation.SuppressLint
import android.graphics.Color
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.ui.unit.dp

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun KnowledgeGraphView(
    jsonData: String,
    onNodeClick: (String) -> Unit,
    modifier: Modifier = Modifier,
    isDarkTheme: Boolean = isSystemInDarkTheme()
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    var webViewRef by remember { mutableStateOf<WebView?>(null) }
    var isHtmlLoaded by remember { mutableStateOf(false) }
    var loadError by remember { mutableStateOf<String?>(null) }

    // HTML loading callback with WebViewAssetLoader support
    val webViewClientInstance = remember(context) {
        val assetLoader = androidx.webkit.WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", androidx.webkit.WebViewAssetLoader.AssetsPathHandler(context))
            .build()

        object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                if (loadError == null) {
                    isHtmlLoaded = true
                }
            }

            override fun onReceivedError(
                view: WebView?,
                request: android.webkit.WebResourceRequest?,
                error: android.webkit.WebResourceError?
            ) {
                super.onReceivedError(view, request, error)
                if (request?.isForMainFrame == true) {
                    loadError = "加载失败: ${error?.description}"
                    android.util.Log.e("WebViewConsole", "onReceivedError: ${error?.description} for URL: ${request.url}")
                }
            }

            override fun shouldInterceptRequest(
                view: WebView?,
                request: android.webkit.WebResourceRequest?
            ): android.webkit.WebResourceResponse? {
                return request?.url?.let { assetLoader.shouldInterceptRequest(it) }
            }
        }
    }

    // Android to JavaScript Interface Bridge
    val jsBridge = remember(onNodeClick) {
        object {
            @JavascriptInterface
            fun onNodeClick(nodeId: String) {
                // Post to main UI thread
                webViewRef?.post {
                    onNodeClick(nodeId)
                }
            }
        }
    }

    // Update graph data when data or theme changes AND html has finished loading
    LaunchedEffect(jsonData, isDarkTheme, isHtmlLoaded) {
        if (isHtmlLoaded && jsonData.isNotBlank()) {
            webViewRef?.evaluateJavascript(
                "javascript:loadGraphData($jsonData, $isDarkTheme)",
                null
            )
        }
    }

    androidx.compose.foundation.layout.Box(modifier = modifier) {
        AndroidView(
            factory = { ctx ->
                WebView(ctx).apply {
                    webViewClient = webViewClientInstance
                    webChromeClient = object : android.webkit.WebChromeClient() {
                        override fun onConsoleMessage(consoleMessage: android.webkit.ConsoleMessage?): Boolean {
                            android.util.Log.d("WebViewConsole", "${consoleMessage?.message()} -- From line ${consoleMessage?.lineNumber()} of ${consoleMessage?.sourceId()}")
                            return true
                        }
                    }
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = true
                    settings.useWideViewPort = true
                    settings.loadWithOverviewMode = true
                    settings.allowFileAccess = true
                    settings.allowContentAccess = true
                    settings.allowFileAccessFromFileURLs = true
                    settings.allowUniversalAccessFromFileURLs = true

                    // Allow transparent background to match Compose theme colors
                    setBackgroundColor(Color.TRANSPARENT)

                    // Hardware acceleration for high-performance fluid 60fps graph animations
                    setLayerType(View.LAYER_TYPE_HARDWARE, null)

                    addJavascriptInterface(jsBridge, "AndroidInterface")
                    loadUrl("https://appassets.androidplatform.net/assets/echarts_graph.html")
                    webViewRef = this
                }
            },
            modifier = Modifier.fillMaxSize(),
            onRelease = {
                webViewRef = null
            }
        )
        if (loadError != null) {
            androidx.compose.material3.Surface(
                color = androidx.compose.material3.MaterialTheme.colorScheme.errorContainer,
                modifier = Modifier.align(androidx.compose.ui.Alignment.Center).padding(16.dp),
                shape = androidx.compose.foundation.shape.RoundedCornerShape(8.dp)
            ) {
                androidx.compose.material3.Text(
                    text = loadError ?: "",
                    color = androidx.compose.material3.MaterialTheme.colorScheme.onErrorContainer,
                    modifier = Modifier.padding(16.dp)
                )
            }
        }
    }
}
