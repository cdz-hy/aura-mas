<template>
  <div class="card rounded-2xl p-6">
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-50 to-purple-50 flex items-center justify-center">
          <svg class="w-4 h-4 text-indigo-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2a7 7 0 0 1 7 7c0 2.4-1.2 4.5-3 5.7V17a1 1 0 0 1-1 1h-6a1 1 0 0 1-1-1v-2.3C6.2 13.5 5 11.4 5 9a7 7 0 0 1 7-7z"/>
            <path d="M9 21h6"/><path d="M10 17v4"/><path d="M14 17v4"/>
          </svg>
        </div>
        <h2 class="font-display text-base font-semibold text-navy-800">AI 学习建议</h2>
      </div>
      <button class="text-xs text-navy-400 hover:text-navy-600 transition-colors flex items-center gap-1 disabled:opacity-50"
        :disabled="loading"
        @click="fetchSuggestions">
        <svg v-if="loading" class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 11-6.219-8.56" />
        </svg>
        <svg v-else class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="1 4 1 10 7 10"/><polyline points="23 20 23 14 17 14"/>
          <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
        </svg>
        {{ loading ? '生成中...' : '换一批' }}
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading && suggestions.length === 0" class="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <div v-for="i in 3" :key="i" class="flex items-start gap-3 p-3 rounded-xl bg-navy-50/50 animate-pulse">
        <div class="w-8 h-8 rounded-lg bg-navy-100" />
        <div class="flex-1 space-y-2">
          <div class="h-3 bg-navy-100 rounded w-full" />
          <div class="h-3 bg-navy-100 rounded w-2/3" />
        </div>
      </div>
    </div>

    <!-- Suggestions -->
    <div v-else-if="suggestions.length > 0" class="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <div v-for="(suggestion, i) in suggestions" :key="suggestion.text + i"
        class="flex items-start gap-3 p-3 rounded-xl bg-navy-50/50 animate-fade-in-up"
        :style="{ animationDelay: `${i * 0.1}s` }">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-indigo-50">
          <span class="text-base">{{ suggestion.emoji }}</span>
        </div>
        <div class="min-w-0">
          <p class="text-sm text-navy-700 leading-relaxed">{{ suggestion.text }}</p>
        </div>
      </div>
    </div>

    <!-- Error fallback -->
    <div v-else-if="error" class="text-center py-6">
      <p class="text-sm text-navy-400">{{ error }}</p>
      <button class="text-xs text-indigo-500 hover:text-indigo-600 mt-2" @click="fetchSuggestions">重试</button>
    </div>

    <!-- Initial state -->
    <div v-else class="text-center py-6">
      <p class="text-sm text-navy-400">点击"换一批"获取 AI 学习建议</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { AnalyticsData } from '@/api/analytics'
import { PYTHON_AI_BASE } from '@/api/request'

const props = defineProps<{
  data: AnalyticsData
}>()

interface Suggestion {
  emoji: string
  text: string
}

const suggestions = ref<Suggestion[]>([])
const loading = ref(false)
const error = ref('')

const CACHE_KEY = 'ai_suggestions_cache'

interface CachedSuggestions {
  date: string
  suggestions: Suggestion[]
}

onMounted(() => {
  // 检查缓存，一天只生成一次
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (raw) {
      const cached: CachedSuggestions = JSON.parse(raw)
      const today = new Date().toISOString().slice(0, 10)
      if (cached.date === today && cached.suggestions.length > 0) {
        suggestions.value = cached.suggestions
        return
      }
    }
  } catch {}
  fetchSuggestions()
})

async function fetchSuggestions() {
  if (loading.value) return
  loading.value = true
  error.value = ''

  try {
    const d = props.data
    const response = await fetch(`${PYTHON_AI_BASE}/api/analytics/ai-suggestions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        overview: d.overview || {},
        quiz_analysis: d.quizAnalysis || {},
        heatmap: d.heatmap || {},
        flashcard_stats: d.flashcardStats || {},
        knowledge_mastery: d.knowledgeMastery || {},
        learning_style: {},
      }),
    })

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const reader = response.body?.getReader()
    if (!reader) throw new Error('No reader')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const msg = JSON.parse(line.slice(6))
          if (msg.type === 'done' && msg.content) {
            const parsed = parseSuggestions(msg.content)
            if (parsed.length > 0) {
              suggestions.value = parsed
              // 缓存到 localStorage，一天有效
              try {
                const cache: CachedSuggestions = {
                  date: new Date().toISOString().slice(0, 10),
                  suggestions: parsed,
                }
                localStorage.setItem(CACHE_KEY, JSON.stringify(cache))
              } catch {}
            }
          } else if (msg.type === 'error') {
            throw new Error(msg.content)
          }
        } catch (e) {
          // skip invalid JSON
        }
      }
    }
  } catch (e: any) {
    console.error('AI suggestions failed:', e)
    error.value = '建议生成失败，请确保 Python 后端已启动'
  } finally {
    loading.value = false
  }
}

function parseSuggestions(content: string): Suggestion[] {
  // Try to extract JSON from the response (LLM may wrap it in markdown)
  const jsonMatch = content.match(/\{[\s\S]*\}/)
  if (!jsonMatch) return []

  try {
    const data = JSON.parse(jsonMatch[0])
    const arr = data.suggestions || data
    if (!Array.isArray(arr)) return []

    return arr.slice(0, 3).map((s: any) => ({
      emoji: s.emoji || '💡',
      text: s.text || String(s),
    }))
  } catch {
    return []
  }
}
</script>
