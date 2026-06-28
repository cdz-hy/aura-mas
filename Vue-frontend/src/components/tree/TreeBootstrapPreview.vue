<template>
  <div class="bootstrap-preview">
    <div class="bootstrap-preview-header">
      <h3 class="bootstrap-preview-title">主干知识卡片预览</h3>
      <p class="bootstrap-preview-desc">
        编辑、删除或新增主干标题，确认后再生成子知识点。
      </p>
    </div>

    <div v-if="loading" class="bootstrap-preview-loading">
      <div class="split-dots">
        <span class="split-dot"></span>
        <span class="split-dot"></span>
        <span class="split-dot"></span>
      </div>
      <span>AI 正在生成主干标题…</span>
    </div>

    <div v-else-if="error" class="bootstrap-preview-error">
      <span>{{ error }}</span>
      <button class="retry-btn" @click="$emit('retry')">重试</button>
    </div>

    <template v-else>
      <TransitionGroup name="topic-list" tag="div" class="topic-list">
        <div
          v-for="(topic, i) in editableTopics"
          :key="topic._key"
          class="topic-row"
        >
          <span class="topic-index">{{ i + 1 }}</span>
          <div class="topic-fields">
            <input
              v-model="topic.title"
              class="topic-title-input"
              placeholder="标题（≤24字）"
              maxlength="40"
            />
            <input
              v-model="topic.summary"
              class="topic-summary-input"
              placeholder="一句话说明（≤60字）"
              maxlength="160"
            />
          </div>
          <button class="topic-remove" title="删除" @click="removeTopic(i)">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6 6 18" /><path d="m6 6 12 12" />
            </svg>
          </button>
          <span v-if="topic.custom" class="topic-custom-badge">自定义</span>
        </div>
      </TransitionGroup>

      <button class="add-topic-btn" @click="addTopic">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 5v14" /><path d="M5 12h14" />
        </svg>
        添加主干
      </button>

      <div v-if="growing" class="growing-status">
        <div class="growing-progress">
          <div class="growing-bar" :style="{ width: growPercent + '%' }"></div>
        </div>
        <span class="growing-text">
          正在生成「{{ currentBranch }}」的子知识点… {{ doneCount }}/{{ totalCount }}
        </span>
      </div>

      <div v-if="!growing" class="bootstrap-actions">
        <button class="btn-skip" @click="$emit('skip')">跳过预览，直接生成</button>
        <button class="btn-confirm" :disabled="!canConfirm" @click="confirmAndGrow">
          确认，展开子节点
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface TopicItem {
  title: string
  summary: string
  custom: boolean
  _key: string
}

const props = defineProps<{
  topics: Array<{ title: string; summary: string; custom?: boolean }>
  loading?: boolean
  error?: string
  growing?: boolean
  currentBranch?: string
  doneCount?: number
  totalCount?: number
}>()

const emit = defineEmits<{
  (e: 'confirm', topics: Array<{ title: string; summary: string }>): void
  (e: 'skip'): void
  (e: 'retry'): void
}>()

let keyCounter = 0
const editableTopics = ref<TopicItem[]>([])

watch(
  () => props.topics,
  (val) => {
    if (val && val.length && editableTopics.value.length === 0) {
      editableTopics.value = val.map((t) => ({
        title: t.title,
        summary: t.summary || '',
        custom: t.custom || false,
        _key: `topic-${keyCounter++}`,
      }))
    }
  },
  { immediate: true },
)

const canConfirm = computed(
  () => editableTopics.value.some((t) => t.title.trim().length > 0),
)

const growPercent = computed(() => {
  if (!props.totalCount) return 0
  return Math.round(((props.doneCount || 0) / props.totalCount) * 100)
})

function addTopic() {
  editableTopics.value.push({
    title: '',
    summary: '',
    custom: true,
    _key: `topic-${keyCounter++}`,
  })
}

function removeTopic(index: number) {
  editableTopics.value.splice(index, 1)
}

function confirmAndGrow() {
  const valid = editableTopics.value
    .filter((t) => t.title.trim().length > 0)
    .map((t) => ({ title: t.title.trim(), summary: t.summary.trim() }))
  emit('confirm', valid)
}
</script>

<style scoped>
.bootstrap-preview {
  background: #fff;
  border: 1px solid rgba(154, 176, 218, 0.25);
  border-radius: 12px;
  padding: 20px;
  max-width: 560px;
  margin: 0 auto;
}

.bootstrap-preview-header {
  margin-bottom: 16px;
}

.bootstrap-preview-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f3158;
  margin: 0 0 4px;
}

.bootstrap-preview-desc {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}

.bootstrap-preview-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 0;
  color: #64748b;
  font-size: 13px;
  justify-content: center;
}

.split-dots {
  display: flex;
  gap: 4px;
}

.split-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #4164b2;
  animation: dotBounce 1.2s ease-in-out infinite;
}
.split-dot:nth-child(2) { animation-delay: 0.15s; }
.split-dot:nth-child(3) { animation-delay: 0.3s; }

@keyframes dotBounce {
  0%, 80%, 100% { opacity: 0.3; transform: translateY(0); }
  40% { opacity: 1; transform: translateY(-4px); }
}

.bootstrap-preview-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #dc2626;
  font-size: 13px;
  padding: 12px 0;
}

.retry-btn {
  padding: 4px 12px;
  border: 1px solid #dc2626;
  border-radius: 6px;
  color: #dc2626;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
}

.topic-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.topic-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid rgba(154, 176, 218, 0.2);
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.6);
  transition: background 0.2s;
}

.topic-row:hover {
  background: rgba(234, 240, 255, 0.3);
}

.topic-index {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(65, 100, 178, 0.1);
  color: #4164b2;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.topic-fields {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.topic-title-input,
.topic-summary-input {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 3px 6px;
  font-size: 13px;
  color: #1f3158;
  background: transparent;
  outline: none;
  transition: border-color 0.2s, background 0.2s;
}

.topic-title-input {
  font-weight: 600;
}

.topic-title-input:focus,
.topic-summary-input:focus {
  border-color: rgba(65, 100, 178, 0.3);
  background: #fff;
}

.topic-summary-input {
  font-size: 12px;
  color: #64748b;
}

.topic-remove {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: color 0.2s, background 0.2s;
}

.topic-remove:hover {
  color: #dc2626;
  background: rgba(220, 38, 38, 0.06);
}

.topic-custom-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
  font-weight: 500;
  flex-shrink: 0;
}

.add-topic-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 12px;
  border: 1px dashed rgba(65, 100, 178, 0.25);
  border-radius: 8px;
  background: transparent;
  color: #4164b2;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  margin-bottom: 16px;
}

.add-topic-btn:hover {
  background: rgba(234, 240, 255, 0.3);
  border-color: rgba(65, 100, 178, 0.4);
}

.growing-status {
  margin-bottom: 12px;
}

.growing-progress {
  height: 4px;
  border-radius: 2px;
  background: rgba(65, 100, 178, 0.1);
  overflow: hidden;
  margin-bottom: 6px;
}

.growing-bar {
  height: 100%;
  background: #4164b2;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.growing-text {
  font-size: 12px;
  color: #64748b;
}

.bootstrap-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn-skip {
  padding: 8px 16px;
  border: 1px solid rgba(154, 176, 218, 0.3);
  border-radius: 8px;
  background: transparent;
  color: #64748b;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-skip:hover {
  background: rgba(248, 250, 252, 0.8);
}

.btn-confirm {
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  background: #4164b2;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
}

.btn-confirm:hover {
  background: #3654a0;
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.topic-list-enter-active,
.topic-list-leave-active {
  transition: all 0.25s ease;
}
.topic-list-enter-from,
.topic-list-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}
.topic-list-move {
  transition: transform 0.25s ease;
}
</style>
