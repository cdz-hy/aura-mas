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
import android.graphics.Typeface
import io.noties.markwon.AbstractMarkwonPlugin
import io.noties.markwon.Markwon
import io.noties.markwon.core.MarkwonTheme
import io.noties.markwon.ext.latex.JLatexMathPlugin
import io.noties.markwon.ext.tables.TablePlugin
import io.noties.markwon.html.HtmlPlugin
import io.noties.markwon.image.coil.CoilImagesPlugin
import io.noties.markwon.inlineparser.MarkwonInlineParserPlugin

/**
 * Production-grade Markdown renderer for Android.
 *
 * Stack:
 * - Markwon 4.6.2 (CommonMark-compliant)
 * - JLatexMathPlugin (LaTeX via native rendering)
 * - CoilImagesPlugin (images: network/SVG/GIF)
 * - TablePlugin (GFM tables)
 * - HtmlPlugin (inline HTML)
 * - MarkwonInlineParserPlugin (enhanced inline parsing)
 * - Mermaid via WebView (diagrams)
 */
@Composable
fun MarkdownRenderer(
    content: String,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val textColor = MaterialTheme.colorScheme.onSurface
    val isDark = isSystemInDarkTheme()

    val segments = remember(content) { parseAndNormalizeContent(content) }

    Column(modifier = modifier) {
        segments.forEach { segment ->
            when (segment.type) {
                SegmentType.MARKDOWN -> {
                    if (segment.content.isNotBlank()) {
                        MarkdownSegment(segment.content, context, textColor, isDark)
                    }
                }
                SegmentType.MERMAID -> {
                    MermaidView(code = segment.content, isDark = isDark)
                }
            }
        }
    }
}

@Composable
private fun MarkdownSegment(
    content: String,
    context: Context,
    textColor: androidx.compose.ui.graphics.Color,
    isDark: Boolean
) {
    val markwon = remember(context, isDark) { buildMarkwon(context, isDark) }
    val spanned = remember(content) {
        try {
            val originalSpanned = markwon.toMarkdown(content)
            val spannable = if (originalSpanned is android.text.Spannable) originalSpanned else android.text.SpannableStringBuilder(originalSpanned)
            // Center-align all drawable / math / image spans (subclasses of ReplacementSpan) vertically
            val replacementSpans = spannable.getSpans(0, spannable.length, android.text.style.ReplacementSpan::class.java)
            for (span in replacementSpans) {
                try {
                    var clazz: Class<*>? = span.javaClass
                    while (clazz != null) {
                        for (fieldName in listOf("mVerticalAlignment", "alignment")) {
                            try {
                                val field = clazz.getDeclaredField(fieldName)
                                field.isAccessible = true
                                field.setInt(span, 2) // 2 = ALIGN_CENTER
                            } catch (_: NoSuchFieldException) {}
                        }
                        clazz = clazz.superclass
                    }
                } catch (_: Exception) {}

                // Horizontally center block-level images/equations (if on a line by itself)
                try {
                    val start = spannable.getSpanStart(span)
                    val end = spannable.getSpanEnd(span)
                    if (start >= 0 && end >= 0) {
                        var lineStart = start
                        while (lineStart > 0 && spannable[lineStart - 1] != '\n') {
                            lineStart--
                        }
                        var lineEnd = end
                        while (lineEnd < spannable.length && spannable[lineEnd] != '\n') {
                            lineEnd++
                        }
                        val lineText = spannable.subSequence(lineStart, lineEnd).toString()
                        val isOnlyImageAndWhitespace = lineText.all { it.isWhitespace() || it == '\uFFFC' }
                        if (isOnlyImageAndWhitespace) {
                            spannable.setSpan(
                                android.text.style.AlignmentSpan.Standard(android.text.Layout.Alignment.ALIGN_CENTER),
                                lineStart,
                                lineEnd,
                                android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                            )
                        }
                    }
                } catch (_: Exception) {}
            }
            spannable
        } catch (_: Exception) { android.text.SpannableString(content) }
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

@Composable
private fun MermaidView(code: String, isDark: Boolean) {
    val bgColor = if (isDark) "#1a1a2e" else "#ffffff"
    val escapedCode = code
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\$")
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

// ── Content parsing ────────────────────────────────────────────

internal enum class SegmentType { MARKDOWN, MERMAID }
internal data class Segment(val type: SegmentType, val content: String)

internal fun parseAndNormalizeContent(content: String): List<Segment> {
    val segments = mutableListOf<Segment>()
    val mermaidPattern = Regex("""```mermaid\s*\n([\s\S]*?)```""")

    data class Match(val start: Int, val end: Int, val content: String)
    val matches = mutableListOf<Match>()
    for (match in mermaidPattern.findAll(content)) {
        matches.add(Match(match.range.first, match.range.last + 1, match.groupValues[1].trim()))
    }
    matches.sortBy { it.start }

    fun normalizeLatex(text: String): String {
        fun Regex.safeReplace(input: CharSequence, transform: (MatchResult) -> String): String {
            val matches = this.findAll(input).toList()
            if (matches.isEmpty()) return input.toString()
            val sb = StringBuilder(input.length)
            var lastStart = 0
            for (match in matches) {
                sb.append(input, lastStart, match.range.first)
                sb.append(transform(match))
                lastStart = match.range.last + 1
            }
            if (lastStart < input.length) {
                sb.append(input, lastStart, input.length)
            }
            return sb.toString()
        }

        var res = text
        res = Regex("""\\\(([\s\S]+?)\\\)""").safeReplace(res) { "\$\$${it.groupValues[1]}\$\$" }
        res = Regex("""\\\[([\s\S]+?)\\\]""").safeReplace(res) { "\$\$${it.groupValues[1]}\$\$" }
        res = Regex("""(?<!\$)\$(?!\$)([^\$\n]+?)\$(?!\$)""").safeReplace(res) { "\$\$${it.groupValues[1]}\$\$" }
        return res
    }

    var lastIndex = 0
    for (match in matches) {
        if (match.start > lastIndex) {
            val md = content.substring(lastIndex, match.start).trim()
            if (md.isNotBlank()) segments.add(Segment(SegmentType.MARKDOWN, normalizeLatex(md)))
        }
        if (match.content.isNotBlank()) segments.add(Segment(SegmentType.MERMAID, match.content))
        lastIndex = match.end
    }
    if (lastIndex < content.length) {
        val md = content.substring(lastIndex).trim()
        if (md.isNotBlank()) segments.add(Segment(SegmentType.MARKDOWN, normalizeLatex(md)))
    }
    if (segments.isEmpty()) segments.add(Segment(SegmentType.MARKDOWN, normalizeLatex(content)))
    return segments
}

// ── Markwon builder ────────────────────────────────────────────

private fun buildMarkwon(context: Context, isDark: Boolean): Markwon {
    val imageLoader = ImageLoader.Builder(context)
        .components {
            add(SvgDecoder.Factory())
            add(GifDecoder.Factory())
        }
        .crossfade(true)
        .build()

    val textSizePx = 15f * context.resources.displayMetrics.scaledDensity

    return Markwon.builder(context)
        .usePlugin(TablePlugin.create(context))
        .usePlugin(HtmlPlugin.create())
        .usePlugin(CoilImagesPlugin.create(context, imageLoader))
        .usePlugin(MarkwonInlineParserPlugin.create())
        .usePlugin(object : AbstractMarkwonPlugin() {
            override fun configureTheme(builder: MarkwonTheme.Builder) {
                builder
                    .codeBlockTypeface(Typeface.MONOSPACE)
                    .codeBlockTextSize((textSizePx * 0.85f).toInt())
                    .codeBlockBackgroundColor(if (isDark) 0xFF1E293B.toInt() else 0xFFF1F5F9.toInt())
                    .codeBlockMargin(16)
                    .codeTypeface(Typeface.MONOSPACE)
                    .codeTextSize((textSizePx * 0.85f).toInt())
                    .codeBackgroundColor(if (isDark) 0xFF334155.toInt() else 0xFFE2E8F0.toInt())
            }
        })
        .usePlugin(JLatexMathPlugin.create(textSizePx) { builder ->
            builder.inlinesEnabled(true)
            builder.theme().blockHorizontalAlignment(ru.noties.jlatexmath.JLatexMathDrawable.ALIGN_CENTER)
        })
        .build()
}
