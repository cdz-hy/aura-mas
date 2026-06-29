<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="section-title">我的学习画像</h1>
      <div class="flex items-center gap-2">
        <template v-if="!editing">
          <button @click="startEdit" class="btn-secondary text-sm">
            编辑画像
          </button>
        </template>
        <template v-else>
          <button @click="cancelEdit" class="btn-secondary text-sm">取消</button>
          <button @click="saveEdit" class="btn-primary text-sm" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </template>
        <router-link to="/plan/create" class="btn-secondary text-sm">
          更新画像
        </router-link>
      </div>
    </div>

    <!-- Toast -->
    <transition name="fade">
      <div v-if="toast" class="fixed top-6 right-6 z-50 px-4 py-2.5 rounded-xl text-sm font-medium shadow-lg"
        :class="toast.type === 'success' ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'">
        {{ toast.message }}
      </div>
    </transition>

    <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <!-- Radar chart - left column -->
      <div class="lg:col-span-2 card p-6 animate-fade-in-up">
        <h2 class="font-display text-lg font-semibold text-navy-800 mb-4">Felder-Silverman 学习风格</h2>
        <div class="aspect-square max-w-sm mx-auto">
          <ProfileRadar :dimensions="dimensions" />
        </div>
      </div>

      <!-- Dimension details - right column -->
      <div class="lg:col-span-3 space-y-4 animate-fade-in-up" style="animation-delay: 0.1s">
        <!-- Felder-Silverman axes -->
        <div class="card p-5">
          <h3 class="font-display font-semibold text-navy-800 mb-4">学习风格维度</h3>
          <div class="space-y-5">
            <div v-for="axis in felderAxes" :key="axis.key">
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-sm font-medium text-navy-700">{{ axis.label }}</span>
                <span class="text-xs px-2 py-0.5 rounded-full"
                  :class="Math.abs(dimensions[axis.key] ?? 0) >= 0.2 ? 'bg-sage-100 text-sage-700' : 'bg-navy-50 text-navy-400'">
                  {{ felderAxisLabel(axis.key, dimensions[axis.key] ?? 0) }}
                </span>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-xs text-navy-400 w-12 text-right">{{ axis.negLabel }}</span>
                <div class="flex-1 relative">
                  <!-- Display bar (always visible) -->
                  <div class="h-2.5 bg-navy-100 rounded-full relative">
                    <div class="absolute top-0 h-full rounded-full transition-all duration-500"
                      :class="(dimensions[axis.key] ?? 0) >= 0 ? 'bg-blue-400' : 'bg-amber-400'"
                      :style="barStyle(dimensions[axis.key] ?? 0)">
                    </div>
                    <div class="absolute top-0 left-1/2 w-0.5 h-full bg-navy-300/30"></div>
                  </div>
                  <!-- Slider (edit mode only) -->
                  <input v-if="editing" type="range" min="-100" max="100" step="5"
                    :value="Math.round((dimensions[axis.key] ?? 0) * 100)"
                    @input="onSliderChange(axis.key, $event)"
                    class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                </div>
                <span class="text-xs text-navy-400 w-12">{{ axis.posLabel }}</span>
              </div>
              <!-- Slider value indicator (edit mode) -->
              <div v-if="editing" class="flex justify-center mt-1">
                <span class="text-xs text-navy-400 tabular-nums">
                  {{ Math.round((dimensions[axis.key] ?? 0) * 100) }}%
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Auxiliary dimensions -->
        <div class="card p-5">
          <h3 class="font-display font-semibold text-navy-800 mb-4">辅助维度</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <!-- Knowledge base -->
            <div class="p-3 rounded-lg bg-navy-50/50 border border-navy-100/50">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-navy-700">知识基础</span>
                <span class="text-xs px-2 py-0.5 rounded-full"
                  :class="(dimensions.knowledge_base?.length) ? 'bg-sage-100 text-sage-700' : 'bg-navy-50 text-navy-400'">
                  {{ dimensions.knowledge_base?.length ? '已完善' : '待完善' }}
                </span>
              </div>
              <div v-if="editing" class="space-y-2">
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="(tag, i) in (dimensions.knowledge_base || [])" :key="i"
                    class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-navy-100 text-navy-600">
                    {{ tag }}
                    <button @click="removeTag('knowledge_base', i)" class="ml-0.5 text-navy-400 hover:text-red-500 transition-colors">&times;</button>
                  </span>
                </div>
                <div class="flex gap-1.5">
                  <input v-model="newTags.knowledge_base" @keyup.enter="addTag('knowledge_base')"
                    class="flex-1 text-xs px-2 py-1 rounded-md border border-navy-200 bg-white focus:outline-none focus:border-navy-400"
                    placeholder="输入后回车添加" />
                  <button @click="addTag('knowledge_base')" class="text-xs px-2 py-1 rounded-md bg-navy-100 text-navy-600 hover:bg-navy-200">+</button>
                </div>
              </div>
              <p v-else class="text-xs text-navy-500 leading-relaxed">
                {{ dimensions.knowledge_base?.length ? dimensions.knowledge_base.join('、') : '暂未收集' }}
              </p>
            </div>

            <!-- Interest tags -->
            <div class="p-3 rounded-lg bg-navy-50/50 border border-navy-100/50">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-navy-700">兴趣标签</span>
                <span class="text-xs px-2 py-0.5 rounded-full"
                  :class="(dimensions.interest_tags?.length) ? 'bg-sage-100 text-sage-700' : 'bg-navy-50 text-navy-400'">
                  {{ dimensions.interest_tags?.length ? '已完善' : '待完善' }}
                </span>
              </div>
              <div v-if="editing" class="space-y-2">
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="(tag, i) in (dimensions.interest_tags || [])" :key="i"
                    class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-navy-100 text-navy-600">
                    {{ tag }}
                    <button @click="removeTag('interest_tags', i)" class="ml-0.5 text-navy-400 hover:text-red-500 transition-colors">&times;</button>
                  </span>
                </div>
                <div class="flex gap-1.5">
                  <input v-model="newTags.interest_tags" @keyup.enter="addTag('interest_tags')"
                    class="flex-1 text-xs px-2 py-1 rounded-md border border-navy-200 bg-white focus:outline-none focus:border-navy-400"
                    placeholder="输入后回车添加" />
                  <button @click="addTag('interest_tags')" class="text-xs px-2 py-1 rounded-md bg-navy-100 text-navy-600 hover:bg-navy-200">+</button>
                </div>
              </div>
              <p v-else class="text-xs text-navy-500 leading-relaxed">
                {{ dimensions.interest_tags?.length ? dimensions.interest_tags.join('、') : '暂未收集' }}
              </p>
            </div>

            <!-- Goal orientation -->
            <div class="p-3 rounded-lg bg-navy-50/50 border border-navy-100/50">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-navy-700">目标导向</span>
                <span class="text-xs px-2 py-0.5 rounded-full"
                  :class="dimensions.goal_orientation ? 'bg-sage-100 text-sage-700' : 'bg-navy-50 text-navy-400'">
                  {{ dimensions.goal_orientation ? '已完善' : '待完善' }}
                </span>
              </div>
              <select v-if="editing" v-model="dimensions.goal_orientation"
                class="w-full text-xs px-2 py-1.5 rounded-md border border-navy-200 bg-white focus:outline-none focus:border-navy-400">
                <option value="">未选择</option>
                <option v-for="(label, key) in GOAL_ORIENTATION_LABELS" :key="key" :value="key">{{ label }}</option>
              </select>
              <p v-else class="text-xs text-navy-500 leading-relaxed">
                {{ GOAL_ORIENTATION_LABELS[dimensions.goal_orientation] || '暂未收集' }}
              </p>
            </div>

            <!-- Weak areas -->
            <div class="p-3 rounded-lg bg-navy-50/50 border border-navy-100/50">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-navy-700">薄弱环节</span>
                <span class="text-xs px-2 py-0.5 rounded-full"
                  :class="(dimensions.weak_areas?.length) ? 'bg-sage-100 text-sage-700' : 'bg-navy-50 text-navy-400'">
                  {{ dimensions.weak_areas?.length ? '已完善' : '待完善' }}
                </span>
              </div>
              <div v-if="editing" class="space-y-2">
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="(tag, i) in (dimensions.weak_areas || [])" :key="i"
                    class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-navy-100 text-navy-600">
                    {{ tag }}
                    <button @click="removeTag('weak_areas', i)" class="ml-0.5 text-navy-400 hover:text-red-500 transition-colors">&times;</button>
                  </span>
                </div>
                <div class="flex gap-1.5">
                  <input v-model="newTags.weak_areas" @keyup.enter="addTag('weak_areas')"
                    class="flex-1 text-xs px-2 py-1 rounded-md border border-navy-200 bg-white focus:outline-none focus:border-navy-400"
                    placeholder="输入后回车添加" />
                  <button @click="addTag('weak_areas')" class="text-xs px-2 py-1 rounded-md bg-navy-100 text-navy-600 hover:bg-navy-200">+</button>
                </div>
              </div>
              <p v-else class="text-xs text-navy-500 leading-relaxed">
                {{ dimensions.weak_areas?.length ? dimensions.weak_areas.join('、') : '暂未收集' }}
              </p>
            </div>

            <!-- Preferred resource types -->
            <div class="p-3 rounded-lg bg-navy-50/50 border border-navy-100/50">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-navy-700">偏好资源</span>
                <span class="text-xs px-2 py-0.5 rounded-full"
                  :class="(dimensions.preferred_resource_types?.length) ? 'bg-sage-100 text-sage-700' : 'bg-navy-50 text-navy-400'">
                  {{ dimensions.preferred_resource_types?.length ? '已完善' : '待完善' }}
                </span>
              </div>
              <div v-if="editing" class="space-y-2">
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="(tag, i) in (dimensions.preferred_resource_types || [])" :key="i"
                    class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-navy-100 text-navy-600">
                    {{ tag }}
                    <button @click="removeTag('preferred_resource_types', i)" class="ml-0.5 text-navy-400 hover:text-red-500 transition-colors">&times;</button>
                  </span>
                </div>
                <div class="flex gap-1.5">
                  <input v-model="newTags.preferred_resource_types" @keyup.enter="addTag('preferred_resource_types')"
                    class="flex-1 text-xs px-2 py-1 rounded-md border border-navy-200 bg-white focus:outline-none focus:border-navy-400"
                    placeholder="输入后回车添加" />
                  <button @click="addTag('preferred_resource_types')" class="text-xs px-2 py-1 rounded-md bg-navy-100 text-navy-600 hover:bg-navy-200">+</button>
                </div>
              </div>
              <p v-else class="text-xs text-navy-500 leading-relaxed">
                {{ dimensions.preferred_resource_types?.length ? dimensions.preferred_resource_types.join('、') : '暂未收集' }}
              </p>
            </div>

            <!-- Quiz preference -->
            <div class="p-3 rounded-lg bg-navy-50/50 border border-navy-100/50">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-navy-700">偏好题目配置</span>
                <span class="text-xs px-2 py-0.5 rounded-full"
                  :class="quizPrefFilled ? 'bg-sage-100 text-sage-700' : 'bg-navy-50 text-navy-400'">
                  {{ quizPrefFilled ? '已完善' : '待完善' }}
                </span>
              </div>
              <div v-if="editing" class="space-y-2">
                <!-- Types -->
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="(tag, i) in (dimensions.preferred_quiz_preference?.types || [])" :key="i"
                    class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-navy-100 text-navy-600">
                    {{ tag }}
                    <button @click="removeQuizType(i)" class="ml-0.5 text-navy-400 hover:text-red-500 transition-colors">&times;</button>
                  </span>
                </div>
                <div class="flex gap-1.5">
                  <input v-model="newQuizType" @keyup.enter="addQuizType"
                    class="flex-1 text-xs px-2 py-1 rounded-md border border-navy-200 bg-white focus:outline-none focus:border-navy-400"
                    placeholder="题型: 单选/多选/判断/填空/简答" />
                  <button @click="addQuizType" class="text-xs px-2 py-1 rounded-md bg-navy-100 text-navy-600 hover:bg-navy-200">+</button>
                </div>
                <!-- Count & Difficulty -->
                <div class="flex gap-2">
                  <div class="flex-1">
                    <label class="text-[10px] text-navy-400 mb-0.5 block">题数</label>
                    <input type="number" min="1" max="50"
                      v-model.number="dimensions.preferred_quiz_preference.count"
                      class="w-full text-xs px-2 py-1 rounded-md border border-navy-200 bg-white focus:outline-none focus:border-navy-400" />
                  </div>
                  <div class="flex-1">
                    <label class="text-[10px] text-navy-400 mb-0.5 block">难度</label>
                    <select v-model="dimensions.preferred_quiz_preference.difficulty"
                      class="w-full text-xs px-2 py-1 rounded-md border border-navy-200 bg-white focus:outline-none focus:border-navy-400">
                      <option value="">未设定</option>
                      <option value="easy">简单</option>
                      <option value="medium">中等</option>
                      <option value="hard">困难</option>
                    </select>
                  </div>
                </div>
              </div>
              <p v-else class="text-xs text-navy-500 leading-relaxed">
                {{ quizPrefDisplay }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Profile history -->
    <div class="card p-6 mt-6 animate-fade-in-up" style="animation-delay: 0.2s">
      <h2 class="font-display text-lg font-semibold text-navy-800 mb-2">画像演变</h2>
      <p class="text-sm text-navy-400">画像会随着你的学习过程自动更新，系统会根据你的学习行为持续优化对你的理解。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import ProfileRadar from '@/components/profile/ProfileRadar.vue'
import { getCurrentProfile, replaceLearningBehavior } from '@/api/user'
import {
  PROFILE_DIMENSION_LABELS,
  GOAL_ORIENTATION_LABELS,
  felderAxisLabel,
} from '@/types/profile'

const dimensions = reactive<Record<string, any>>({})
const editing = ref(false)
const saving = ref(false)
const toast = ref<{ message: string; type: 'success' | 'error' } | null>(null)
const snapshot = ref<string>('')

const newTags = reactive<Record<string, string>>({
  knowledge_base: '',
  interest_tags: '',
  weak_areas: '',
  preferred_resource_types: '',
})
const newQuizType = ref('')

const felderAxes = [
  { key: 'sensing_vs_intuitive', label: '感知-直觉', negLabel: '感知型', posLabel: '直觉型' },
  { key: 'visual_vs_verbal', label: '视觉-言语', negLabel: '视觉型', posLabel: '言语型' },
  { key: 'active_vs_reflective', label: '活跃-沉思', negLabel: '活跃型', posLabel: '沉思型' },
  { key: 'sequential_vs_global', label: '循序-全局', negLabel: '循序型', posLabel: '全局型' },
]

const listFields = ['knowledge_base', 'interest_tags', 'weak_areas', 'preferred_resource_types']

const quizPrefFilled = computed(() => {
  const q = dimensions.preferred_quiz_preference
  if (!q || typeof q !== 'object') return false
  return (Array.isArray(q.types) && q.types.length > 0) || q.count != null || !!q.difficulty
})

const quizPrefDisplay = computed(() => {
  const q = dimensions.preferred_quiz_preference
  if (!q || typeof q !== 'object') return '暂未收集'
  const typesStr = Array.isArray(q.types) && q.types.length > 0 ? q.types.join('、') : '无'
  const countStr = q.count != null ? `${q.count}道` : '未设定'
  const diffStr = q.difficulty || '未设定'
  return `题型: ${typesStr} | 数量: ${countStr} | 难度: ${diffStr}`
})

function barStyle(value: number) {
  const abs = Math.abs(value)
  const width = (abs / 1) * 50
  if (value >= 0) {
    return { left: '50%', width: `${width}%` }
  } else {
    return { left: `${50 - width}%`, width: `${width}%` }
  }
}

function onSliderChange(key: string, event: Event) {
  const val = parseInt((event.target as HTMLInputElement).value) / 100
  dimensions[key] = Math.round(val * 100) / 100
}

function showToast(message: string, type: 'success' | 'error' = 'success') {
  toast.value = { message, type }
  setTimeout(() => { toast.value = null }, 2500)
}

function startEdit() {
  // Save snapshot for cancel
  snapshot.value = JSON.stringify(dimensions)
  // Ensure quiz_preference is an object
  if (!dimensions.preferred_quiz_preference || typeof dimensions.preferred_quiz_preference !== 'object') {
    dimensions.preferred_quiz_preference = { types: [], count: null, difficulty: '' }
  }
  editing.value = true
}

function cancelEdit() {
  Object.assign(dimensions, JSON.parse(snapshot.value))
  editing.value = false
}

async function saveEdit() {
  saving.value = true
  try {
    // Clean up empty values
    const data = { ...dimensions }
    if (data.goal_orientation === '') data.goal_orientation = null
    if (data.preferred_quiz_preference) {
      const q = { ...data.preferred_quiz_preference }
      if (!q.types?.length && q.count == null && !q.difficulty) {
        data.preferred_quiz_preference = null
      }
    }
    await replaceLearningBehavior(JSON.stringify(data))
    editing.value = false
    showToast('画像已保存')
  } catch (e: any) {
    showToast(e?.message || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

function removeTag(field: string, index: number) {
  if (!dimensions[field]) return
  dimensions[field].splice(index, 1)
}

function addTag(field: string) {
  const text = newTags[field]?.trim()
  if (!text) return
  if (!dimensions[field]) dimensions[field] = []
  if (!dimensions[field].includes(text)) {
    dimensions[field].push(text)
  }
  newTags[field] = ''
}

function removeQuizType(index: number) {
  dimensions.preferred_quiz_preference?.types?.splice(index, 1)
}

function addQuizType() {
  const text = newQuizType.value.trim()
  if (!text) return
  if (!dimensions.preferred_quiz_preference) {
    dimensions.preferred_quiz_preference = { types: [], count: null, difficulty: '' }
  }
  if (!dimensions.preferred_quiz_preference.types) {
    dimensions.preferred_quiz_preference.types = []
  }
  if (!dimensions.preferred_quiz_preference.types.includes(text)) {
    dimensions.preferred_quiz_preference.types.push(text)
  }
  newQuizType.value = ''
}

onMounted(async () => {
  try {
    const res = await getCurrentProfile()
    const profile = res.data
    if (profile?.learningBehavior) {
      const behavior = typeof profile.learningBehavior === 'string'
        ? JSON.parse(profile.learningBehavior)
        : profile.learningBehavior
      Object.assign(dimensions, behavior)
    }
  } catch (e) {
    console.error('Failed to load profile:', e)
  }
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* Custom range slider thumb for edit mode */
input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
}
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  opacity: 0;
  transition: opacity 0.2s;
}
input[type="range"]:hover::-webkit-slider-thumb {
  opacity: 1;
}
</style>
