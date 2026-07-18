package com.aura.mas.ui.components.resource

import org.junit.Assert.assertEquals
import org.junit.Test

class MarkdownRendererTest {

    @Test
    fun testParseAndNormalizeContent_withLatexFormulasContainingBackslashes() {
        val input = """
            Here is some math: \( \alpha + \beta = \gamma \) and also \[ \sum_{i=1}^n i = \frac{n(n+1)}{2} \].
            And inline: ${'$'}x \times y${'$'}.
        """.trimIndent()

        // This would have crashed before with IllegalArgumentException: Illegal group reference
        val segments = parseAndNormalizeContent(input)

        assertEquals(1, segments.size)
        assertEquals(SegmentType.MARKDOWN, segments[0].type)
        
        val expected = """
            Here is some math: ${"$$"} \alpha + \beta = \gamma ${"$$"} and also ${"$$"} \sum_{i=1}^n i = \frac{n(n+1)}{2} ${"$$"}.
            And inline: ${"$$"}x \times y${"$$"}.
        """.trimIndent()
        
        assertEquals(expected, segments[0].content)
    }

    @Test
    fun testParseAndNormalizeContent_withMermaidAndLatex() {
        val input = """
            Before Mermaid: \( a \backslash b \)
            ```mermaid
            graph TD
                A --> B
            ```
            After Mermaid: ${'$'}x \in X${'$'}
        """.trimIndent()

        val segments = parseAndNormalizeContent(input)

        assertEquals(3, segments.size)
        assertEquals(SegmentType.MARKDOWN, segments[0].type)
        assertEquals("Before Mermaid: ${"$$"} a \\backslash b ${"$$"}", segments[0].content.trim())
        
        assertEquals(SegmentType.MERMAID, segments[1].type)
        assertEquals("graph TD\n    A --> B", segments[1].content.trim())
        
        assertEquals(SegmentType.MARKDOWN, segments[2].type)
        assertEquals("After Mermaid: ${"$$"}x \\in X${"$$"}", segments[2].content.trim())
    }
}
