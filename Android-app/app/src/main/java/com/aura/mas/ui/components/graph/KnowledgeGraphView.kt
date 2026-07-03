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

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun KnowledgeGraphView(
    jsonData: String,
    onNodeClick: (String) -> Unit,
    modifier: Modifier = Modifier,
    isDarkTheme: Boolean = isSystemInDarkTheme()
) {
    var webViewRef by remember { mutableStateOf<WebView?>(null) }
    var isHtmlLoaded by remember { mutableStateOf(false) }

    // HTML loading callback
    val webViewClientInstance = remember {
        object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                isHtmlLoaded = true
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

    AndroidView(
        factory = { context ->
            WebView(context).apply {
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
                loadUrl("file:///android_asset/echarts_graph.html")
                webViewRef = this
            }
        },
        modifier = modifier,
        onRelease = {
            webViewRef = null
        }
    )
}
