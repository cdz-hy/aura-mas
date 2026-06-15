<template>
  <div ref="container" class="markdown-body"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { parseMarkdown } from '@/utils/markdown'

const props = defineProps<{
  content: string
  streaming?: boolean
}>()

const container = ref<HTMLElement | null>(null)
let mermaidInitialized = false

async function renderMermaidDiagrams() {
  if (!container.value) return
  
  const unrendered = container.value.querySelectorAll('.gv-mermaid-wrapper:not([data-rendered="true"]):not([data-rendering="true"])')
  if (unrendered.length === 0) return

  // Mark them as currently rendering to prevent concurrent async render calls
  unrendered.forEach(el => el.setAttribute('data-rendering', 'true'))

  try {
    const mermaid = (await import('mermaid')).default
    if (!(window as any).__mermaid_initialized__) {
      mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' })
      ;(window as any).__mermaid_initialized__ = true
    }

    for (const el of Array.from(unrendered)) {
      const codeBase64 = el.getAttribute('data-mermaid-code')
      if (!codeBase64) continue

      try {
        const rawCode = decodeURIComponent(codeBase64)
        // 空白字符规范化：处理NBSP/零宽空格等容易导致解析崩溃的字符
        const normalizedCode = rawCode
          .replace(/[\u00A0\u2003\u2002\u2009\u3000]/g, ' ')
          .replace(/[\u200B\u200C\u200D\uFEFF]/g, '')

        // Record what code we are rendering on this element
        el.setAttribute('data-rendering-code', codeBase64)

        const id = 'mermaid-' + Math.random().toString(36).substr(2, 9)
        const { svg } = await mermaid.render(id, normalizedCode)
        
        // Check if the element's code has changed while we were rendering
        if (el.getAttribute('data-mermaid-code') !== codeBase64) {
          continue
        }

        el.innerHTML = svg
        el.setAttribute('data-rendered', 'true')
        el.removeAttribute('data-rendering')
        el.removeAttribute('data-rendering-code')
        el.classList.add('stream-fade-in')
      } catch (err: any) {
        // Only show error if the code hasn't changed in the meantime
        if (el.getAttribute('data-mermaid-code') === codeBase64) {
          console.error('Mermaid rendering error:', err)
          el.innerHTML = `
            <div class="flex flex-col p-4 bg-red-50 rounded-xl border border-red-100">
              <span class="text-sm font-semibold text-red-600 mb-2">⚠️ 图表渲染失败</span>
              <pre class="text-xs text-red-500 overflow-x-auto p-2 bg-white rounded border border-red-50/50">${err.message || String(err)}</pre>
            </div>
          `
          el.setAttribute('data-rendered', 'true')
          el.removeAttribute('data-rendering')
          el.removeAttribute('data-rendering-code')
        }
      }
    }
  } catch (err) {
    console.error('Failed to load Mermaid module:', err)
    // Revert rendering flag so it can retry later if needed
    unrendered.forEach(el => {
      el.removeAttribute('data-rendering')
      el.removeAttribute('data-rendering-code')
    })
  }
}

function updateDOM() {
  if (!container.value) return
  
  // Add a cursor if streaming is active
  const rawHtml = parseMarkdown(props.content + (props.streaming ? '<span class="stream-cursor"></span>' : ''))
  
  if (!props.streaming) {
    container.value.innerHTML = rawHtml
    nextTick(() => {
      renderMermaidDiagrams()
    })
    return
  }

  // Create a temporary element to parse the new HTML
  const temp = document.createElement('div')
  temp.innerHTML = rawHtml

  const oldNodes = Array.from(container.value.childNodes)
  const newNodes = Array.from(temp.childNodes)

  // Shallow diffing to preserve existing nodes and their state/animations
  for (let i = 0; i < newNodes.length; i++) {
    const newNode = newNodes[i] as HTMLElement
    const oldNode = oldNodes[i] as HTMLElement

    if (!oldNode) {
      // New node added
      if (newNode.nodeType === Node.ELEMENT_NODE) {
        newNode.classList.add('stream-fade-in')
      }
      container.value.appendChild(newNode)
    } else {
      // Compare node types and tags
      if (newNode.nodeType === Node.ELEMENT_NODE && oldNode.nodeType === Node.ELEMENT_NODE) {
        if (newNode.outerHTML !== oldNode.outerHTML) {
          if (newNode.tagName === oldNode.tagName) {
            // Special handling for Mermaid wrappers: preserve SVG if code hasn't changed
            if (
              oldNode.classList.contains('gv-mermaid-wrapper') &&
              newNode.classList.contains('gv-mermaid-wrapper') &&
              oldNode.getAttribute('data-mermaid-code') === newNode.getAttribute('data-mermaid-code')
            ) {
              // Code is identical, keep the already rendered SVG and data-rendered attribute
              // Do nothing to oldNode.innerHTML
            } else {
              // Update contents of existing node without replacing it
              oldNode.innerHTML = newNode.innerHTML
              oldNode.className = newNode.className
              if (oldNode.classList.contains('gv-mermaid-wrapper')) {
                oldNode.removeAttribute('data-rendering')
                oldNode.removeAttribute('data-rendered')
                oldNode.removeAttribute('data-rendering-code')
                oldNode.setAttribute('data-mermaid-code', newNode.getAttribute('data-mermaid-code') || '')
              }
            }
          } else {
            // Tag changed, replace the node entirely
            container.value.replaceChild(newNode, oldNode)
          }
        }
      } else {
        // Text nodes or other types
        if (newNode.textContent !== oldNode.textContent) {
          container.value.replaceChild(newNode, oldNode)
        }
      }
    }
  }

  // Remove any leftover old nodes
  while (container.value.childNodes.length > newNodes.length) {
    container.value.removeChild(container.value.lastChild!)
  }

  nextTick(() => {
    renderMermaidDiagrams()
  })
}

watch(() => props.content, updateDOM)
watch(() => props.streaming, updateDOM)

onMounted(updateDOM)
</script>

<style>
/* Global styles because they are injected dynamically into innerHTML */
.stream-cursor {
  display: inline-block;
  width: 6px;
  height: 1.1em;
  background-color: #6366f1; /* indigo-500 */
  vertical-align: middle;
  margin-left: 4px;
  border-radius: 3px;
  animation: pulse-cursor 0.8s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.5);
  position: relative;
  top: -2px;
}

@keyframes pulse-cursor {
  0%, 100% { opacity: 1; transform: scaleY(1); }
  50% { opacity: 0.3; transform: scaleY(0.85); }
}

.stream-fade-in {
  animation: stream-fade-in 0.4s ease-out forwards;
}

@keyframes stream-fade-in {
  0% { opacity: 0; transform: translateY(4px); }
  100% { opacity: 1; transform: translateY(0); }
}
</style>
