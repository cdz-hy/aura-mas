<template>
  <div v-if="!data || !data.questions || data.questions.length === 0" class="text-center py-8 text-navy-400">
    <p>暂无题目数据</p>
  </div>

  <div v-else>
    <!-- Quiz header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h3 class="font-display text-lg font-semibold text-navy-800">{{ data.title || '练习题' }}</h3>
        <p class="text-sm text-navy-400 mt-0.5">共 {{ data.questions.length }} 题 · 每题 1 分</p>
      </div>
      <div v-if="grading" class="text-sm text-amber-500 animate-pulse">
        批改中...
      </div>
      <div v-else-if="!submitted" class="text-sm text-navy-500">
        已答 {{ answeredCount }} / {{ data.questions.length }}
      </div>
      <div v-else class="text-sm font-medium" :class="(displayScore ?? 0) >= (data.questions.length * 0.8) ? 'text-emerald-600' : (displayScore ?? 0) >= (data.questions.length * 0.6) ? 'text-amber-600' : 'text-red-500'">
        {{ displayScore ?? '—' }} / {{ data.questions.length }} 正确
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

        <!-- 批改结果（每题内联显示） -->
        <div v-if="submitted && questionResults?.[qi]" class="mt-3 ml-10 space-y-2">
          <!-- 批改反馈 -->
          <div class="p-2 rounded-lg text-xs" :class="questionResults[qi].is_correct ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'">
            <p :class="questionResults[qi].is_correct ? 'text-emerald-700' : 'text-red-700'">
              {{ questionResults[qi].feedback || (questionResults[qi].is_correct ? '回答正确' : '回答错误') }}
            </p>
          </div>
          <!-- 展开详情按钮 -->
          <button class="text-xs text-navy-400 hover:text-navy-600 transition-colors"
            @click="toggleDetail(qi)">
            {{ expandedDetails.has(qi) ? '收起详情 ▲' : '查看详情 ▼' }}
          </button>
          <!-- 展开的详情 -->
          <div v-if="expandedDetails.has(qi)" class="space-y-2">
            <div v-if="q.explanation" class="p-2 rounded-lg bg-navy-50/50 border border-navy-100/50">
              <p class="text-xs font-medium text-navy-500 mb-0.5">解析</p>
              <p class="text-xs text-navy-600 leading-relaxed">{{ q.explanation }}</p>
            </div>
            <div v-if="questionResults[qi].key_points_hit?.length" class="p-2 rounded-lg bg-emerald-50/50 border border-emerald-100/50">
              <p class="text-xs font-medium text-emerald-600 mb-0.5">命中的知识点</p>
              <div class="flex flex-wrap gap-1">
                <span v-for="p in questionResults[qi].key_points_hit" :key="p" class="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-600">{{ p }}</span>
              </div>
            </div>
            <div v-if="questionResults[qi].key_points_missed?.length" class="p-2 rounded-lg bg-red-50/50 border border-red-100/50">
              <p class="text-xs font-medium text-red-500 mb-0.5">遗漏的知识点</p>
              <div class="flex flex-wrap gap-1">
                <span v-for="p in questionResults[qi].key_points_missed" :key="p" class="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-500">{{ p }}</span>
              </div>
            </div>
            <div v-if="questionResults[qi].improvement_suggestions?.length" class="p-2 rounded-lg bg-amber-50/50 border border-amber-100/50">
              <p class="text-xs font-medium text-amber-600 mb-0.5">改进建议</p>
              <ul class="text-xs text-navy-500 space-y-0.5">
                <li v-for="(s, si) in questionResults[qi].improvement_suggestions" :key="si">{{ s }}</li>
              </ul>
            </div>
          </div>
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
import { ref, computed, watch } from 'vue'
import type { QuizData } from '@/types/quiz'
import { QUESTION_TYPE_LABELS } from '@/types/quiz'

const props = defineProps<{
  data: QuizData | null
  initialAnswers?: Record<number, any>
  initialSubmitted?: boolean
  grading?: boolean
  resultScore?: number | null
  questionResults?: Record<number, any> | null
}>()
const emit = defineEmits<{
  submit: [answers: Record<number, any>]
  retake: []
}>()

const answers = ref<Record<number, any>>({})
const submitted = ref(false)
const expandedDetails = ref<Set<number>>(new Set())

// 显示分数：优先使用后端批改结果，否则本地计算
const displayScore = computed(() => {
  if (props.resultScore != null) return props.resultScore
  if (!submitted.value || !props.data) return null
  let correct = 0
  props.data.questions.forEach((_, i) => {
    if (isCorrect(i)) correct++
  })
  return correct
})

// 当外部传入历史答案时，自动恢复已提交状态
function applyInitial() {
  if (props.initialSubmitted && props.initialAnswers) {
    answers.value = { ...props.initialAnswers }
    submitted.value = true
  }
}

// 仅在 data 变化时（切换题目资源）应用初始状态，避免与本地 reset 冲突
watch(() => props.data, () => {
  if (props.initialSubmitted && props.initialAnswers) {
    applyInitial()
  } else {
    answers.value = {}
    submitted.value = false
  }
}, { immediate: true })

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
  let correct = false
  if (Array.isArray(q.correctAnswer)) {
    correct = (q.correctAnswer as unknown as number[]).includes(oi)
  } else {
    const s = String(q.correctAnswer).trim()
    // "A,C" 格式: 将选项索引转为字母比对
    const letter = 'ABCDE'[oi]
    if (/^[A-E](,[A-E])*$/.test(s)) {
      correct = s.split(',').map(c => c.trim()).includes(letter)
    } else {
      correct = s === String(oi)
    }
  }
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
    // correctAnswer 可能是数组 [0,2] 或字符串 "A,C" / "0,2"
    let correct: number[] = []
    if (Array.isArray(q.correctAnswer)) {
      correct = (q.correctAnswer as unknown as number[]).slice().sort()
    } else {
      const s = String(q.correctAnswer).trim()
      // "A,C" 格式 -> 索引
      if (/^[A-E](,[A-E])*$/.test(s)) {
        correct = s.split(',').map(c => ' ABCDE'.indexOf(c.trim())).sort()
      } else {
        correct = s.split(',').map(c => parseInt(c.trim())).filter(n => !isNaN(n)).sort()
      }
    }
    const given = ((a as unknown as number[]) || []).slice().sort()
    return JSON.stringify(correct) === JSON.stringify(given)
  }
  if (q.type === 'true_false') return a === q.correctAnswer
  return String(a).trim().toLowerCase() === String(q.correctAnswer).trim().toLowerCase()
}

function submitQuiz() {
  if (!props.data) return
  submitted.value = true
  emit('submit', { ...answers.value })
}

function toggleDetail(qi: number) {
  const s = new Set(expandedDetails.value)
  if (s.has(qi)) s.delete(qi)
  else s.add(qi)
  expandedDetails.value = s
}

function resetQuiz() {
  answers.value = {}
  submitted.value = false
  expandedDetails.value = new Set()
  emit('retake')
}
</script>
