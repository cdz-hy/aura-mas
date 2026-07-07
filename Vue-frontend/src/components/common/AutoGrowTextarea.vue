<!--
  自动增高的多行输入框：
  - v-model 绑定文本
  - Enter 提交所在 form（触发 form @submit.prevent）；Shift+Enter 换行
  - 内容变化自动调整高度，上限 maxHeight 后出现滚动条
  - 兼容原生 <input> 的外观类 input-field
  - 可选：showVoice 显示麦克风语音输入按钮
-->
<template>
  <div class="relative flex-1 flex items-end">
    <textarea
      ref="el"
      :class="textareaClass"
      :style="{ minHeight: '40px', paddingRight: showVoice ? '44px' : undefined }"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :maxlength="maxlength"
      rows="1"
      @input="onInput"
      @keydown="onKeydown"
    />
    <!-- 麦克风按钮 -->
    <button
      v-if="showVoice"
      type="button"
      class="mic-btn"
      :class="{ 'mic-recording': voiceRecording }"
      :disabled="disabled"
      @click.stop="$emit('voiceToggle')"
      :title="voiceRecording ? '点击结束录音' : '语音输入'"
    >
      <!-- 录音中的脉冲光环 -->
      <span v-if="voiceRecording" class="mic-pulse-ring" />
      <span v-if="voiceRecording" class="mic-pulse-ring mic-pulse-ring-delay" />

      <!-- 图标 -->
      <span class="mic-icon-wrap">
        <!-- 录音中：停止方块 -->
        <svg v-if="voiceRecording" class="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="2"/>
        </svg>
        <!-- 空闲：麦克风 -->
        <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  disabled?: boolean
  maxlength?: number
  maxHeight?: number
  textareaClass?: string
  showVoice?: boolean
  voiceRecording?: boolean
}>(), {
  placeholder: '',
  disabled: false,
  maxlength: 4000,
  maxHeight: 160,
  textareaClass: 'input-field flex-1 resize-none overflow-y-auto leading-relaxed',
  showVoice: false,
  voiceRecording: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'submit'): void
  (e: 'voiceToggle'): void
}>()

const el = ref<HTMLTextAreaElement | null>(null)

function resize() {
  const ta = el.value
  if (!ta) return
  ta.style.height = 'auto'
  const h = Math.min(ta.scrollHeight, props.maxHeight)
  ta.style.height = `${h}px`
}

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value)
  nextTick(resize)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    emit('submit')
    const form = (e.target as HTMLElement)?.closest('form')
    if (form) form.requestSubmit()
  }
}

watch(() => props.modelValue, () => nextTick(resize))
onMounted(resize)
</script>

<style scoped>
.mic-btn {
  position: absolute;
  right: 6px;
  bottom: 6px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  background: transparent;
  color: #94a3b8;
  overflow: visible;
}

.mic-btn:hover:not(:disabled) {
  background: #f1f5f9;
  color: #475569;
  transform: scale(1.08);
}

.mic-btn:active:not(:disabled) {
  transform: scale(0.95);
}

/* 录音中状态 */
.mic-btn.mic-recording {
  background: linear-gradient(135deg, #ef4444, #f97316);
  color: white;
  box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
  animation: mic-glow 2s ease-in-out infinite;
}

@keyframes mic-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  50% { box-shadow: 0 0 12px 4px rgba(239, 68, 68, 0.2); }
}

/* 图标容器 */
.mic-icon-wrap {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 脉冲光环 */
.mic-pulse-ring {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid rgba(239, 68, 68, 0.3);
  animation: mic-pulse 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
  z-index: 0;
}

.mic-pulse-ring-delay {
  animation-delay: 0.5s;
}

@keyframes mic-pulse {
  0% {
    transform: scale(1);
    opacity: 0.6;
  }
  100% {
    transform: scale(2.2);
    opacity: 0;
  }
}
</style>
