<template>
  <div class="space-y-4">
    <div v-for="(q, i) in partialQuestions" :key="i" class="border border-navy-100 rounded-xl p-4 bg-white/50 animate-pulse">
      <div class="flex gap-2">
        <span class="w-6 h-6 rounded-full bg-navy-100 text-navy-500 text-xs flex items-center justify-center">{{ i + 1 }}</span>
        <p class="text-sm text-navy-800 font-medium">{{ q.question || '正在生成题目...' }}</p>
      </div>
      <div v-if="q.options && q.options.length" class="mt-3 ml-8 space-y-2">
        <div v-for="(opt, oi) in q.options" :key="oi" class="text-xs text-navy-600 p-2 rounded bg-navy-50 border border-navy-100/50">
           {{ 'ABCDE'[oi] || oi + 1 }}. {{ opt }}
        </div>
      </div>
    </div>
    <div v-if="!partialQuestions.length" class="text-sm text-navy-400 p-4 text-center border border-dashed border-navy-200 rounded-xl">
      智能体正在冥思苦想题目内容...
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  rawJson?: string
}>()

const partialQuestions = computed(() => {
  const str = props.rawJson || ''
  if (!str.trim()) return []

  const questionsIndex = str.indexOf('"questions"')
  if (questionsIndex === -1) {
    return []
  }

  const questionsStr = str.substring(questionsIndex)
  const parts = questionsStr.split('{')
  const questions: Array<{question: string, options: string[]}> = []

  for (let i = 1; i < parts.length; i++) {
    const part = parts[i]

    // Extract question text
    const qMatch = part.match(/"question(?:_text)?"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)(?:"|$)/)
    const questionText = qMatch ? qMatch[1] : ''

    // Extract options
    const options: string[] = []
    const optMatch = part.match(/"options"\s*:\s*\[([^\]]*)(?:\]|$)/)
    if (optMatch) {
      const optStr = optMatch[1]
      const optRegex = /"([^"\\]*(?:\\.[^"\\]*)*)"/g
      let m
      while ((m = optRegex.exec(optStr)) !== null) {
        options.push(m[1])
      }
    }

    if (questionText || options.length > 0) {
      questions.push({
        question: questionText,
        options
      })
    }
  }

  return questions
})
</script>
