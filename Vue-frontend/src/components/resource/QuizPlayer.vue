<template>
  <div v-if="!data || !data.questions || data.questions.length === 0" class="text-center py-8 text-navy-400">
    <p>暂无题目数据</p>
  </div>

  <div v-else>
    <!-- Quiz header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h3 class="font-display text-lg font-semibold text-navy-800">{{ data.title || '练习题' }}</h3>
        <p class="text-sm text-navy-400 mt-0.5">共 {{ data.questions.length }} 题 · {{ data.totalPoints || 100 }} 分</p>
      </div>
      <div v-if="!submitted" class="text-sm text-navy-500">
        已答 {{ answeredCount }} / {{ data.questions.length }}
      </div>
      <div v-else class="text-sm font-medium" :class="score >= 80 ? 'text-emerald-600' : score >= 60 ? 'text-amber-600' : 'text-red-500'">
        得分：{{ score }}分
      </div>
    </div>

    <!-- Progress bar -->
    <div class="h-1.5 bg-navy-100 rounded-full mb-6 overflow-hidden">
      <div class="h-full bg-gradient-to-r from-navy-400 to-sage-500 rounded-full transition-all" :style="{ width: `${(answeredCount / data.questions.length) * 100}%` }"></div>
    </div>

    <!-- Questions -->
    <div class="space-y-6">
      <div v-for="(q, qi) in data.questions" :key="qi" class="border border-navy-100/50 rounded-xl p-5 transition-all"
        :class="submitted ? (isCorrect(qi) ? 'border-emerald-200 bg-emerald-50/30' : 'border-red-200 bg-red-50/30') : 'hover:border-navy-200'">
        <!-- Question header -->
        <div class="flex items-start gap-3 mb-4">
          <span class="w-7 h-7 rounded-full text-xs flex items-center justify-center font-bold flex-shrink-0"
            :class="submitted ? (isCorrect(qi) ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white') : 'bg-navy-100 text-navy-600'">
            {{ qi + 1 }}
          </span>
          <div class="flex-1">
            <p class="text-navy-800 font-medium leading-relaxed">{{ q.question }}</p>
            <div class="flex items-center gap-2 mt-1">
              <span class="text-xs px-2 py-0.5 rounded-full bg-navy-50 text-navy-500">{{ typeLabel(q.type) }}</span>
              <span class="text-xs text-navy-300">难度 {{ q.difficulty }}/5</span>
            </div>
          </div>
        </div>

        <!-- Choice options -->
        <div v-if="q.type === 'single_choice' || q.type === 'multiple_choice'" class="space-y-2 ml-10">
          <label v-for="(opt, oi) in q.options" :key="oi"
            class="flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all border"
            :class="optionClass(qi, oi)"
            @click="selectOption(qi, oi)">
            <span class="w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs font-bold flex-shrink-0"
              :class="isSelected(qi, oi) ? 'border-navy-600 bg-navy-600 text-white' : 'border-navy-300 text-navy-400'">
              {{ 'ABCD'[oi] }}
            </span>
            <span class="text-sm text-navy-700">{{ opt }}</span>
          </label>
        </div>

        <!-- True/False -->
        <div v-else-if="q.type === 'true_false'" class="flex gap-3 ml-10">
          <button v-for="val in ['正确', '错误']" :key="val"
            class="flex-1 py-3 rounded-lg text-sm font-medium border transition-all"
            :class="answers[qi] === val ? 'bg-navy-600 text-white border-navy-600' : 'bg-white text-navy-600 border-navy-200 hover:border-navy-400'"
            @click="answers[qi] = val">
            {{ val }}
          </button>
        </div>

        <!-- Fill blank / Short answer / Code -->
        <div v-else class="ml-10">
          <textarea
            v-model="answers[qi]"
            class="input-field min-h-[80px] resize-y font-mono text-sm"
            :placeholder="q.type === 'code_output' ? '输入你认为的代码输出...' : '输入你的答案...'"
          ></textarea>
        </div>

        <!-- Explanation (after submit) -->
        <div v-if="submitted && q.explanation" class="mt-4 ml-10 p-3 rounded-lg bg-navy-50/50 border border-navy-100/50">
          <p class="text-xs font-medium text-navy-500 mb-1">解析</p>
          <p class="text-sm text-navy-600 leading-relaxed">{{ q.explanation }}</p>
        </div>
      </div>
    </div>

    <!-- Submit button -->
    <div class="mt-6 flex justify-center">
      <button v-if="!submitted" class="btn-primary px-10" @click="submitQuiz" :disabled="answeredCount === 0">
        提交答案
      </button>
      <button v-else class="btn-secondary px-10" @click="resetQuiz">
        重新作答
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { QuizData } from '@/types/quiz'
import { QUESTION_TYPE_LABELS } from '@/types/quiz'

const props = defineProps<{ data: QuizData | null }>()
const emit = defineEmits<{ submit: [answers: Record<number, any>] }>()

const answers = ref<Record<number, any>>({})
const submitted = ref(false)
const score = ref(0)

const answeredCount = computed(() => {
  return Object.keys(answers.value).filter(k => {
    const v = answers.value[Number(k)]
    return v !== undefined && v !== '' && (Array.isArray(v) ? v.length > 0 : true)
  }).length
})

function typeLabel(type: string) {
  return QUESTION_TYPE_LABELS[type as keyof typeof QUESTION_TYPE_LABELS] || type
}

function selectOption(qi: number, oi: number) {
  if (submitted.value) return
  const q = props.data?.questions[qi]
  if (!q) return

  if (q.type === 'single_choice') {
    answers.value[qi] = oi
  } else {
    const current: number[] = answers.value[qi] || []
    const idx = current.indexOf(oi)
    if (idx >= 0) {
      current.splice(idx, 1)
    } else {
      current.push(oi)
    }
    answers.value[qi] = [...current]
  }
}

function isSelected(qi: number, oi: number) {
  const v = answers.value[qi]
  if (Array.isArray(v)) return v.includes(oi)
  return v === oi
}

function optionClass(qi: number, oi: number) {
  if (!submitted.value) {
    return isSelected(qi, oi) ? 'border-navy-300 bg-navy-50' : 'border-transparent bg-navy-50/30 hover:bg-navy-50'
  }
  const q = props.data?.questions[qi]
  if (!q) return ''
  const correct = Array.isArray(q.correctAnswer) ? (q.correctAnswer as unknown as number[]).includes(oi) : q.correctAnswer === String(oi)
  if (correct) return 'border-emerald-300 bg-emerald-50'
  if (isSelected(qi, oi)) return 'border-red-300 bg-red-50'
  return 'border-transparent bg-navy-50/30'
}

function isCorrect(qi: number) {
  const q = props.data?.questions[qi]
  if (!q) return false
  const a = answers.value[qi]
  if (q.type === 'single_choice') return String(a) === String(q.correctAnswer)
  if (q.type === 'multiple_choice') {
    const correct = (q.correctAnswer as unknown as number[]).slice().sort()
    const given = ((a as unknown as number[]) || []).slice().sort()
    return JSON.stringify(correct) === JSON.stringify(given)
  }
  if (q.type === 'true_false') return a === q.correctAnswer
  return String(a).trim().toLowerCase() === String(q.correctAnswer).trim().toLowerCase()
}

function submitQuiz() {
  if (!props.data) return
  let correct = 0
  props.data.questions.forEach((_, i) => {
    if (isCorrect(i)) correct++
  })
  score.value = Math.round((correct / props.data!.questions.length) * 100)
  submitted.value = true
  emit('submit', { ...answers.value })
}

function resetQuiz() {
  answers.value = {}
  submitted.value = false
  score.value = 0
}
</script>
