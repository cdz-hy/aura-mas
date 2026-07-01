package com.aura.mas.ui.components.resource

import android.content.Context
import android.graphics.Color
import android.widget.TextView
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import coil.ImageLoader
import coil.decode.GifDecoder
import coil.decode.SvgDecoder
import io.noties.markwon.Markwon
import io.noties.markwon.ext.latex.JLatexMathPlugin
import io.noties.markwon.ext.tables.TablePlugin
import io.noties.markwon.html.HtmlPlugin
import io.noties.markwon.image.coil.CoilImagesPlugin
import io.noties.markwon.inlineparser.MarkwonInlineParserPlugin

/**
 * Full-featured Markdown renderer:
 * 1. Preprocesses LaTeX to use $$ delimiters required by JLatexMathPlugin.
 * 2. Extracts Mermaid code blocks for WebView rendering.
 * 3. Renders Markdown + LaTeX natively using Markwon.
 */
@Composable
fun MarkdownRenderer(
    content: String,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val textColor = MaterialTheme.colorScheme.onSurface
    val isDark = isSystemInDarkTheme()

    // Normalize LaTeX and split out Mermaid segments
    val segments = remember(content) { parseAndNormalizeContent(content) }

    Column(modifier = modifier) {
        segments.forEach { segment ->
            when (segment.type) {
                SegmentType.MARKDOWN -> {
                    if (segment.content.isNotBlank()) {
                        MarkdownSegment(segment.content, context, textColor)
                    }
                }
                SegmentType.MERMAID -> {
                    MermaidView(code = segment.content, isDark = isDark)
                }
            }
        }
    }
}

// ── Markdown segment (Markwon + JLatexMath) ─────────────────────

@Composable
private fun MarkdownSegment(content: String, context: Context, textColor: androidx.compose.ui.graphics.Color) {
    val markwon = remember(context) { buildMarkwon(context) }
    val spanned = remember(content) {
        try { markwon.toMarkdown(content) }
        catch (_: Exception) { android.text.SpannableString(content) }
    }
    AndroidView(
        modifier = Modifier.fillMaxWidth(),
        factory = { ctx ->
            TextView(ctx).apply {
                setTextColor(textColor.toArgb())
                textSize = 15f
                setLineSpacing(0f, 1.5f)
                setPadding(0, 0, 0, 0)
                movementMethod = android.text.method.LinkMovementMethod.getInstance()
            }
        },
        update = { tv ->
            tv.setTextColor(textColor.toArgb())
            markwon.setParsedMarkdown(tv, spanned)
        }
    )
}

// ── Mermaid rendering via WebView ──────────────────────────────

@Composable
private fun MermaidView(code: String, isDark: Boolean) {
    val bgColor = if (isDark) "#1a1a2e" else "#ffffff"

    val escapedCode = code
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\\$")
        .replace("</script>", "<\\/script>")

    AndroidView(
        modifier = Modifier.fillMaxWidth().heightIn(min = 200.dp),
        factory = { ctx ->
            android.webkit.WebView(ctx).apply {
                setBackgroundColor(Color.TRANSPARENT)
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
            }
        },
        update = { webView ->
            val html = """
                <!DOCTYPE html>
                <html><head>
                <meta name="viewport" content="width=device-width,initial-scale=1.0">
                <style>
                *{margin:0;padding:0}
                body{background:$bgColor;padding:12px;font-family:system-ui}
                .mermaid{display:flex;justify-content:center}
                svg{max-width:100%;height:auto}
                </style>
                <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
                <script>
                mermaid.initialize({startOnLoad:true,theme:'${if (isDark) "dark" else "default"}',securityLevel:'loose'});
                </script>
                </head><body>
                <div class="mermaid">$escapedCode</div>
                </body></html>
            """.trimIndent()
            webView.loadDataWithBaseURL("https://cdn.jsdelivr.net", html, "text/html", "UTF-8", null)
        }
    )
}

// ── Content parsing: split into segments ───────────────────────

private enum class SegmentType { MARKDOWN, MERMAID }
private data class Segment(val type: SegmentType, val content: String)

/**
 * Pre-formats LaTeX to be compatible with JLatexMathPlugin ($$ inline and block)
 * and separates out Mermaid blocks.
 */
private fun parseAndNormalizeContent(content: String): List<Segment> {
    val segments = mutableListOf<Segment>()

    // 1. Extract Mermaid blocks first to prevent corrupting Mermaid syntax
    val mermaidPattern = Regex("""```mermaid\s*\n([\s\S]*?)```""")
    
    data class Match(val start: Int, val end: Int, val content: String)
    val matches = mutableListOf<Match>()

    for (match in mermaidPattern.findAll(content)) {
        matches.add(Match(match.range.first, match.range.last + 1, match.groupValues[1].trim()))
    }
    matches.sortBy { it.start }

    // Helper to normalize LaTeX in Markdown segments
    fun normalizeLatex(text: String): String {
        var res = text
        // Replace inline \(...\)
        res = res.replace(Regex("""\\\(([\s\S]+?)\\\)"""), "\\$\\$$1\\$\\$")
        // Replace block \[...\] (Strictly requires backslash)
        res = res.replace(Regex("""\\\[([\s\S]+?)\\\]"""), "\\$\\$$1\\$\\$")
        // Replace inline $...$ (ensuring we don't accidentally match $$)
        res = res.replace(Regex("""(?<!\$)\$(?!\$)([^\$\n]+?)\$(?!\$)"""), "\\$\\$$1\\$\\$")
        return res
    }

    // 2. Build segments
    var lastIndex = 0
    for (match in matches) {
        if (match.start > lastIndex) {
            val md = content.substring(lastIndex, match.start).trim()
            if (md.isNotBlank()) {
                segments.add(Segment(SegmentType.MARKDOWN, normalizeLatex(md)))
            }
        }
        if (match.content.isNotBlank()) {
            segments.add(Segment(SegmentType.MERMAID, match.content))
        }
        lastIndex = match.end
    }

    if (lastIndex < content.length) {
        val md = content.substring(lastIndex).trim()
        if (md.isNotBlank()) {
            segments.add(Segment(SegmentType.MARKDOWN, normalizeLatex(md)))
        }
    }

    return segments
}

// ── Markwon builder ────────────────────────────────────────────

private fun buildMarkwon(context: Context): Markwon {
    val imageLoader = ImageLoader.Builder(context)
        .components {
            add(SvgDecoder.Factory())
            add(GifDecoder.Factory())
        }
        .crossfade(true)
        .build()

    // JLatexMath requires configuring text size (sp -> px). 15sp is our default body text size.
    val textSizePx = 15f * context.resources.displayMetrics.scaledDensity

    return Markwon.builder(context)
        .usePlugin(TablePlugin.create(context))
        .usePlugin(HtmlPlugin.create())
        .usePlugin(CoilImagesPlugin.create(context, imageLoader))
        .usePlugin(MarkwonInlineParserPlugin.create())
        .usePlugin(JLatexMathPlugin.create(textSizePx) { builder -> 
            builder.inlinesEnabled(true)
        })
        .build()
}
