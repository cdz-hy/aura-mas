package com.aura.mas.ui.components

import android.webkit.WebView
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView

/**
 * Renders an SVG string from planConfig.iconSvg using WebView.
 */
@Composable
fun SvgIcon(
    svgString: String,
    modifier: Modifier = Modifier
) {
    AndroidView(
        factory = { ctx ->
            WebView(ctx).apply {
                setBackgroundColor(0x00000000)
                isVerticalScrollBarEnabled = false
                isHorizontalScrollBarEnabled = false
                settings.javaScriptEnabled = false
            }
        },
        update = { webView ->
            val sanitized = svgString.trim()
            val html = """
                <html>
                <head>
                <style>
                * { margin:0; padding:0; }
                body { background:transparent; display:flex; align-items:center; justify-content:center; width:100%; height:100%; }
                svg { width:100%; height:100%; }
                </style>
                </head>
                <body>$sanitized</body>
                </html>
            """.trimIndent()
            webView.loadDataWithBaseURL(null, html, "text/html", "UTF-8", null)
        },
        modifier = modifier
    )
}
