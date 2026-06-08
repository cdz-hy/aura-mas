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

export interface ParsedCitation {
  id: string
  title: string
  url: string
}

export function extractCitations(md: string): ParsedCitation[] {
  if (!md) return []
  const citations: ParsedCitation[] = []
  const seenIds = new Set<string>()

  // 匹配模式如：
  // - [1] 标题 - http://...
  // - [page1] 标题 - http://...
  // - [1] 标题: http://...
  // - [1] 来源: http://...
  const lines = md.split('\n')
  const refRegex = /^\[(\d+|page\d+)\]\s*(.*?)\s*(?:-|:|来源:)\s*(https?:\/\/[^\s\)]+)/i
  const simpleRefRegex = /^\[(\d+|page\d+)\]\s*(https?:\/\/[^\s\)]+)/i
  const colonRefRegex = /^\[(\d+|page\d+)\]:\s*(https?:\/\/[^\s\)]+)/i

  for (const line of lines) {
    const trimmed = line.trim()
    let match = trimmed.match(refRegex)
    if (match) {
      const id = match[1]
      if (!seenIds.has(id)) {
        seenIds.add(id)
        citations.push({
          id,
          title: match[2].trim() || `来源 [${id}]`,
          url: match[3].trim()
        })
      }
      continue
    }

    match = trimmed.match(colonRefRegex) || trimmed.match(simpleRefRegex)
    if (match) {
      const id = match[1]
      if (!seenIds.has(id)) {
        seenIds.add(id)
        citations.push({
          id,
          title: `网页来源 [${id}]`,
          url: match[2].trim()
        })
      }
    }
  }

  // 兜底策略：提取文中所有唯一的 URL，按顺序映射到 [1], [2] 等引用标记（防止大模型没有在末尾写引用列表）
  const urlRegex = /(?<!["'])(https?:\/\/[^\s\)\u4e00-\u9fa5]+)/g
  let matchUrl
  let counter = 1
  while ((matchUrl = urlRegex.exec(md)) !== null) {
    const url = matchUrl[1].trim()
    // 过滤掉 markdown 图片语法中的 URL
    const idx = md.lastIndexOf('![', matchUrl.index)
    if (idx !== -1 && md.indexOf(')', idx) > matchUrl.index) {
      continue
    }
    const id = String(counter)
    if (!seenIds.has(id)) {
      // 避免把已解析到的参考列表中的 URL 当作独立引用
      const isAlreadyListed = citations.some(c => c.url === url)
      if (!isAlreadyListed) {
        seenIds.add(id)
        citations.push({
          id,
          title: `参考链接 [${id}]`,
          url
        })
        counter++
      }
    }
  }

  return citations
}

export function parseMarkdown(md: string): string {
  if (!md) return ''

  // 1. 剥离流式输出中的不完整内容
  const cleaned = stripIncompleteLatex(md)
  // Strip incomplete image markdown during streaming to prevent layout jumps
  const cleanedImage = cleaned.replace(/!\[[^\]]*\]\([^)]*$/, '')

  // 2. 提取文中所有的引用链接，生成引用字典
  const citations = extractCitations(cleanedImage)
  const citMap = new Map<string, { url: string; title: string }>()
  citations.forEach(c => citMap.set(c.id, { url: c.url, title: c.title }))

  // 3. 保护 LaTeX 公式（公式内部的内容包括 \n、\r、\t 等将保持原样，免受外部替换和 marked 影响）
  const { text, placeholders } = protectLatex(cleanedImage)

  // 4. 兜底处理外围文本的转义字符：将字面 \n（反斜杠+n）转为实际换行
  let fixed = text.replace(/\\n/g, '\n').replace(/\\r/g, '\r').replace(/\\t/g, '\t')

  // 5. 替换正文中的引用标识 [1]、[page1] 为交互式的 HTML Span
  // 仅匹配不在感叹号后面、且不紧跟 ( 的引用标识，防止破坏图片和正常 markdown 链接
  const citationPattern = /\[(\d+|page\d+)\](?!\()/g
  fixed = fixed.replace(citationPattern, (match, id) => {
    const cit = citMap.get(id)
    const url = cit ? cit.url : ''
    const title = cit ? cit.title : `网页来源 [${id}]`
    const displayText = id.startsWith('page') ? `p${id.replace('page', '')}` : id
    return `<span class="citation-ref inline-flex items-center justify-center bg-navy-50/50 hover:bg-purple-50 text-navy-500 hover:text-purple-600 border border-navy-100/20 hover:border-purple-200/30 text-[9px] font-sans font-semibold rounded-full min-w-[14px] h-3.5 px-0.5 select-none cursor-pointer relative -top-[0.3em] mx-0.5 transition-all duration-200" data-ref="${id}" data-url="${url}" data-title="${title}">${displayText}</span>`
  })

  // 6. marked 解析
  let html = marked.parse(fixed) as string

  // 7. 还原 LaTeX 为 KaTeX HTML
  if (placeholders.size > 0) {
    html = restoreLatex(html, placeholders)
  }

  // 8. 处理图片：防防盗链 + 加载失败降级
  html = html.replace(/<img\s/g, '<img referrerpolicy="no-referrer" loading="lazy" ')
  html = html.replace(/<img([^>]*?)>/g, (match, attrs) => {
    // 如果已经有 onerror 就不重复添加
    if (attrs.includes('onerror')) return match
    return `<img${attrs} onerror="this.onerror=null;this.style.display='none';this.insertAdjacentHTML('afterend','<span style=\\'color:#999;font-size:12px\\'>[图片加载失败]</span>');">`
  })

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
