<template>
  <div v-if="!data || !data.questions || data.questions.length === 0" class="text-center py-8 text-navy-400">
    <p>暂无题目数据</p>
  </div>

  <div v-else>
    <!-- Quiz header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h3 class="font-display text-lg font-semibold text-navy-800">{{ data.title || '练习题' }}</h3>
        <p class="text-sm text-navy-400 mt-0.5">共 {{ data.questions.length }} 题</p>
      </div>
      <div v-if="grading" class="text-sm text-amber-500 animate-pulse">
        批改中...
      </div>
      <div v-else-if="!submitted" class="text-sm text-navy-500">
        已答 {{ answeredCount }} / {{ data.questions.length }}
      </div>
      <div v-else class="text-sm font-medium" :class="(resultScore ?? 0) >= 80 ? 'text-emerald-600' : (resultScore ?? 0) >= 60 ? 'text-amber-600' : 'text-red-500'">
        {{ resultScore != null ? resultScore + '分' : '已提交' }}
      </div>
    </div>

    <!-- Progress bar -->
    <div class="h-1.5 bg-navy-100 rounded-full mb-6 overflow-hidden">
      <div class="h-full bg-gradient-to-r from-navy-400 to-sage-500 rounded-full transition-all" :style="{ width: `${(answeredCount / data.questions.length) * 100}%` }"></div>
    </div>

    <!-- Questions -->
    <div class="space-y-6">
      <div v-for="(q, qi) in data.questions" :key="qi" class="border border-navy-100/50 rounded-xl p-5 transition-all"
        :class="questionBorderClass(qi)">
        <!-- Question header -->
        <div class="flex items-start gap-3 mb-4">
          <span class="w-7 h-7 rounded-full text-xs flex items-center justify-center font-bold flex-shrink-0"
            :class="questionBadgeClass(qi)">
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
              {{ 'ABCDE'[oi] || oi + 1 }}
            </span>
            <span class="text-sm text-navy-700">{{ opt }}</span>
          </label>
        </div>

        <!-- True/False -->
        <div v-else-if="q.type === 'true_false'" class="flex gap-3 ml-10">
          <button v-for="(val, vi) in ['正确', '错误']" :key="val"
            class="flex-1 py-3 rounded-lg text-sm font-medium border transition-all"
            :class="submitted
              ? (isOptionCorrect(qi, vi) ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : answers[qi] === val ? 'bg-red-50 text-red-700 border-red-300' : 'bg-white text-navy-400 border-navy-200')
              : (answers[qi] === val ? 'bg-navy-600 text-white border-navy-600' : 'bg-white text-navy-600 border-navy-200 hover:border-navy-400')"
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

// 将 correctAnswer 解析为选项索引数组（统一处理各种格式）
function getCorrectIndices(q: { type: string; correctAnswer: string | string[]; options?: string[] }): number[] {
  const raw = q.correctAnswer
  const opts = q.options || []

  // 辅助：去除选项文本的 "A. " 前缀
  const stripPrefix = (text: string) => text.replace(/^[A-Ea-e][\.\)）]\s*/, '').trim()

  // 将单个值解析为选项索引（0-based）
  function resolveOne(val: string): number {
    const v = val.trim()
    if (!v) return -1
    // 字母 A->0, B->1, C->2, D->3, E->4
    const upper = v.toUpperCase()
    if (v.length <= 2 && /^[A-E]$/.test(upper)) return upper.charCodeAt(0) - 65
    // 数字索引
    if (/^\d+$/.test(v)) { const n = parseInt(v); return n < opts.length ? n : -1 }
    // 文本匹配（精确）
    for (let i = 0; i < opts.length; i++) {
      if (stripPrefix(opts[i]) === stripPrefix(v) || opts[i].trim() === v) return i
    }
    // 文本匹配（模糊）
    for (let i = 0; i < opts.length; i++) {
      const opt = stripPrefix(opts[i])
      if (opt.includes(stripPrefix(v)) || stripPrefix(v).includes(opt)) return i
    }
    return -1
  }

  // 将多值字符串解析为索引数组
  function resolveMulti(s: string): number[] {
    // 逗号分隔（"A,D"、"A, D"、"选项1,选项3"、"0,2"）
    if (s.includes(',') || s.includes('，')) {
      const parts = s.split(/[,，]/).map(p => p.trim()).filter(Boolean)
      return parts.map(p => resolveOne(p)).filter(n => n >= 0)
    }
    const idx = resolveOne(s)
    return idx >= 0 ? [idx] : []
  }

  if (q.type === 'true_false') {
    const trueVals = [true, 'true', '正确', 'A', 'a', '1']
    return trueVals.includes(raw) ? [0] : [1] // 0=正确, 1=错误
  }

  // 数组直接处理
  if (Array.isArray(raw)) {
    return raw.map(v => typeof v === 'number' ? v : resolveOne(String(v))).filter(n => n >= 0)
  }

  const s = String(raw).trim()
  if (!s) return []

  // Python 列表表示 "['A','C']" 或 JSON 数组 '["A","C"]'
  if (s.startsWith('[') && s.endsWith(']')) {
    try {
      const arr = JSON.parse(s)
      if (Array.isArray(arr)) {
        return arr.map(v => typeof v === 'number' ? v : resolveOne(String(v))).filter(n => n >= 0)
      }
    } catch {
      // Python 格式: 单引号，去掉方括号后解析
      const inner = s.slice(1, -1).replace(/'/g, '').replace(/"/g, '')
      return resolveMulti(inner)
    }
  }

  return resolveMulti(s)
}

// 选项是否为正确答案
function isOptionCorrect(qi: number, oi: number): boolean {
  const q = props.data?.questions[qi]
  if (!q) return false
  return getCorrectIndices(q).includes(oi)
}

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
  if (isOptionCorrect(qi, oi)) return 'border-emerald-300 bg-emerald-50'
  if (isSelected(qi, oi)) return 'border-red-300 bg-red-50'
  return 'border-transparent bg-navy-50/30'
}

// 是否为可自动判分的题型（选择题、判断题）
function isAutoGradable(qi: number) {
  const t = props.data?.questions[qi]?.type
  return t === 'single_choice' || t === 'multiple_choice' || t === 'true_false'
}

// 题目序号颜色：选择题/判断题提交后立刻显示；其它题型等批改结果
function questionBadgeClass(qi: number) {
  if (!submitted.value) return 'bg-navy-100 text-navy-600'
  if (isAutoGradable(qi)) {
    return isCorrect(qi) ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
  }
  // 需要 AI 批改的题型
  if (props.questionResults?.[qi]) {
    return props.questionResults[qi].is_correct ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
  }
  return 'bg-navy-100 text-navy-600' // 结果未出，保持原色
}

// 题目边框颜色
function questionBorderClass(qi: number) {
  if (!submitted.value) return 'hover:border-navy-200'
  if (isAutoGradable(qi)) {
    return isCorrect(qi) ? 'border-emerald-200 bg-emerald-50/30' : 'border-red-200 bg-red-50/30'
  }
  if (props.questionResults?.[qi]) {
    return props.questionResults[qi].is_correct ? 'border-emerald-200 bg-emerald-50/30' : 'border-red-200 bg-red-50/30'
  }
  return 'border-navy-100/50' // 结果未出，保持原色
}

function isCorrect(qi: number) {
  const q = props.data?.questions[qi]
  if (!q) return false
  const a = answers.value[qi]
  const hasAnswer = a !== undefined && a !== '' && !(Array.isArray(a) && a.length === 0)
  if (!hasAnswer) return false
  if (q.correctAnswer == null || q.correctAnswer === '') return false

  const correctIndices = getCorrectIndices(q)

  if (q.type === 'single_choice') {
    return correctIndices.includes(a as number)
  }
  if (q.type === 'multiple_choice') {
    const given = ((a as unknown as number[]) || []).slice().sort()
    return JSON.stringify(correctIndices.slice().sort()) === JSON.stringify(given)
  }
  if (q.type === 'true_false') {
    const trueVals = [true, 'true', '正确', 'A', 'a', '1']
    const correctVal = trueVals.includes(q.correctAnswer) ? '正确' : '错误'
    return a === correctVal
  }
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
