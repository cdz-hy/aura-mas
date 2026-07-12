<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6 flex-wrap gap-3">
      <h1 class="section-title">大模型调用分析</h1>
      <div class="flex items-center gap-3 flex-wrap">
        <!-- View Toggle -->
        <div class="flex items-center bg-navy-100 rounded-lg p-0.5">
          <button
            class="px-3.5 py-1.5 text-sm rounded-md transition-all font-medium"
            :class="viewMode === 'chart' ? 'bg-white text-navy-800 shadow-sm' : 'text-navy-500 hover:text-navy-700'"
            @click="viewMode = 'chart'"
          >
            <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            图表
          </button>
          <button
            class="px-3.5 py-1.5 text-sm rounded-md transition-all font-medium"
            :class="viewMode === 'list' ? 'bg-white text-navy-800 shadow-sm' : 'text-navy-500 hover:text-navy-700'"
            @click="switchToList"
          >
            <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
            列表
          </button>
        </div>

        <!-- Date Range -->
        <div class="flex items-center gap-2 bg-navy-50 rounded-lg px-3 py-2">
          <svg class="w-4 h-4 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <input v-model="dateRange.start" type="date" class="bg-transparent text-sm text-navy-700 outline-none" />
          <span class="text-navy-300">-</span>
          <input v-model="dateRange.end" type="date" class="bg-transparent text-sm text-navy-700 outline-none" />
        </div>

        <button class="btn-primary text-sm" @click="handleSearch" :disabled="loading">
          <svg v-if="loading" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
          <span v-else>查询</span>
        </button>

        <!-- Presets -->
        <div class="flex bg-navy-100/60 rounded-lg p-0.5 gap-0.5">
          <button v-for="preset in datePresets" :key="preset.label"
            class="px-3.5 py-1.5 text-xs rounded-md transition-all font-medium whitespace-nowrap"
            :class="activePreset === preset.label ? 'bg-navy-700 text-white shadow-sm' : 'text-navy-500 hover:text-navy-700 hover:bg-navy-50'"
            @click="applyPreset(preset)">
            {{ preset.label }}
          </button>
        </div>

        <!-- Export -->
        <button class="btn-ghost text-sm flex items-center gap-1.5" @click="exportXlsx" :disabled="!data">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          导出
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading && !data" class="flex items-center justify-center py-20">
      <svg class="w-8 h-8 animate-spin text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
    </div>

    <template v-else-if="data">
      <!-- ======================== CHART VIEW ======================== -->
      <template v-if="viewMode === 'chart'">
        <!-- Summary Cards -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
          <div v-for="(stat, i) in summaryStats" :key="stat.label"
            class="stat-card animate-fade-in-up rounded-2xl"
            :style="{ animationDelay: `${i * 0.08}s` }">
            <div class="flex items-center gap-3 mb-2">
              <div class="w-9 h-9 rounded-xl flex items-center justify-center" :class="stat.bgClass">
                <div class="w-5 h-5" :class="stat.iconClass" v-html="stat.icon"></div>
              </div>
              <span class="stat-label">{{ stat.label }}</span>
            </div>
            <span class="stat-value">{{ stat.value }}</span>
          </div>
        </div>

        <!-- Bento Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div class="card rounded-2xl p-6 lg:col-span-2">
            <h2 class="font-display text-base font-semibold text-navy-800 mb-4">每日Token消耗趋势</h2>
            <div class="h-[300px]">
              <Line :data="dailyTrendData" :options="lineChartOptions" />
            </div>
          </div>
          <div class="card rounded-2xl p-6">
            <h2 class="font-display text-base font-semibold text-navy-800 mb-4">模型消耗分布</h2>
            <div class="h-[300px] flex items-center justify-center">
              <Doughnut :data="modelData" :options="doughnutOptions" />
            </div>
          </div>
          <div class="card rounded-2xl p-6 lg:col-span-2">
            <h2 class="font-display text-base font-semibold text-navy-800 mb-4">场景消耗分布</h2>
            <div class="h-[280px]">
              <Bar :data="sceneData" :options="sceneBarOptions" />
            </div>
          </div>
          <div class="card rounded-2xl p-6">
            <h2 class="font-display text-base font-semibold text-navy-800 mb-4">用户消耗排行 Top10</h2>
            <div class="h-[280px]">
              <Bar :data="userRankingData" :options="userBarOptions" />
            </div>
          </div>
          <div class="card rounded-2xl p-6 lg:col-span-3">
            <h2 class="font-display text-base font-semibold text-navy-800 mb-4">每日调用次数</h2>
            <div class="h-[220px]">
              <Bar :data="dailyCallData" :options="callBarOptions" />
            </div>
          </div>
        </div>
      </template>

      <!-- ======================== LIST VIEW ======================== -->
      <template v-else>
        <!-- Summary Cards -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
          <div v-for="(stat, i) in summaryStats" :key="stat.label"
            class="stat-card animate-fade-in-up rounded-2xl"
            :style="{ animationDelay: `${i * 0.08}s` }">
            <div class="flex items-center gap-3 mb-2">
              <div class="w-9 h-9 rounded-xl flex items-center justify-center" :class="stat.bgClass">
                <div class="w-5 h-5" :class="stat.iconClass" v-html="stat.icon"></div>
              </div>
              <span class="stat-label">{{ stat.label }}</span>
            </div>
            <span class="stat-value">{{ stat.value }}</span>
          </div>
        </div>

        <!-- Filter Bar -->
        <div class="card rounded-2xl p-4 mb-4">
          <div class="flex flex-wrap items-center gap-3">
            <!-- Model Dropdown -->
            <div class="custom-dropdown" v-click-outside="() => modelDropdownOpen = false">
              <button class="dropdown-trigger" :class="{ 'has-value': filters.model }" @click="modelDropdownOpen = !modelDropdownOpen">
                <svg class="w-4 h-4 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v2m0 18v2m-9-11h2m18 0h2m-3.3-6.7-1.4 1.4M6.7 17.3l-1.4 1.4m0-13.4 1.4 1.4m10.6 10.6 1.4 1.4"/></svg>
                <span>{{ modelLabel }}</span>
                <svg class="w-4 h-4 text-navy-300 transition-transform" :class="{ 'rotate-180': modelDropdownOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
              </button>
              <transition name="dropdown">
                <div v-if="modelDropdownOpen" class="dropdown-menu">
                  <button v-for="opt in modelOptions" :key="opt.value"
                    class="dropdown-item" :class="{ 'active': filters.model === opt.value }"
                    @click="filters.model = opt.value; modelDropdownOpen = false; loadRecords(1)">
                    <span>{{ opt.label }}</span>
                    <svg v-if="filters.model === opt.value" class="w-4 h-4 ml-auto text-navy-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </button>
                </div>
              </transition>
            </div>

            <!-- Scene Dropdown -->
            <div class="custom-dropdown" v-click-outside="() => sceneDropdownOpen = false">
              <button class="dropdown-trigger" :class="{ 'has-value': filters.scene }" @click="sceneDropdownOpen = !sceneDropdownOpen">
                <svg class="w-4 h-4 text-navy-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
                <span>{{ sceneLabel2 }}</span>
                <svg class="w-4 h-4 text-navy-300 transition-transform" :class="{ 'rotate-180': sceneDropdownOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
              </button>
              <transition name="dropdown">
                <div v-if="sceneDropdownOpen" class="dropdown-menu">
                  <button v-for="opt in sceneOptions" :key="opt.value"
                    class="dropdown-item" :class="{ 'active': filters.scene === opt.value }"
                    @click="filters.scene = opt.value; sceneDropdownOpen = false; loadRecords(1)">
                    <span>{{ opt.label }}</span>
                    <svg v-if="filters.scene === opt.value" class="w-4 h-4 ml-auto text-navy-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </button>
                </div>
              </transition>
            </div>

            <button class="btn-ghost text-sm" @click="resetFilters">
              <svg class="w-4 h-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
              重置
            </button>
          </div>
        </div>

        <!-- Table -->
        <div class="card rounded-2xl overflow-hidden">
          <div v-if="tableLoading" class="p-12 text-center">
            <div class="inline-block w-8 h-8 border-2 border-navy-200 border-t-navy-600 rounded-full animate-spin" />
            <p class="text-sm text-navy-400 mt-3">加载中...</p>
          </div>

          <template v-else-if="records.length > 0">
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead>
                  <tr class="border-b border-navy-100 bg-navy-50/50">
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">ID</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">用户</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">模型</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">场景</th>
                    <th class="px-5 py-3 text-right text-xs font-semibold text-navy-500 uppercase tracking-wider">输入Token</th>
                    <th class="px-5 py-3 text-right text-xs font-semibold text-navy-500 uppercase tracking-wider">输出Token</th>
                    <th class="px-5 py-3 text-right text-xs font-semibold text-navy-500 uppercase tracking-wider">总Token</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-navy-500 uppercase tracking-wider">时间</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in records" :key="row.id"
                    class="border-b border-navy-50 hover:bg-navy-50/30 transition-colors animate-row"
                    :style="{ animationDelay: `${idx * 30}ms` }">
                    <td class="px-5 py-3.5 text-sm text-navy-400 font-mono">{{ row.id }}</td>
                    <td class="px-5 py-3.5">
                      <span class="text-sm font-medium text-navy-800">{{ row.userName || `用户${row.userId}` }}</span>
                    </td>
                    <td class="px-5 py-3.5">
                      <span class="badge bg-indigo-50 text-indigo-700 border border-indigo-200">{{ row.modelName }}</span>
                    </td>
                    <td class="px-5 py-3.5">
                      <span class="badge" :class="sceneBadgeClass(row.scene)">{{ sceneLabelFn(row.scene) }}</span>
                    </td>
                    <td class="px-5 py-3.5 text-sm text-right text-emerald-600 font-mono">{{ formatNumber(row.inputTokens) }}</td>
                    <td class="px-5 py-3.5 text-sm text-right text-amber-600 font-mono">{{ formatNumber(row.outputTokens) }}</td>
                    <td class="px-5 py-3.5 text-sm text-right font-semibold text-navy-800 font-mono">{{ formatNumber(row.totalTokens) }}</td>
                    <td class="px-5 py-3.5 text-sm text-navy-400">{{ formatTime(row.createdAt) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Pagination -->
            <div class="px-5 py-4 border-t border-navy-100 flex items-center justify-between">
              <p class="text-sm text-navy-400">
                共 <span class="font-medium text-navy-600">{{ tableTotal }}</span> 条记录
              </p>
              <div class="flex items-center gap-1">
                <button class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
                  :class="tablePage > 1 ? 'text-navy-600 hover:bg-navy-50' : 'text-navy-300 cursor-not-allowed'"
                  :disabled="tablePage <= 1" @click="loadRecords(tablePage - 1)">上一页</button>
                <button v-for="p in visiblePages" :key="p"
                  class="w-9 h-9 rounded-lg text-sm font-medium transition-colors"
                  :class="p === tablePage ? 'bg-navy-600 text-white shadow-sm' : 'text-navy-600 hover:bg-navy-50'"
                  @click="loadRecords(p)">{{ p }}</button>
                <button class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
                  :class="tablePage < tableTotalPages ? 'text-navy-600 hover:bg-navy-50' : 'text-navy-300 cursor-not-allowed'"
                  :disabled="tablePage >= tableTotalPages" @click="loadRecords(tablePage + 1)">下一页</button>
              </div>
            </div>
          </template>

          <div v-else class="p-16 text-center">
            <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-navy-50 flex items-center justify-center">
              <svg class="w-8 h-8 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
            <p class="text-navy-500 font-medium">暂无调用记录</p>
            <p class="text-sm text-navy-400 mt-1">当前时间范围内没有Token消耗数据</p>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import dayjs from 'dayjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Legend, Filler } from 'chart.js'
import { Line, Doughnut, Bar } from 'vue-chartjs'
import { getTokenAnalysis, getTokenRecords, type TokenAnalysisData, type TokenRecord } from '@/api/admin'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Legend, Filler)

// Click-outside directive
const vClickOutside = {
  mounted(el: HTMLElement, binding: any) {
    el._clickOutside = (e: MouseEvent) => { if (!el.contains(e.target as Node)) binding.value(e) }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el: HTMLElement) { document.removeEventListener('click', el._clickOutside) },
}

// ======================== State ========================
const loading = ref(false)
const data = ref<TokenAnalysisData | null>(null)
const viewMode = ref<'chart' | 'list'>('chart')
const activePreset = ref('近7天')

const dateRange = ref({
  start: dayjs().subtract(6, 'day').format('YYYY-MM-DD'),
  end: dayjs().format('YYYY-MM-DD'),
})

const datePresets = [
  { label: '近7天', days: 6 },
  { label: '近30天', days: 29 },
  { label: '近90天', days: 89 },
]

// Table state
const records = ref<TokenRecord[]>([])
const tableTotal = ref(0)
const tablePage = ref(1)
const tableSize = ref(20)
const tableLoading = ref(false)

// Filters
const filters = ref({ model: '', scene: '' })
const modelDropdownOpen = ref(false)
const sceneDropdownOpen = ref(false)

const colors = ['#3b5998', '#1abc9c', '#e74c3c', '#f39c12', '#9b59b6', '#2ecc71', '#e67e22', '#3498db', '#95a5a6', '#e91e63']

// ======================== Filter Options ========================
const modelOptions = computed(() => {
  const models = data.value?.byModel || []
  return [
    { value: '', label: '全部模型' },
    ...models.map(m => ({ value: m.modelName, label: m.modelName })),
  ]
})

const sceneOptions = computed(() => {
  const scenes = data.value?.byScene || []
  return [
    { value: '', label: '全部场景' },
    ...scenes.map(s => ({ value: s.scene, label: sceneLabelFn(s.scene) })),
  ]
})

const modelLabel = computed(() => modelOptions.value.find(o => o.value === filters.value.model)?.label || '全部模型')
const sceneLabel2 = computed(() => sceneOptions.value.find(o => o.value === filters.value.scene)?.label || '全部场景')

function resetFilters() {
  filters.value = { model: '', scene: '' }
  loadRecords(1)
}

// ======================== Fetch ========================
async function fetchData() {
  loading.value = true
  try {
    const res = await getTokenAnalysis(dateRange.value.start, dateRange.value.end + ' 23:59:59') as any
    data.value = res.data ?? res
  } finally {
    loading.value = false
  }
}

let skipPresetClear = false

function applyPreset(preset: { label: string; days: number }) {
  skipPresetClear = true
  activePreset.value = preset.label
  dateRange.value.start = dayjs().subtract(preset.days, 'day').format('YYYY-MM-DD')
  dateRange.value.end = dayjs().format('YYYY-MM-DD')
  handleSearch()
}

function handleSearch() {
  fetchData()
  if (viewMode.value === 'list') loadRecords(1)
}

function switchToList() {
  viewMode.value = 'list'
  if (records.value.length === 0) loadRecords(1)
}

watch(dateRange, () => {
  if (skipPresetClear) { skipPresetClear = false; return }
  activePreset.value = ''
}, { deep: true })
onMounted(fetchData)

// ======================== Table ========================
async function loadRecords(page: number) {
  if (page < 1 || (tableTotalPages.value > 1 && page > tableTotalPages.value)) return
  tableLoading.value = true
  tablePage.value = page
  try {
    const res = await getTokenRecords(
      dateRange.value.start, dateRange.value.end + ' 23:59:59',
      page, tableSize.value,
      filters.value.model || undefined,
      filters.value.scene || undefined,
    ) as any
    const d = res.data ?? res
    records.value = d.records ?? []
    tableTotal.value = d.total ?? 0
  } catch {
    records.value = []
    tableTotal.value = 0
  } finally {
    tableLoading.value = false
  }
}

const tableTotalPages = computed(() => Math.max(1, Math.ceil(tableTotal.value / tableSize.value)))

const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, tablePage.value - 2)
  const end = Math.min(tableTotalPages.value, tablePage.value + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

// ======================== Helpers ========================
function formatTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

function formatNumber(n: number): string { return n.toLocaleString() }

function formatTime(t: string | null | undefined): string {
  if (!t) return '-'
  return dayjs(t).format('MM-DD HH:mm:ss')
}

const sceneMap: Record<string, string> = {
  // 核心流程
  controller_react: '控制调度', task_decomposition_react: '任务分解', task_decomposition: '任务分解',
  simple_qa: '简单问答', anomaly_clarify: '异常澄清', anomaly_check: '异常检测',
  content_orchestration: '内容编排', content_review: '内容审核',
  // 资源生成
  resource_generation: '资源生成', resource_react_search: '资源检索', resource_type_generation: '资源类型生成',
  quiz_generation: '题目生成', quiz_grading: '题目批改', quiz_grading_inline: '题目批改',
  animation_generation: '动画生成', flashcard_generation: '闪卡生成',
  // PPT 生成
  pptx_manuscript: 'PPT文稿', pptx_outline: 'PPT大纲', pptx_content: 'PPT内容',
  pptx_image_query: 'PPT配图', pptx_image_validate: 'PPT图片校验',
  // 对话与辅导
  tutor_react: '智能辅导', tutor_response: '辅导回复', tutor_profile_analysis: '辅导画像分析',
  conversation_compression: '对话压缩', note_formatting: '笔记格式化',
  // 搜索与检索
  video_search_react: '视频检索', video_search_screening: '视频筛选',
  rag_query_optimization: 'RAG查询优化',
  // 画像与分析
  profile_maintenance: '画像维护', intent_recognition: '意图识别',
  analytics_suggestions: '分析建议', analytics_report: '分析报告',
  greeting: '智能问候', plan_icon_generation: '计划图标生成',
  // 学习分析与顾问
  learning_analysis: '学习分析', plan_advisor: '学习顾问',
  // 知识树
  knowledge_tree_explain: '知识树讲解', knowledge_tree_subdivide: '知识树拆分',
  knowledge_tree_multi_angle: '知识树多角度', knowledge_tree_first_principles: '知识树第一性原理',
  knowledge_tree_quiz: '知识树测验', knowledge_tree_flashcards: '知识树闪卡',
  knowledge_tree_bootstrap: '知识树初始化', preview_topics: '主题预览', grow_children: '子节点扩展',
  // 其他
  qwen_chat: '通义千问对话',
}

function sceneLabelFn(scene: string): string { return sceneMap[scene] || scene }

function sceneBadgeClass(scene: string): string {
  const map: Record<string, string> = {
    // 蓝色系：核心流程
    controller_react: 'bg-blue-50 text-blue-700 border border-blue-200',
    task_decomposition: 'bg-blue-50 text-blue-700 border border-blue-200',
    task_decomposition_react: 'bg-blue-50 text-blue-700 border border-blue-200',
    content_orchestration: 'bg-blue-50 text-blue-700 border border-blue-200',
    content_review: 'bg-blue-50 text-blue-700 border border-blue-200',
    // 绿色系：问答与辅导
    simple_qa: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    tutor_react: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    tutor_response: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    tutor_profile_analysis: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    plan_advisor: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    // 紫色系：资源生成
    resource_generation: 'bg-purple-50 text-purple-700 border border-purple-200',
    resource_react_search: 'bg-purple-50 text-purple-700 border border-purple-200',
    resource_type_generation: 'bg-purple-50 text-purple-700 border border-purple-200',
    animation_generation: 'bg-purple-50 text-purple-700 border border-purple-200',
    // 琥珀色系：题目
    quiz_generation: 'bg-amber-50 text-amber-700 border border-amber-200',
    quiz_grading: 'bg-amber-50 text-amber-700 border border-amber-200',
    quiz_grading_inline: 'bg-amber-50 text-amber-700 border border-amber-200',
    // 青色系：知识树
    knowledge_tree_explain: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
    knowledge_tree_subdivide: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
    knowledge_tree_multi_angle: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
    knowledge_tree_first_principles: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
    knowledge_tree_quiz: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
    knowledge_tree_flashcards: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
    knowledge_tree_bootstrap: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
    // 玫瑰色系：画像与分析
    profile_maintenance: 'bg-rose-50 text-rose-700 border border-rose-200',
    learning_analysis: 'bg-rose-50 text-rose-700 border border-rose-200',
    analytics_suggestions: 'bg-rose-50 text-rose-700 border border-rose-200',
    analytics_report: 'bg-rose-50 text-rose-700 border border-rose-200',
    // 橙色系：PPT
    pptx_manuscript: 'bg-orange-50 text-orange-700 border border-orange-200',
    pptx_outline: 'bg-orange-50 text-orange-700 border border-orange-200',
    pptx_content: 'bg-orange-50 text-orange-700 border border-orange-200',
    pptx_image_query: 'bg-orange-50 text-orange-700 border border-orange-200',
    pptx_image_validate: 'bg-orange-50 text-orange-700 border border-orange-200',
    // 青绿色系：检索
    video_search_react: 'bg-teal-50 text-teal-700 border border-teal-200',
    video_search_screening: 'bg-teal-50 text-teal-700 border border-teal-200',
    rag_query_optimization: 'bg-teal-50 text-teal-700 border border-teal-200',
    // 粉色系：其他
    flashcard_generation: 'bg-pink-50 text-pink-700 border border-pink-200',
    conversation_compression: 'bg-pink-50 text-pink-700 border border-pink-200',
    note_formatting: 'bg-pink-50 text-pink-700 border border-pink-200',
    greeting: 'bg-pink-50 text-pink-700 border border-pink-200',
    anomaly_clarify: 'bg-pink-50 text-pink-700 border border-pink-200',
    anomaly_check: 'bg-pink-50 text-pink-700 border border-pink-200',
  }
  return map[scene] || 'bg-navy-50 text-navy-700 border border-navy-200'
}

// ======================== Export ========================
async function exportXlsx() {
  if (!data.value) return
  const { utils, writeFile } = await import('xlsx')
  const wb = utils.book_new()

  // Sheet 1: Daily Trend
  const trendRows = (data.value.dailyTrend || []).map(d => ({
    '日期': dayjs(d.date).format('YYYY-MM-DD'), '输入Token': d.inputTokens,
    '输出Token': d.outputTokens, '总Token': d.totalTokens, '调用次数': d.callCount,
  }))
  utils.book_append_sheet(wb, utils.json_to_sheet(trendRows), '每日趋势')

  // Sheet 2: Model Distribution
  const modelRows = (data.value.byModel || []).map(m => ({
    '模型': m.modelName, '调用次数': m.callCount,
    '输入Token': m.inputTokens, '输出Token': m.outputTokens, '总Token': m.totalTokens,
  }))
  utils.book_append_sheet(wb, utils.json_to_sheet(modelRows), '模型分布')

  // Sheet 3: Scene Distribution
  const sceneRows = (data.value.byScene || []).map(s => ({
    '场景': sceneLabelFn(s.scene), '场景标识': s.scene, '调用次数': s.callCount,
    '输入Token': s.inputTokens, '输出Token': s.outputTokens, '总Token': s.totalTokens,
  }))
  utils.book_append_sheet(wb, utils.json_to_sheet(sceneRows), '场景分布')

  // Sheet 4: User Ranking
  const userRows = (data.value.userRanking || []).map(u => ({
    '用户': u.userName || `用户${u.userId}`, '调用次数': u.callCount, '总Token': u.totalTokens,
  }))
  utils.book_append_sheet(wb, utils.json_to_sheet(userRows), '用户排行')

  // Sheet 5: Raw Records (fetch all for export)
  try {
    const allRecords: any[] = []
    let page = 1
    let hasMore = true
    while (hasMore) {
      const res = await getTokenRecords(
        dateRange.value.start, dateRange.value.end + ' 23:59:59',
        page, 500, filters.value.model || undefined, filters.value.scene || undefined,
      ) as any
      const d = res.data ?? res
      const batch = d.records || []
      allRecords.push(...batch)
      hasMore = batch.length === 500
      page++
    }
    const detailRows = allRecords.map((r: any) => ({
      'ID': r.id, '用户': r.userName || `用户${r.userId}`, '模型': r.modelName,
      '场景': sceneLabelFn(r.scene), '输入Token': r.inputTokens, '输出Token': r.outputTokens,
      '总Token': r.totalTokens, '时间': dayjs(r.createdAt).format('YYYY-MM-DD HH:mm:ss'),
    }))
    utils.book_append_sheet(wb, utils.json_to_sheet(detailRows), '详细记录')
  } catch {
    // If fetch fails, skip detail sheet
  }

  writeFile(wb, `大模型调用分析_${dateRange.value.start}_${dateRange.value.end}.xlsx`)
}

// ======================== Summary Stats ========================
const summaryStats = computed(() => {
  const s = data.value?.summary
  if (!s) return []
  return [
    { label: '总调用次数', value: formatNumber(s.totalCalls), bgClass: 'bg-blue-50', iconClass: 'text-blue-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>' },
    { label: '总Token消耗', value: formatTokens(s.totalTokens), bgClass: 'bg-purple-50', iconClass: 'text-purple-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>' },
    { label: '输入Token', value: formatTokens(s.totalInputTokens), bgClass: 'bg-emerald-50', iconClass: 'text-emerald-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>' },
    { label: '输出Token', value: formatTokens(s.totalOutputTokens), bgClass: 'bg-amber-50', iconClass: 'text-amber-500',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' },
  ]
})

// ======================== Charts ========================
const dailyTrendData = computed(() => {
  const trend = data.value?.dailyTrend || []
  return {
    labels: trend.map(d => dayjs(d.date).format('MM/DD')),
    datasets: [
      { label: '输入Token', data: trend.map(d => d.inputTokens), borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,0.08)', fill: true, tension: 0.35, pointRadius: 3, pointHoverRadius: 5 },
      { label: '输出Token', data: trend.map(d => d.outputTokens), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.08)', fill: true, tension: 0.35, pointRadius: 3, pointHoverRadius: 5 },
      { label: '总Token', data: trend.map(d => d.totalTokens), borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.06)', fill: true, tension: 0.35, pointRadius: 3, pointHoverRadius: 5, borderDash: [5, 5] },
    ],
  }
})

const lineChartOptions = {
  responsive: true, maintainAspectRatio: false, interaction: { mode: 'index' as const, intersect: false },
  plugins: { legend: { position: 'top' as const, labels: { usePointStyle: true, padding: 16, font: { size: 12 } } }, tooltip: { callbacks: { label: (ctx: any) => `${ctx.dataset.label}: ${formatNumber(ctx.parsed.y)}` } } },
  scales: { y: { beginAtZero: true, ticks: { callback: (v: any) => formatTokens(v) }, grid: { color: 'rgba(0,0,0,0.04)' } }, x: { grid: { display: false } } },
}

const modelData = computed(() => {
  const models = data.value?.byModel || []
  return { labels: models.map(m => m.modelName), datasets: [{ data: models.map(m => m.totalTokens), backgroundColor: colors.slice(0, models.length), borderWidth: 2, borderColor: '#fff' }] }
})

const doughnutOptions = {
  responsive: true, maintainAspectRatio: false, cutout: '55%',
  plugins: { legend: { position: 'bottom' as const, labels: { padding: 14, usePointStyle: true, font: { size: 12 } } }, tooltip: { callbacks: { label: (ctx: any) => { const t = ctx.dataset.data.reduce((a: number, b: number) => a + b, 0); return `${ctx.label}: ${formatTokens(ctx.parsed)} (${t > 0 ? ((ctx.parsed / t) * 100).toFixed(1) : 0}%)` } } } },
}

const sceneData = computed(() => {
  const scenes = data.value?.byScene || []
  return { labels: scenes.map(s => sceneLabelFn(s.scene)), datasets: [
    { label: '输入Token', data: scenes.map(s => s.inputTokens), backgroundColor: 'rgba(16,185,129,0.7)', borderRadius: 4 },
    { label: '输出Token', data: scenes.map(s => s.outputTokens), backgroundColor: 'rgba(245,158,11,0.7)', borderRadius: 4 },
  ] }
})

const sceneBarOptions = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { position: 'top' as const, labels: { usePointStyle: true, padding: 16, font: { size: 12 } } }, tooltip: { callbacks: { label: (ctx: any) => `${ctx.dataset.label}: ${formatNumber(ctx.parsed.y)}` } } },
  scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, beginAtZero: true, ticks: { callback: (v: any) => formatTokens(v) }, grid: { color: 'rgba(0,0,0,0.04)' } } },
}

const userRankingData = computed(() => {
  const ranking = data.value?.userRanking || []
  return { labels: ranking.map(u => u.userName || `用户${u.userId}`), datasets: [{ label: 'Token消耗', data: ranking.map(u => u.totalTokens), backgroundColor: ranking.map((_, i) => colors[i % colors.length]), borderRadius: 4 }] }
})

const userBarOptions = {
  responsive: true, maintainAspectRatio: false, indexAxis: 'y' as const,
  plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx: any) => { const u = data.value?.userRanking?.[ctx.dataIndex]; return `Token: ${formatNumber(ctx.parsed.x)} | 调用: ${u?.callCount || 0}次` } } } },
  scales: { x: { beginAtZero: true, ticks: { callback: (v: any) => formatTokens(v) }, grid: { color: 'rgba(0,0,0,0.04)' } }, y: { grid: { display: false } } },
}

const dailyCallData = computed(() => {
  const trend = data.value?.dailyTrend || []
  return { labels: trend.map(d => dayjs(d.date).format('MM/DD')), datasets: [{ label: '调用次数', data: trend.map(d => d.callCount), backgroundColor: 'rgba(99,102,241,0.6)', borderRadius: 4, maxBarThickness: 40 }] }
})

const callBarOptions = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx: any) => `调用次数: ${ctx.parsed.y}` } } },
  scales: { y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: 'rgba(0,0,0,0.04)' } }, x: { grid: { display: false } } },
}
</script>

<style scoped>
.animate-row {
  animation: fadeInRow 0.35s ease-out forwards;
  opacity: 0;
}

@keyframes fadeInRow {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Custom Dropdown */
.custom-dropdown { position: relative; }

.dropdown-trigger {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px; min-width: 130px;
  background: white; border: 1.5px dashed #c8d6e0; border-radius: 10px;
  font-size: 0.875rem; color: #64748b; cursor: pointer; transition: all 0.2s ease; font-family: inherit;
}
.dropdown-trigger:hover { border-color: #94a3b8; background: #f8fafc; }
.dropdown-trigger.has-value { color: #1e293b; border-color: #94a3b8; border-style: solid; }

.dropdown-menu {
  position: absolute; top: calc(100% + 6px); left: 0; min-width: 100%;
  background: white; border: 1.5px solid #e2e8f0; border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04);
  padding: 4px; z-index: 50; overflow: hidden;
}
.dropdown-item {
  display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 12px;
  border-radius: 8px; font-size: 0.875rem; color: #475569; background: transparent;
  border: none; cursor: pointer; transition: all 0.15s ease; text-align: left; font-family: inherit;
}
.dropdown-item:hover { background: #f1f5f9; color: #1e293b; }
.dropdown-item.active { background: #f1f5f9; color: #1e293b; font-weight: 500; }

.dropdown-enter-active { transition: all 0.2s ease-out; }
.dropdown-leave-active { transition: all 0.15s ease-in; }
.dropdown-enter-from { opacity: 0; transform: translateY(-6px) scale(0.98); }
.dropdown-leave-to { opacity: 0; transform: translateY(-4px) scale(0.98); }
</style>
