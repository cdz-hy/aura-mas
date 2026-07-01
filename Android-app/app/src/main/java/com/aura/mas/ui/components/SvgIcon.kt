package com.aura.mas.ui.components

import android.webkit.WebView
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView

/**
 * Renders an SVG string from planConfig.iconSvg.
 * Uses a large internal viewport (300px) and lets the WebView scale down.
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
            // Render SVG at 300x300 internal resolution
            // The WebView will be constrained by the Compose modifier size
            val html = """
                <html>
                <head>
                <style>
                *{margin:0;padding:0}
                html,body{width:300px;height:300px;background:transparent;overflow:hidden}
                svg{width:300px;height:300px;display:block}
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
