<template>
  <Teleport to="body">
    <aside v-if="node" class="split-panel" aria-label="节点拆分面板">
      <header class="split-head">
        <div class="min-w-0">
          <p class="split-eyebrow">想怎么拆开它</p>
          <h3 class="split-title" :title="node.title">{{ node.title || '未命名节点' }}</h3>
        </div>
        <button class="split-close" title="关闭" @click="$emit('close')">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </button>
      </header>

      <div class="split-mode" role="group" aria-label="拆分粒度">
        <button
          v-for="modeOption in splitModes"
          :key="modeOption.mode"
          :class="{ active: splitMode === modeOption.mode }"
          :title="modeOption.title"
          @click="$emit('update:split-mode', modeOption.mode)"
        >
          <span>{{ modeOption.mode }}</span>
          <small>{{ modeOption.range }}</small>
        </button>
      </div>

      <section v-if="step === 'choice'" class="split-body">
        <button class="split-choice" @click="loadOptions">
          <span class="split-choice-title">按知识点拆分</span>
          <span class="split-choice-desc">先让 AI 给出几个拆分角度，再选择单角度或多角度展开。</span>
        </button>
        <button class="split-choice" @click="startFirstPrinciples">
          <span class="split-choice-title">第一性原理 · 拆到底</span>
          <span class="split-choice-desc">把当前节点继续拆成更基础、不可再省略的组成部分。</span>
        </button>
        <div class="split-custom">
          <input
            v-model="customAngle"
            maxlength="60"
            placeholder="自定义拆分角度"
            @keydown.enter.prevent="submitCustom"
          />
          <button @click="submitCustom">拆分</button>
        </div>
      </section>

      <section v-else-if="step === 'loading'" class="split-loading">
        <span class="split-dot"></span>
        <span>AI 正在挑选拆分角度...</span>
      </section>

      <section v-else class="split-body">
        <div v-if="caution" class="split-caution">
          <span class="split-caution-label">{{ caution.label }}</span>
          <span class="split-caution-text">{{ caution.rationale }}</span>
        </div>

        <button v-if="options.length >= 2" class="split-multi" @click="$emit('multi-angle', options)">
          <span class="split-multi-title">按这 {{ options.length }} 个角度一次全拆</span>
          <span class="split-multi-desc">{{ options.map(option => option.label).join('、') }}</span>
        </button>

        <div v-if="options.length" class="split-divider"><span>或者只挑一个角度</span></div>

        <button
          v-for="option in options"
          :key="`${option.angle}:${option.label}`"
          class="split-option"
          @click="$emit('single-angle', option.angle)"
        >
          <span class="split-option-label">{{ option.label }}</span>
          <span class="split-option-rationale">{{ option.rationale }}</span>
        </button>

        <div class="split-custom">
          <input
            v-model="customAngle"
            maxlength="60"
            placeholder="或者自己写一个角度"
            @keydown.enter.prevent="submitCustom"
          />
          <button @click="submitCustom">拆分</button>
        </div>
      </section>

      <p v-if="error" class="split-error">{{ error }}</p>
    </aside>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type {
  KnowledgeNode,
  TreeSplitMode,
  TreeSubdivisionCaution,
  TreeSubdivisionOption,
} from '@/types/knowledgeTree'

const props = defineProps<{
  node: KnowledgeNode | null
  options: TreeSubdivisionOption[]
  caution?: TreeSubdivisionCaution | null
  splitMode: TreeSplitMode
  loading: boolean
  error?: string
}>()

const emit = defineEmits<{
  close: []
  'load-options': []
  'single-angle': [angle: string]
  'multi-angle': [options: TreeSubdivisionOption[]]
  'first-principles': []
  'update:split-mode': [mode: TreeSplitMode]
}>()

const step = ref<'choice' | 'loading' | 'options'>('choice')
const customAngle = ref('')
const splitModes: Array<{ mode: TreeSplitMode; range: string; title: string }> = [
  { mode: 'Lite', range: '3-4', title: 'Lite：轻量拆分' },
  { mode: 'Medium', range: '5-7', title: 'Medium：中等拆分' },
  { mode: 'Zen', range: '8-12', title: 'Zen：深度拆分' },
]

watch(() => props.node?.id, () => {
  step.value = 'choice'
  customAngle.value = ''
})

watch(() => props.loading, loading => {
  if (loading) {
    step.value = 'loading'
    return
  }
  if (step.value === 'loading') {
    step.value = 'options'
  }
})

function loadOptions() {
  step.value = 'loading'
  emit('load-options')
}

function startFirstPrinciples() {
  emit('first-principles')
}

function submitCustom() {
  const angle = customAngle.value.trim()
  if (!angle) return
  emit('single-angle', angle)
}
</script>

<style scoped>
.split-panel {
  position: fixed;
  right: 24px;
  top: 112px;
  z-index: 1200;
  width: min(420px, calc(100vw - 48px));
  overflow: hidden;
  border: 1px solid rgba(26, 40, 71, 0.12);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 18px 48px rgba(26, 40, 71, 0.18);
  backdrop-filter: blur(12px);
}

.split-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(26, 40, 71, 0.08);
  padding: 16px;
}

.split-eyebrow {
  color: #7c8aa5;
  font-size: 12px;
  font-weight: 700;
}

.split-title {
  margin-top: 4px;
  overflow: hidden;
  color: #1f3158;
  font-size: 16px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.split-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  color: #7c8aa5;
}

.split-close:hover {
  background: #f2f5fa;
  color: #1f3158;
}

.split-body {
  display: grid;
  gap: 10px;
  padding: 16px;
}

.split-mode {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  border-bottom: 1px solid rgba(26, 40, 71, 0.08);
  padding: 10px 16px;
}

.split-mode button {
  display: grid;
  gap: 2px;
  min-width: 0;
  border: 1px solid rgba(26, 40, 71, 0.1);
  border-radius: 8px;
  padding: 7px 4px;
  color: #64748b;
  text-align: center;
}

.split-mode button.active {
  border-color: rgba(65, 100, 178, 0.35);
  background: #eaf0ff;
  color: #294a91;
}

.split-mode span {
  font-size: 12px;
  font-weight: 700;
}

.split-mode small {
  font-size: 10px;
}

.split-choice,
.split-option,
.split-multi {
  display: grid;
  gap: 5px;
  width: 100%;
  border: 1px solid rgba(26, 40, 71, 0.1);
  border-radius: 8px;
  padding: 12px;
  text-align: left;
}

.split-choice:hover,
.split-option:hover,
.split-multi:hover {
  border-color: rgba(65, 100, 178, 0.28);
  background: #f7f9ff;
}

.split-choice-title,
.split-multi-title,
.split-option-label {
  color: #1f3158;
  font-size: 13px;
  font-weight: 700;
}

.split-choice-desc,
.split-multi-desc,
.split-option-rationale {
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.split-caution {
  display: grid;
  gap: 4px;
  border: 1px solid rgba(245, 158, 11, 0.22);
  border-radius: 8px;
  background: #fff8eb;
  padding: 10px 12px;
}

.split-caution-label {
  color: #9a5a00;
  font-size: 12px;
  font-weight: 700;
}

.split-caution-text {
  color: #8a6b2e;
  font-size: 12px;
  line-height: 1.5;
}

.split-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 22px 16px;
  color: #53627c;
  font-size: 13px;
}

.split-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #4164b2;
  animation: splitPulse 1s ease-in-out infinite;
}

.split-divider {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #8a95a8;
  font-size: 11px;
}

.split-divider::before,
.split-divider::after {
  content: "";
  height: 1px;
  flex: 1;
  background: rgba(26, 40, 71, 0.08);
}

.split-custom {
  display: flex;
  gap: 8px;
}

.split-custom input {
  min-width: 0;
  height: 34px;
  flex: 1;
  border: 1px solid rgba(26, 40, 71, 0.12);
  border-radius: 8px;
  padding: 0 10px;
  color: #1f3158;
  font-size: 12px;
}

.split-custom button {
  height: 34px;
  border-radius: 8px;
  background: #eaf0ff;
  padding: 0 12px;
  color: #4164b2;
  font-size: 12px;
  font-weight: 700;
}

.split-custom button:hover {
  background: #dfe8ff;
}

.split-error {
  border-top: 1px solid rgba(248, 113, 113, 0.18);
  padding: 10px 16px 14px;
  color: #dc2626;
  font-size: 12px;
}

@keyframes splitPulse {
  0%, 100% { opacity: 0.4; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.1); }
}
</style>
