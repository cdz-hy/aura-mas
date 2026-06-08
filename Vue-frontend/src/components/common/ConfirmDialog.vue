<template>
  <Teleport to="body">
    <transition name="fade">
      <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="onCancel" />
        <div class="relative bg-white rounded-2xl shadow-2xl w-[380px] max-w-[85vw] p-6 animate-scale-in">
          <!-- Icon -->
          <div class="flex justify-center mb-4">
            <div class="w-12 h-12 rounded-full flex items-center justify-center"
              :class="type === 'danger' ? 'bg-red-50' : 'bg-navy-50'"
            >
              <svg v-if="type === 'danger'" class="w-6 h-6 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <svg v-else class="w-6 h-6 text-navy-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
            </div>
          </div>

          <!-- Title & message -->
          <h3 class="text-center text-base font-semibold text-navy-800 mb-1">{{ title }}</h3>
          <p class="text-center text-sm text-navy-400 mb-6">{{ message }}</p>

          <!-- Buttons -->
          <div class="flex gap-3">
            <button
              class="flex-1 py-2.5 rounded-lg text-sm border border-navy-200 text-navy-600 hover:bg-navy-50 transition-colors font-medium"
              @click="onCancel"
            >
              {{ cancelText }}
            </button>
            <button
              class="flex-1 py-2.5 rounded-lg text-sm text-white transition-colors font-medium"
              :class="type === 'danger'
                ? 'bg-red-500 hover:bg-red-600'
                : 'bg-navy-600 hover:bg-navy-700'"
              @click="onConfirm"
            >
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  visible: boolean
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  type?: 'default' | 'danger'
}>(), {
  title: '提示',
  message: '确定执行此操作吗？',
  confirmText: '确定',
  cancelText: '取消',
  type: 'default',
})

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

function onConfirm() { emit('confirm') }
function onCancel() { emit('cancel') }
</script>

<style scoped>
.animate-scale-in {
  animation: scaleIn 0.2s ease-out;
}

@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
