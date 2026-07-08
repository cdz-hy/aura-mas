<template>
  <div class="flashcard-review-page">
    <!-- 头部 -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <button
          class="p-2 rounded-lg text-navy-500 hover:bg-navy-100 transition-colors"
          @click="goBack"
        >
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <h1 class="section-title">闪卡复习</h1>
      </div>
      <div v-if="cards.length > 0" class="text-sm text-navy-400">
        共 {{ cards.length }} 张闪卡
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="card p-16 text-center">
      <div class="animate-spin w-8 h-8 border-2 border-navy-300 border-t-transparent rounded-full mx-auto mb-4"></div>
      <p class="text-navy-400">加载闪卡中...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="cards.length === 0" class="card p-16 text-center">
      <svg class="w-16 h-16 mx-auto mb-4 text-navy-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
      </svg>
      <p class="text-navy-400 mb-4">没有待复习的闪卡</p>
      <button class="btn-primary text-sm" @click="goBack">返回笔记</button>
    </div>

    <!-- 闪卡播放器 -->
    <div v-else class="max-w-lg mx-auto">
      <FlashcardPlayer
        :cards="cards"
        @close="goBack"
        @reviewed="onReviewed"
      />
    </div>

    <!-- 复习完成提示 -->
    <transition name="fade">
      <div
        v-if="showComplete"
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        @click="goBack"
      >
        <div class="bg-white rounded-2xl p-8 max-w-sm mx-4 text-center" @click.stop>
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-100 flex items-center justify-center">
            <svg class="w-8 h-8 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-navy-800 mb-2">复习完成!</h3>
          <p class="text-sm text-navy-500 mb-6">
            你已完成 {{ reviewedCount }} 张闪卡的复习
          </p>
          <button class="btn-primary w-full" @click="goBack">返回笔记</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getDueFlashcards, getFlashcardsByNote } from '@/api/flashcard'
import FlashcardPlayer from '@/components/flashcard/FlashcardPlayer.vue'
import type { Flashcard } from '@/types/flashcard'

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const cards = ref<Flashcard[]>([])
const showComplete = ref(false)
const reviewedCount = ref(0)

function goBack() {
  router.push('/notes')
}

function onReviewed(cardId: number, quality: number) {
  reviewedCount.value++
  // 移除已复习的卡片
  cards.value = cards.value.filter(c => c.id !== cardId)

  // 如果所有卡片都复习完了，显示完成提示
  if (cards.value.length === 0) {
    setTimeout(() => {
      showComplete.value = true
    }, 300)
  }
}

async function loadCards() {
  loading.value = true
  try {
    const noteId = route.query.noteId ? Number(route.query.noteId) : null
    const cardId = route.query.cardId ? Number(route.query.cardId) : null

    if (noteId) {
      // 加载特定笔记的闪卡
      const res = await getFlashcardsByNote(noteId)
      cards.value = res.data || []

      // 如果指定了 cardId，将该卡片放在第一位
      if (cardId) {
        const idx = cards.value.findIndex(c => c.id === cardId)
        if (idx > 0) {
          const card = cards.value.splice(idx, 1)[0]
          cards.value.unshift(card)
        }
      }
    } else {
      // 加载所有待复习的闪卡
      const res = await getDueFlashcards(20)
      cards.value = res.data || []
    }
  } catch (e) {
    console.error('Load flashcards failed:', e)
    cards.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadCards)
</script>

<style scoped>
.fade-enter-active {
  transition: opacity 0.3s ease-out;
}

.fade-leave-active {
  transition: opacity 0.2s ease-in;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
