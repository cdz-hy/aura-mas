<template>
  <div v-if="visible" class="fixed inset-0 z-[100] flex items-center justify-center">
    <!-- Overlay -->
    <transition name="rrm-overlay">
      <div class="absolute inset-0 bg-navy-900/30 backdrop-blur-[3px]" @click="close"></div>
    </transition>

    <!-- Modal -->
    <div class="rrm-modal relative w-[620px] max-h-[85vh] flex flex-col">
      <!-- Header -->
      <div class="rrm-header px-6 py-5 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="rrm-header-icon">
            <svg class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="3" /><circle cx="5" cy="5" r="2" /><circle cx="19" cy="5" r="2" />
              <circle cx="5" cy="19" r="2" /><circle cx="19" cy="19" r="2" />
              <line x1="7" y1="7" x2="10" y2="10" /><line x1="17" y1="7" x2="14" y2="10" />
              <line x1="7" y1="17" x2="10" y2="14" /><line x1="17" y1="17" x2="14" y2="14" />
            </svg>
          </div>
          <div>
            <h3 class="font-display text-xl font-bold text-navy-800">重新分析知识资源</h3>
            <p class="text-xs text-navy-400 mt-0.5">选择需要重新构建入图谱的学习资源</p>
          </div>
        </div>
        <button @click="close" class="rrm-close-btn">
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <!-- Body -->
      <div class="rrm-body flex-1 overflow-y-auto px-6 py-5">
        <!-- Loading -->
        <div v-if="loading" class="flex flex-col items-center justify-center py-12">
          <div class="rrm-loading-ring mb-4"></div>
          <p class="text-sm text-navy-400">正在加载学习计划...</p>
        </div>

        <!-- Empty -->
        <div v-else-if="plans.length === 0" class="rrm-empty text-center py-12">
          <svg class="w-16 h-16 mx-auto text-navy-200 mb-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" />
          </svg>
          <h4 class="font-display text-lg text-navy-600 mb-1">暂无学习计划</h4>
          <p class="text-sm text-navy-400">创建学习计划后即可进行资源分析</p>
        </div>

        <!-- Plan list -->
        <div v-else class="space-y-3">
          <div v-for="(plan, pi) in plans" :key="plan.id" class="rrm-plan-card" :style="{ animationDelay: pi * 0.05 + 's' }">
            <!-- Plan header -->
            <div
              class="rrm-plan-header"
              :class="{ 'rrm-plan-expanded': expandedPlans.includes(plan.id) }"
              @click="togglePlan(plan.id)"
            >
              <div class="flex items-center gap-3 flex-1 min-w-0">
                <svg
                  class="w-4 h-4 text-navy-400 transition-transform duration-200 flex-shrink-0"
                  :class="{ 'rotate-90': expandedPlans.includes(plan.id) }"
                  viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>

                <input
                  type="checkbox"
                  class="rrm-checkbox flex-shrink-0"
                  :checked="isPlanAllSelected(plan.id)"
                  :indeterminate.prop="isPlanIndeterminate(plan.id)"
                  @click.stop="toggleSelectPlan(plan.id, $event)"
                />

                <div class="flex-1 min-w-0">
                  <div class="text-sm font-semibold text-navy-800 truncate">{{ plan.title }}</div>
                  <div class="text-xs text-navy-400 mt-0.5">
                    <template v-if="planResourceCounts[plan.id] !== undefined">
                      {{ planResourceCounts[plan.id] }} 个学习资源
                    </template>
                    <template v-else>
                      加载中...
                    </template>
                  </div>
                </div>
              </div>

              <!-- Plan badge -->
              <span class="rrm-badge">
                {{ selectedCountForPlan(plan.id) }}/{{ (resourcesByPlan[plan.id] || []).length }}
              </span>
            </div>

            <!-- Plan resources -->
            <transition name="rrm-expand">
              <div v-show="expandedPlans.includes(plan.id)" class="rrm-resources">
                <div v-if="loadingResources[plan.id]" class="py-4 text-center">
                  <div class="rrm-loading-ring-sm mx-auto mb-2"></div>
                  <span class="text-xs text-navy-400">加载资源列表...</span>
                </div>
                <div v-else-if="!resourcesByPlan[plan.id]?.length" class="py-4 text-center text-xs text-navy-400 italic">
                  暂无已生成的学习资源
                </div>
                <label
                  v-for="res in resourcesByPlan[plan.id]"
                  :key="res.id"
                  class="rrm-resource-item"
                >
                  <input
                    type="checkbox"
                    class="rrm-checkbox"
                    :value="res.id"
                    v-model="selectedResourceIds"
                  />
                  <div class="rrm-resource-type-badge" :class="typeBadgeClass(res.moduleType)">
                    {{ typeLabels[res.moduleType] || res.moduleType || '?' }}
                  </div>
                  <span class="text-sm text-navy-700 truncate flex-1">
                    {{ getResourceTitle(res) }}
                  </span>
                </label>
              </div>
            </transition>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="rrm-footer px-6 py-4 flex items-center justify-between">
        <div class="text-sm text-navy-500">
          已选择 <span class="font-bold text-navy-800">{{ selectedResourceIds.length }}</span> 个资源
        </div>
        <div class="flex gap-3">
          <button @click="close" class="rrm-btn-cancel">取消</button>
          <button
            @click="handleConfirm"
            :disabled="selectedResourceIds.length === 0 || submitting"
            class="rrm-btn-primary"
          >
            <svg v-if="submitting" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 11-6.219-8.56" />
            </svg>
            开始分析
          </button>
        </div>
      </div>
    </div>

    <!-- Confirm dialog -->
    <transition name="rrm-overlay">
      <div v-if="showConfirm" class="fixed inset-0 z-[110] flex items-center justify-center">
        <div class="absolute inset-0 bg-navy-900/50 backdrop-blur-[2px]" @click="showConfirm = false"></div>
        <div class="rrm-confirm-dialog relative w-96">
          <div class="rrm-confirm-icon">
            <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <h4 class="font-display text-lg font-bold text-navy-800 mb-2 text-center">确认重新分析？</h4>
          <p class="text-sm text-navy-600 mb-6 leading-relaxed text-center">
            将对 <span class="font-bold text-navy-800">{{ selectedResourceIds.length }}</span> 个资源调用大模型进行知识节点抽取，<span class="text-red-500 font-semibold">会消耗较多 Token</span>。任务将在后台逐步执行。
          </p>
          <div class="flex justify-end gap-3">
            <button @click="showConfirm = false" class="rrm-btn-cancel">再想想</button>
            <button @click="executeAnalysis" class="rrm-btn-danger">确认执行</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { getPlans } from '@/api/plan'
import { getPlanResources } from '@/api/resource'
import { analyzeResources } from '@/api/knowledgeGraph'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits(['update:visible', 'success'])

const authStore = useAuthStore()
const loading = ref(false)
const plans = ref<any[]>([])
const resourcesByPlan = ref<Record<number, any[]>>({})
const planResourceCounts = reactive<Record<number, number>>({})
const loadingResources = ref<Record<number, boolean>>({})
const expandedPlans = ref<number[]>([])
const selectedResourceIds = ref<number[]>([])
const showConfirm = ref(false)
const submitting = ref(false)

const typeLabels: Record<string, string> = {
  text: '图文', image: '图片', diagram: '导图', code: '代码', quiz: '题目', summary: '总结',
  document: '文档', mindmap: '导图', reading: '阅读', video: '视频', podcast: '播客', animation: '动画',
}

function typeBadgeClass(type: string): string {
  const map: Record<string, string> = {
    text: 'rrm-badge-blue', document: 'rrm-badge-blue', mindmap: 'rrm-badge-purple',
    quiz: 'rrm-badge-amber', code: 'rrm-badge-green', reading: 'rrm-badge-rose',
    video: 'rrm-badge-red', summary: 'rrm-badge-sky', podcast: 'rrm-badge-green',
    animation: 'rrm-badge-orange', image: 'rrm-badge-pink', diagram: 'rrm-badge-indigo',
  }
  return map[type] || 'rrm-badge-blue'
}

function getResourceTitle(res: any): string {
  // Try multiple paths for the title
  if (res.moduleData?.title) return res.moduleData.title
  if (res.moduleData?.name) return res.moduleData.name
  if (typeof res.moduleData === 'string') {
    try {
      const parsed = JSON.parse(res.moduleData)
      if (parsed.title) return parsed.title
      if (parsed.name) return parsed.name
    } catch {}
  }
  if (res.title) return res.title
  return `资源 #${res.id}`
}

const close = () => emit('update:visible', false)

watch(() => props.visible, async (newVal) => {
  if (newVal) {
    selectedResourceIds.value = []
    expandedPlans.value = []
    await loadPlans()
  }
})

const loadPlans = async () => {
  loading.value = true
  try {
    const res = await getPlans({ page: 1, size: 100 })
    plans.value = res.data?.records || []
    // Preload resource counts for all plans
    await Promise.all(plans.value.map(p => loadResourceCount(p.id)))
  } catch (e) {
    console.error('Failed to load plans', e)
  } finally {
    loading.value = false
  }
}

const loadResourceCount = async (planId: number) => {
  try {
    const res = await getPlanResources(planId)
    const resources = (res.data || []).filter((r: any) => r.moduleData != null)
    planResourceCounts[planId] = resources.length
    // Cache the full resource list too
    resourcesByPlan.value[planId] = resources
  } catch (e) {
    planResourceCounts[planId] = 0
    resourcesByPlan.value[planId] = []
  }
}

const loadResourcesForPlan = async (planId: number) => {
  if (resourcesByPlan.value[planId]) return
  loadingResources.value[planId] = true
  try {
    const res = await getPlanResources(planId)
    resourcesByPlan.value[planId] = (res.data || []).filter((r: any) => r.moduleData != null)
    planResourceCounts[planId] = resourcesByPlan.value[planId].length
  } catch (e) {
    resourcesByPlan.value[planId] = []
    planResourceCounts[planId] = 0
  } finally {
    loadingResources.value[planId] = false
  }
}

const togglePlan = async (planId: number) => {
  const idx = expandedPlans.value.indexOf(planId)
  if (idx > -1) {
    expandedPlans.value.splice(idx, 1)
  } else {
    expandedPlans.value.push(planId)
    await loadResourcesForPlan(planId)
  }
}

const getPlanResourceIds = (planId: number) => (resourcesByPlan.value[planId] || []).map((r: any) => r.id)

const isPlanAllSelected = (planId: number) => {
  const ids = getPlanResourceIds(planId)
  return ids.length > 0 && ids.every(id => selectedResourceIds.value.includes(id))
}

const isPlanIndeterminate = (planId: number) => {
  const ids = getPlanResourceIds(planId)
  if (ids.length === 0) return false
  const count = ids.filter(id => selectedResourceIds.value.includes(id)).length
  return count > 0 && count < ids.length
}

const selectedCountForPlan = (planId: number) => {
  const ids = getPlanResourceIds(planId)
  return ids.filter(id => selectedResourceIds.value.includes(id)).length
}

const toggleSelectPlan = async (planId: number, event: Event) => {
  if (!resourcesByPlan.value[planId]) {
    await loadResourcesForPlan(planId)
  }
  const ids = getPlanResourceIds(planId)
  const isChecked = (event.target as HTMLInputElement).checked
  if (isChecked) {
    ids.forEach(id => { if (!selectedResourceIds.value.includes(id)) selectedResourceIds.value.push(id) })
  } else {
    selectedResourceIds.value = selectedResourceIds.value.filter(id => !ids.includes(id))
  }
}

const handleConfirm = () => { showConfirm.value = true }

const executeAnalysis = async () => {
  showConfirm.value = false
  submitting.value = true
  try {
    const userId = authStore.user?.id
    if (!userId) return
    await analyzeResources(userId, selectedResourceIds.value)
    emit('success')
    close()
  } catch (e) {
    console.error('Failed to submit analysis', e)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
/* ─── Modal ─── */
.rrm-modal {
  background: #fdf9f0;
  border-radius: 20px;
  box-shadow: 0 8px 40px rgba(26, 40, 71, 0.18), 0 0 0 1px rgba(26, 40, 71, 0.05);
  animation: rrm-in 0.35s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
@keyframes rrm-in {
  from { opacity: 0; transform: translateY(12px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.rrm-header {
  border-bottom: 1px solid rgba(26, 40, 71, 0.06);
  background: rgba(255, 255, 255, 0.5);
  border-radius: 20px 20px 0 0;
}

.rrm-header-icon {
  width: 40px; height: 40px; border-radius: 12px;
  background: linear-gradient(135deg, #1a2847, #4164b2);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}

.rrm-close-btn {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: #6783c1; transition: all 0.2s; cursor: pointer; background: none; border: none;
}
.rrm-close-btn:hover { background: rgba(26, 40, 71, 0.06); color: #1a2847; }

.rrm-body { scrollbar-width: thin; scrollbar-color: rgba(26,40,71,0.12) transparent; }

/* ─── Loading ─── */
.rrm-loading-ring {
  width: 32px; height: 32px; border-radius: 50%;
  border: 3px solid rgba(65, 100, 178, 0.15); border-top-color: #4164b2;
  animation: rrm-spin 0.8s linear infinite;
}
.rrm-loading-ring-sm {
  width: 20px; height: 20px; border-radius: 50%;
  border: 2px solid rgba(65, 100, 178, 0.15); border-top-color: #4164b2;
  animation: rrm-spin 0.8s linear infinite;
}
@keyframes rrm-spin { to { transform: rotate(360deg); } }

/* ─── Plan cards ─── */
.rrm-plan-card {
  border: 1px solid rgba(26, 40, 71, 0.06);
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.6);
  animation: rrm-card-in 0.3s ease forwards;
  opacity: 0;
}
@keyframes rrm-card-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.rrm-plan-header {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px;
  cursor: pointer; transition: background 0.15s;
}
.rrm-plan-header:hover { background: rgba(65, 100, 178, 0.03); }
.rrm-plan-expanded { border-bottom: 1px solid rgba(26, 40, 71, 0.04); }

.rrm-badge {
  font-size: 11px; font-weight: 600; color: #6783c1;
  background: rgba(65, 100, 178, 0.08);
  padding: 2px 8px; border-radius: 10px; flex-shrink: 0;
}

/* ─── Resources ─── */
.rrm-resources { background: rgba(253, 249, 240, 0.4); }

.rrm-resource-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 16px 8px 44px;
  cursor: pointer; transition: background 0.15s;
}
.rrm-resource-item:hover { background: rgba(65, 100, 178, 0.03); }

.rrm-resource-type-badge {
  font-size: 10px; font-weight: 600; padding: 2px 8px;
  border-radius: 6px; flex-shrink: 0; text-transform: uppercase;
}

/* ─── Checkbox ─── */
.rrm-checkbox {
  width: 16px; height: 16px; border-radius: 4px;
  border: 1.5px solid rgba(26, 40, 71, 0.2);
  accent-color: #4164b2; cursor: pointer; flex-shrink: 0;
}

/* ─── Footer ─── */
.rrm-footer {
  border-top: 1px solid rgba(26, 40, 71, 0.06);
  background: rgba(255, 255, 255, 0.4);
  border-radius: 0 0 20px 20px;
}

.rrm-btn-cancel {
  padding: 8px 20px; font-size: 13px; font-weight: 500;
  color: #6783c1; border-radius: 10px; border: none; cursor: pointer;
  transition: all 0.15s; background: transparent;
}
.rrm-btn-cancel:hover { background: rgba(26, 40, 71, 0.04); color: #1a2847; }

.rrm-btn-primary {
  padding: 8px 20px; font-size: 13px; font-weight: 600;
  color: #fdf9f0; border-radius: 10px; border: none; cursor: pointer;
  background: linear-gradient(135deg, #1a2847, #4164b2);
  box-shadow: 0 2px 8px rgba(26, 40, 71, 0.2);
  transition: all 0.2s; display: flex; align-items: center; gap: 6px;
}
.rrm-btn-primary:hover { box-shadow: 0 4px 16px rgba(26, 40, 71, 0.3); transform: translateY(-1px); }
.rrm-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }

.rrm-btn-danger {
  padding: 8px 20px; font-size: 13px; font-weight: 600;
  color: white; border-radius: 10px; border: none; cursor: pointer;
  background: linear-gradient(135deg, #c0392b, #e74c3c);
  box-shadow: 0 2px 8px rgba(192, 57, 43, 0.2);
  transition: all 0.2s;
}
.rrm-btn-danger:hover { box-shadow: 0 4px 16px rgba(192, 57, 43, 0.3); transform: translateY(-1px); }

/* ─── Confirm dialog ─── */
.rrm-confirm-dialog {
  background: #fdf9f0; border-radius: 16px; padding: 24px;
  box-shadow: 0 8px 40px rgba(26, 40, 71, 0.2);
  animation: rrm-in 0.25s ease forwards;
}
.rrm-confirm-icon {
  width: 48px; height: 48px; border-radius: 50%; margin: 0 auto 16px;
  background: rgba(201, 135, 59, 0.1); color: #c9873b;
  display: flex; align-items: center; justify-content: center;
}

/* ─── Type badge colors ─── */
.rrm-badge-blue { background: rgba(65, 100, 178, 0.1); color: #4164b2; }
.rrm-badge-purple { background: rgba(139, 92, 246, 0.1); color: #7c3aed; }
.rrm-badge-amber { background: rgba(201, 135, 59, 0.1); color: #c9873b; }
.rrm-badge-green { background: rgba(100, 155, 100, 0.1); color: #649b64; }
.rrm-badge-rose { background: rgba(244, 63, 94, 0.1); color: #e11d48; }
.rrm-badge-red { background: rgba(239, 68, 68, 0.1); color: #dc2626; }
.rrm-badge-sky { background: rgba(14, 165, 233, 0.1); color: #0284c7; }
.rrm-badge-orange { background: rgba(249, 115, 22, 0.1); color: #ea580c; }
.rrm-badge-pink { background: rgba(236, 72, 153, 0.1); color: #db2777; }
.rrm-badge-indigo { background: rgba(99, 102, 241, 0.1); color: #4f46e5; }

/* ─── Transitions ─── */
.rrm-overlay-enter-active, .rrm-overlay-leave-active { transition: opacity 0.25s ease; }
.rrm-overlay-enter-from, .rrm-overlay-leave-to { opacity: 0; }

.rrm-expand-enter-active { transition: all 0.25s ease; overflow: hidden; }
.rrm-expand-leave-active { transition: all 0.2s ease; overflow: hidden; }
.rrm-expand-enter-from, .rrm-expand-leave-to { max-height: 0; opacity: 0; }
.rrm-expand-enter-to, .rrm-expand-leave-from { max-height: 1000px; opacity: 1; }
</style>
