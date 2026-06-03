<template>
  <div ref="container" class="markdown-body"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { parseMarkdown } from '@/utils/markdown'

const props = defineProps<{
  content: string
  streaming?: boolean
}>()

const container = ref<HTMLElement | null>(null)

function updateDOM() {
  if (!container.value) return
  
  // Add a cursor if streaming is active
  const rawHtml = parseMarkdown(props.content + (props.streaming ? '<span class="stream-cursor"></span>' : ''))
  
  if (!props.streaming) {
    container.value.innerHTML = rawHtml
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
            // Update contents of existing node without replacing it
            oldNode.innerHTML = newNode.innerHTML
            oldNode.className = newNode.className
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
