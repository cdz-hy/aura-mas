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
  // 1. 保护 $$...$$ 块级公式
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, replacer)
  // 2. 保护 \[...\] 块级公式
  text = text.replace(/\\\[([\s\S]+?)\\\]/g, replacer)
  // 3. 保护 \(...\) 行内公式
  text = text.replace(/\\\(([\s\S]+?)\\\)/g, replacer)
  // 4. 保护 $...$ 行内公式
  text = text.replace(/(?<!\$)\$(?!\$)([\s\S]+?)(?<!\$)\$(?!\$)/g, replacer)

  return { text, placeholders }
}

// 还原占位符为 KaTeX HTML
function restoreLatex(html: string, placeholders: Map<string, string>): string {
  for (const [key, latex] of Array.from(placeholders.entries())) {
    let isBlock = false
    let content = ''
    if (latex.startsWith('$$')) {
      isBlock = true
      content = latex.slice(2, -2).trim()
    } else if (latex.startsWith('\\[')) {
      isBlock = true
      content = latex.slice(2, -2).trim()
    } else if (latex.startsWith('\\(')) {
      isBlock = false
      content = latex.slice(2, -2).trim()
    } else if (latex.startsWith('$')) {
      isBlock = false
      content = latex.slice(1, -1).trim()
    } else {
      content = latex.trim()
    }

    if (!content) continue

    try {
      const rendered = katex.renderToString(content, {
        displayMode: isBlock,
        throwOnError: false,
        trust: true,
      })
      if (isBlock) {
        // If the block placeholder is wrapped in a paragraph tag by marked, remove the wrapper
        const pRegex = new RegExp(`<p>\\s*${key}\\s*</p>`, 'g')
        if (pRegex.test(html)) {
          html = html.replace(pRegex, rendered)
        } else {
          html = html.replace(key, rendered)
        }
      } else {
        html = html.replace(key, rendered)
      }
    } catch {
      // KaTeX 渲染失败，保留原始文本
      html = html.replace(key, `<code>${content}</code>`)
    }
  }
  return html
}

// 处理流式输出中的不完整 LaTeX（等待更多内容）
function stripIncompleteLatex(md: string): string {
  let i = 0
  const len = md.length

  let lastDoubleDollar = -1
  let lastSingleDollar = -1
  let lastBackslashSquare = -1
  let lastBackslashRound = -1

  let inDoubleDollar = false
  let inSingleDollar = false
  let inBackslashSquare = false
  let inBackslashRound = false

  while (i < len) {
    if (md[i] === '\\') {
      if (i + 1 < len) {
        const next = md[i + 1]
        if (next === '\\') {
          // Escaped backslash, skip both
          i += 2
          continue
        } else if (next === '$') {
          // Escaped dollar, skip both
          i += 2
          continue
        } else if (next === '[') {
          if (!inDoubleDollar && !inSingleDollar && !inBackslashSquare && !inBackslashRound) {
            inBackslashSquare = true
            lastBackslashSquare = i
          }
          i += 2
          continue
        } else if (next === ']') {
          if (inBackslashSquare) {
            inBackslashSquare = false
            lastBackslashSquare = -1
          }
          i += 2
          continue
        } else if (next === '(') {
          if (!inDoubleDollar && !inSingleDollar && !inBackslashSquare && !inBackslashRound) {
            inBackslashRound = true
            lastBackslashRound = i
          }
          i += 2
          continue
        } else if (next === ')') {
          if (inBackslashRound) {
            inBackslashRound = false
            lastBackslashRound = -1
          }
          i += 2
          continue
        }
      }
      i++
      continue
    }

    if (md[i] === '$') {
      if (i + 1 < len && md[i + 1] === '$') {
        if (!inSingleDollar && !inBackslashSquare && !inBackslashRound) {
          if (inDoubleDollar) {
            inDoubleDollar = false
            lastDoubleDollar = -1
          } else {
            inDoubleDollar = true
            lastDoubleDollar = i
          }
        }
        i += 2
        continue
      } else {
        if (!inDoubleDollar && !inBackslashSquare && !inBackslashRound) {
          if (inSingleDollar) {
            inSingleDollar = false
            lastSingleDollar = -1
          } else {
            inSingleDollar = true
            lastSingleDollar = i
          }
        }
        i++
        continue
      }
    }

    i++
  }

  const unclosedIndices = [
    inDoubleDollar ? lastDoubleDollar : -1,
    inSingleDollar ? lastSingleDollar : -1,
    inBackslashSquare ? lastBackslashSquare : -1,
    inBackslashRound ? lastBackslashRound : -1
  ].filter(idx => idx !== -1)

  if (unclosedIndices.length > 0) {
    const truncateIndex = Math.min(...unclosedIndices)
    if (truncateIndex !== -1) {
      return md.substring(0, truncateIndex)
    }
  }

  return md
}

export function parseMarkdown(md: string): string {
  if (!md) return ''

  // 1. 剥离流式输出中的不完整内容
  const cleaned = stripIncompleteLatex(md)
  // Strip incomplete image markdown during streaming to prevent layout jumps
  const cleanedImage = cleaned.replace(/!\[[^\]]*\]\([^)]*$/, '')

  // 2. 保护 LaTeX 公式（公式内部的内容包括 \n、\r、\t 等将保持原样，免受外部替换和 marked 影响）
  const { text, placeholders } = protectLatex(cleanedImage)

  // 3. 兜底处理外围文本的转义字符：将字面 \n（反斜杠+n）转为实际换行
  const fixed = text.replace(/\\n/g, '\n').replace(/\\r/g, '\r').replace(/\\t/g, '\t')

  // 4. marked 解析
  let html = marked.parse(fixed) as string

  // 5. 还原 LaTeX 为 KaTeX HTML
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
