import { marked } from 'marked'
import katex from 'katex'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true,
})

// 保护 LaTeX 公式不被 marked 解析破坏
// 在 marked 解析前，将 LaTeX 替换为占位符，解析后再还原为 KaTeX HTML
function protectLatex(md: string): { text: string; placeholders: Map<string, string> } {
  const placeholders = new Map<string, string>()
  let counter = 0

  function replacer(match: string): string {
    const key = `%%LATEX_${counter++}%%`
    placeholders.set(key, match)
    return key
  }

  let text = md
  // 保护 $$...$$ 块级公式（不匹配不完整的公式）
  text = text.replace(/\$\$([^$]+?)\$\$/g, replacer)
  // 保护 $...$ 行内公式（不匹配不完整的公式）
  text = text.replace(/(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)/g, replacer)

  return { text, placeholders }
}

// 还原占位符为 KaTeX HTML
function restoreLatex(html: string, placeholders: Map<string, string>): string {
  for (const [key, latex] of Array.from(placeholders.entries())) {
    const isBlock = latex.startsWith('$$')
    const content = isBlock ? latex.slice(2, -2).trim() : latex.slice(1, -1).trim()
    if (!content) continue

    try {
      const rendered = katex.renderToString(content, {
        displayMode: isBlock,
        throwOnError: false,
        trust: true,
      })
      html = html.replace(key, rendered)
    } catch {
      // KaTeX 渲染失败，保留原始文本
      html = html.replace(key, `<code>${content}</code>`)
    }
  }
  return html
}

// 处理流式输出中的不完整 LaTeX（等待更多内容）
function stripIncompleteLatex(md: string): string {
  // 移除不完整的 $$ 块级公式（没有闭合的）
  const blockOpen = md.lastIndexOf('$$')
  if (blockOpen !== -1) {
    const after = md.slice(blockOpen + 2)
    if (!after.includes('$$')) {
      // 不完整的块级公式，截断到 $$ 之前
      md = md.slice(0, blockOpen)
    }
  }

  // 移除不完整的 $ 行内公式（没有闭合的）
  // 从后往前查找未闭合的 $
  let lastDollar = -1
  let inBlock = false
  for (let i = 0; i < md.length; i++) {
    if (md[i] === '$') {
      if (i + 1 < md.length && md[i + 1] === '$') {
        inBlock = !inBlock
        i++ // 跳过第二个 $
        continue
      }
      if (!inBlock) {
        lastDollar = i
      }
    }
  }
  // 如果最后有一个未闭合的行内公式，截断
  if (lastDollar !== -1) {
    const before = md.slice(0, lastDollar)
    const after = md.slice(lastDollar + 1)
    // 检查是否有闭合的 $
    if (!after.includes('$') || after.indexOf('$') === after.lastIndexOf('$')) {
      // 可能不完整，检查是否在公式中间
      const openCount = (before.match(/(?<!\$)\$(?!\$)/g) || []).length
      if (openCount % 2 !== 0) {
        md = md.slice(0, lastDollar)
      }
    }
  }

  return md
}

export function parseMarkdown(md: string): string {
  if (!md) return ''

  // 剥离流式输出中的不完整内容
  let cleaned = stripIncompleteLatex(md)
  // Strip incomplete image markdown during streaming to prevent layout jumps
  cleaned = cleaned.replace(/!\[[^\]]*\]\([^)]*$/, '')

  // 保护 LaTeX 公式
  const { text, placeholders } = protectLatex(cleaned)

  // marked 解析
  let html = marked.parse(text) as string

  // 还原 LaTeX 为 KaTeX HTML
  if (placeholders.size > 0) {
    html = restoreLatex(html, placeholders)
  }

  return html
}

// Extract draggable text segments from rendered HTML
export function extractTextSegments(html: string): Array<{ text: string; position: string }> {
  const segments: Array<{ text: string; position: string }> = []
  const div = document.createElement('div')
  div.innerHTML = html
  const elements = div.querySelectorAll('p, li, h1, h2, h3, h4, blockquote, td')
  elements.forEach((el, i) => {
    const text = el.textContent?.trim()
    if (text && text.length > 5) {
      segments.push({
        text: text.substring(0, 200),
        position: `segment-${i}`,
      })
    }
  })
  return segments
}
