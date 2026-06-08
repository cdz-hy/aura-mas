<template>
  <div class="flashcard-player">
    <!-- Progress bar -->
    <div class="flex items-center justify-between mb-4">
      <span class="text-sm text-navy-400">{{ currentIndex + 1 }} / {{ cards.length }}</span>
      <div class="flex-1 mx-4 h-1.5 bg-navy-100 rounded-full overflow-hidden">
        <div class="h-full bg-navy-500 rounded-full transition-all duration-300" :style="{ width: progressWidth }" />
      </div>
      <button
        class="text-sm text-navy-400 hover:text-navy-600 transition-colors"
        @click="$emit('close')"
      >
        关闭
      </button>
    </div>

    <!-- Card container with 3D flip -->
    <div class="card-scene" @click="flipped = !flipped">
      <div class="card-inner" :class="{ 'is-flipped': flipped }">
        <!-- Front (Question) -->
        <div class="card-face card-front">
          <div class="difficulty-badge" :class="difficultyClass">
            {{ difficultyLabel }}
          </div>
          <div class="card-content">
            <p class="text-lg text-navy-800 leading-relaxed text-center">{{ currentCard.question }}</p>
          </div>
          <p class="text-xs text-navy-300 mt-4">点击翻转查看答案</p>
        </div>
        <!-- Back (Answer) -->
        <div class="card-face card-back">
          <div class="card-content">
            <p class="text-base text-navy-700 leading-relaxed text-center">{{ currentCard.answer }}</p>
          </div>
          <p class="text-xs text-navy-300 mt-4">选择你的掌握程度</p>
        </div>
      </div>
    </div>

    <!-- Review buttons (only visible on back) -->
    <div v-if="flipped" class="flex justify-center gap-3 mt-6">
      <button
        class="review-btn review-btn-hard"
        @click.stop="submitReview(1)"
      >
        忘了
      </button>
      <button
        class="review-btn review-btn-medium"
        @click.stop="submitReview(3)"
      >
        还行
      </button>
      <button
        class="review-btn review-btn-easy"
        @click.stop="submitReview(5)"
      >
        简单
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Flashcard } from '@/types/flashcard'
import { reviewFlashcard } from '@/api/flashcard'

const props = defineProps<{
  cards: Flashcard[]
}>()

const emit = defineEmits<{
  close: []
  reviewed: [cardId: number, quality: number]
}>()

const currentIndex = ref(0)
const flipped = ref(false)

const currentCard = computed(() => {
  const card = props.cards[currentIndex.value]
  return card || { id: 0, question: '', answer: '', difficulty: 1 } as Flashcard
})
const progressWidth = computed(() => `${((currentIndex.value + 1) / props.cards.length) * 100}%`)

const difficultyClass = computed(() => {
  const d = currentCard.value?.difficulty ?? 1
  return d === 1 ? 'diff-easy' : d === 2 ? 'diff-medium' : 'diff-hard'
})

const difficultyLabel = computed(() => {
  const d = currentCard.value?.difficulty ?? 1
  return d === 1 ? '简单' : d === 2 ? '中等' : '困难'
})

async function submitReview(quality: number) {
  const card = currentCard.value
  if (!card) return

  try {
    await reviewFlashcard(card.id, quality)
  } catch (e) {
    console.error('Review failed:', e)
  }

  emit('reviewed', card.id, quality)

  // Move to next card or finish
  if (currentIndex.value < props.cards.length - 1) {
    currentIndex.value++
    flipped.value = false
  } else {
    emit('close')
  }
}
</script>

<style scoped>
.flashcard-player {
  max-width: 480px;
  margin: 0 auto;
}

.card-scene {
  perspective: 800px;
  height: 280px;
  cursor: pointer;
}

.card-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.5s ease;
  transform-style: preserve-3d;
}

.card-inner.is-flipped {
  transform: rotateY(180deg);
}

.card-face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  border-radius: 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.card-front {
  background: white;
  border: 1px solid #e5e7eb;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.card-back {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  transform: rotateY(180deg);
}

.card-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}

.difficulty-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 9999px;
  font-weight: 500;
}

.diff-easy {
  background: #dcfce7;
  color: #166534;
}

.diff-medium {
  background: #fef9c3;
  color: #854d0e;
}

.diff-hard {
  background: #fee2e2;
  color: #991b1b;
}

.review-btn {
  padding: 8px 24px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.review-btn-hard {
  background: #fee2e2;
  color: #991b1b;
  border-color: #fecaca;
}

.review-btn-hard:hover {
  background: #fecaca;
}

.review-btn-medium {
  background: #fef9c3;
  color: #854d0e;
  border-color: #fde68a;
}

.review-btn-medium:hover {
  background: #fde68a;
}

.review-btn-easy {
  background: #dcfce7;
  color: #166534;
  border-color: #bbf7d0;
}

.review-btn-easy:hover {
  background: #bbf7d0;
}
</style>
