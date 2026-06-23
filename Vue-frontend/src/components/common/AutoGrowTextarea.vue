<!--
  自动增高的多行输入框：
  - v-model 绑定文本
  - Enter 提交所在 form（触发 form @submit.prevent）；Shift+Enter 换行
  - 内容变化自动调整高度，上限 maxHeight 后出现滚动条
  - 兼容原生 <input> 的外观类 input-field
-->
<template>
  <textarea
    ref="el"
    :class="textareaClass"
    style="min-height: 40px;"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :maxlength="maxlength"
    rows="1"
    @input="onInput"
    @keydown="onKeydown"
  />
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
}>(), {
  placeholder: '',
  disabled: false,
  maxlength: 4000,
  maxHeight: 160,
  textareaClass: 'input-field flex-1 resize-none overflow-y-auto leading-relaxed',
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'submit'): void
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
  // Enter 提交（Shift+Enter 换行；输入法组合中不处理）
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    emit('submit')
    // 触发所在 form 的提交，复用父级 <form @submit.prevent> 逻辑
    const form = (e.target as HTMLElement)?.closest('form')
    if (form) {
      form.requestSubmit()
    }
  }
}

watch(() => props.modelValue, () => nextTick(resize))
onMounted(resize)
</script>