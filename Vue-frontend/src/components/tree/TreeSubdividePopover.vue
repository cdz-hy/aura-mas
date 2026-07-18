<template>
  <Teleport to="body">
    <Transition name="split-enter">
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

        <Transition name="split-step" mode="out-in">
          <section v-if="step === 'choice'" key="choice" class="split-body">
            <p v-if="atMaxDepth" class="split-depth-hint">已达最深层，无法继续拆分。分类节点可先拆子分类，再逐层拆到知识点。</p>
            <button class="split-choice split-choice--fp" :disabled="atMaxDepth" @click="startFirstPrinciples">
              <svg class="split-choice-icon split-choice-icon--fp" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
                <path d="M4 4h5v5H4z" />
                <path d="M11 4h5v5h-5z" />
                <path d="M6.5 9v3" />
                <path d="M13.5 9v3" />
                <path d="M6.5 12h7" />
                <path d="M10 12v4" />
              </svg>
              <div class="min-w-0">
                <span class="split-choice-title">第一性原理 · 拆到底</span>
                <span class="split-choice-desc">一层层挖出更底层的前置知识，直到触底。随时可停，比较耗时。</span>
              </div>
            </button>
            <button class="split-choice split-choice--topic" :disabled="atMaxDepth" @click="loadOptions">
              <svg class="split-choice-icon split-choice-icon--topic" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="10" cy="4" r="2.5" />
                <path d="M10 6.5v3" />
                <path d="M10 9.5 5.5 14" />
                <path d="M10 9.5l4.5 4.5" />
                <circle cx="5.5" cy="15.5" r="2" />
                <circle cx="14.5" cy="15.5" r="2" />
              </svg>
              <div class="min-w-0">
                <span class="split-choice-title">按知识点拆分</span>
                <span class="split-choice-desc">让 AI 推荐几个角度，把它拆成一组并列的子知识点。</span>
              </div>
            </button>
            <div class="split-custom">
              <input
                v-model="customAngle"
                maxlength="60"
                placeholder="自定义拆分角度"
                :disabled="atMaxDepth"
                @keydown.enter.prevent="submitCustom"
              />
              <button :disabled="atMaxDepth" @click="submitCustom">拆分</button>
            </div>
          </section>

          <section v-else-if="step === 'loading'" key="loading" class="split-loading">
            <div class="split-dots">
              <span class="split-dot"></span>
              <span class="split-dot"></span>
              <span class="split-dot"></span>
            </div>
            <span>AI 正在挑选拆分角度...</span>
          </section>

          <section v-else key="options" class="split-body">
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
              <span class="split-option-label">
                {{ option.label }}
                <span v-if="option.angle" class="split-angle-tag">{{ option.angle }}</span>
              </span>
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
        </Transition>

        <p v-if="error" class="split-error">{{ error }}</p>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type {
  KnowledgeNode,
  TreeSubdivisionCaution,
  TreeSubdivisionOption,
} from '@/types/knowledgeTree'
import { useKnowledgeTreeStore } from '@/stores/knowledgeTree'

const treeStore = useKnowledgeTreeStore()

const props = defineProps<{
  node: KnowledgeNode | null
  options: TreeSubdivisionOption[]
  caution?: TreeSubdivisionCaution | null
  loading: boolean
  error?: string
}>()

const emit = defineEmits<{
  close: []
  'load-options': []
  'single-angle': [angle: string]
  'multi-angle': [options: TreeSubdivisionOption[]]
  'first-principles': []
}>()

const step = ref<'choice' | 'loading' | 'options'>('choice')
const customAngle = ref('')
const atMaxDepth = computed(() => (props.node ? treeStore.isAtMaxDepth(props.node.id) : false))

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
  if (atMaxDepth.value) return
  step.value = 'loading'
  emit('load-options')
}

function startFirstPrinciples() {
  if (atMaxDepth.value) return
  emit('first-principles')
}

function submitCustom() {
  if (atMaxDepth.value) return
  const angle = customAngle.value.trim()
  if (!angle) return
  emit('single-angle', angle)
}
</script>

<style scoped>
/* Panel entrance animation */
.split-enter-enter-active {
  transition: opacity 0.25s ease, transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.split-enter-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.split-enter-enter-from {
  opacity: 0;
  transform: translateX(24px);
}
.split-enter-leave-to {
  opacity: 0;
  transform: translateX(12px);
}

/* Step crossfade */
.split-step-enter-active,
.split-step-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.split-step-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.split-step-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

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
  transition: background 0.15s ease, color 0.15s ease;
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

.split-depth-hint {
  margin: 0;
  border-radius: 8px;
  background: rgb(254 243 199);
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.45;
  color: rgb(146 64 14);
}

.split-choice:disabled,
.split-custom button:disabled,
.split-custom input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.split-choice,
.split-option,
.split-multi {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  border: 1px solid rgba(26, 40, 71, 0.1);
  border-radius: 8px;
  padding: 12px;
  text-align: left;
  transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.split-choice:hover,
.split-option:hover,
.split-multi:hover {
  border-color: rgba(65, 100, 178, 0.28);
  background: #f7f9ff;
  box-shadow: 0 2px 8px rgba(65, 100, 178, 0.08);
}

.split-choice-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  margin-top: 1px;
  color: #4164b2;
  opacity: 0.65;
  transition: opacity 0.18s ease;
}

.split-choice:hover .split-choice-icon {
  opacity: 1;
}

/* 第一性原理（橙，仿 Sylva） */
.split-choice--fp {
  border-color: rgba(245, 158, 11, 0.28);
  background: rgba(255, 247, 237, 0.75);
}
.split-choice--fp:hover {
  border-color: rgba(245, 158, 11, 0.45);
  background: rgba(255, 237, 213, 0.85);
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.12);
}
.split-choice-icon--fp,
.split-choice--fp .split-choice-title {
  color: #b45309;
}

/* 按知识点拆分（蓝） */
.split-choice--topic {
  border-color: rgba(65, 100, 178, 0.18);
  background: rgba(234, 240, 255, 0.35);
}
.split-choice--topic:hover {
  border-color: rgba(65, 100, 178, 0.32);
  background: rgba(234, 240, 255, 0.65);
}
.split-choice-icon--topic,
.split-choice--topic .split-choice-title {
  color: #4164b2;
}

.split-choice-title,
.split-multi-title,
.split-option-label {
  display: block;
  color: #1f3158;
  font-size: 13px;
  font-weight: 700;
}

.split-choice-desc,
.split-multi-desc,
.split-option-rationale {
  display: block;
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.split-option {
  position: relative;
  padding-left: 16px;
}

.split-option::before {
  content: "";
  position: absolute;
  left: 4px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  border-radius: 1px;
  background: #4164b2;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.split-option:hover::before {
  opacity: 0.45;
}

.split-angle-tag {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 500;
  color: #5b7bb4;
  background: rgba(65, 100, 178, 0.08);
  border-radius: 4px;
  vertical-align: middle;
  line-height: 1.6;
}

.split-multi {
  border-color: rgba(65, 100, 178, 0.2);
  background: linear-gradient(135deg, rgba(234, 240, 255, 0.45) 0%, rgba(248, 250, 252, 0.8) 100%);
}

.split-multi:hover {
  background: linear-gradient(135deg, rgba(234, 240, 255, 0.75) 0%, rgba(223, 232, 255, 0.6) 100%);
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
  gap: 12px;
  padding: 22px 16px;
  color: #53627c;
  font-size: 13px;
}

.split-dots {
  display: flex;
  align-items: center;
  gap: 4px;
}

.split-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #4164b2;
  animation: splitDotBounce 1.2s ease-in-out infinite;
}

.split-dot:nth-child(2) {
  animation-delay: 0.15s;
}

.split-dot:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes splitDotBounce {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.15); }
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
  transition: border-color 0.18s ease;
}

.split-custom input:focus {
  border-color: rgba(65, 100, 178, 0.35);
  outline: none;
}

.split-custom button {
  height: 34px;
  border-radius: 8px;
  background: #eaf0ff;
  padding: 0 12px;
  color: #4164b2;
  font-size: 12px;
  font-weight: 700;
  transition: background 0.18s ease;
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
</style>
