<template>
  <Teleport to="body">
    <transition-group name="toast-group" tag="div" class="fixed top-5 right-5 z-[9999] flex flex-col gap-3 pointer-events-none">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto w-[340px] max-w-[90vw] bg-white rounded-xl shadow-lg border border-navy-100 overflow-hidden animate-toast-in"
        :class="t.exiting ? 'animate-toast-out' : ''"
      >
        <div class="flex items-start gap-3 p-4">
          <!-- Icon -->
          <div class="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center" :class="iconBg(t.type)">
            <svg v-if="t.type === 'success'" class="w-4.5 h-4.5 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <svg v-else-if="t.type === 'error'" class="w-4.5 h-4.5 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <svg v-else-if="t.type === 'warning'" class="w-4.5 h-4.5 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <svg v-else class="w-4.5 h-4.5 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <!-- Content -->
          <div class="flex-1 min-w-0">
            <p v-if="t.title" class="text-sm font-semibold text-navy-800">{{ t.title }}</p>
            <p class="text-sm text-navy-500 leading-relaxed" :class="t.title ? 'mt-0.5' : ''">{{ t.message }}</p>
          </div>
          <!-- Close -->
          <button
            class="flex-shrink-0 p-1 rounded-md text-navy-300 hover:text-navy-500 hover:bg-navy-50 transition-colors"
            @click="dismiss(t.id)"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <!-- Progress bar -->
        <div class="h-0.5 bg-navy-50">
          <div
            class="h-full transition-all ease-linear"
            :class="progressColor(t.type)"
            :style="{ width: t.progress + '%', transitionDuration: t.duration + 'ms' }"
          />
        </div>
      </div>
    </transition-group>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { toastState, type ToastItem, removeToast } from '@/composables/useToast'

const toasts = toastState.toasts

function iconBg(type: ToastItem['type']) {
  const map: Record<string, string> = {
    success: 'bg-emerald-50',
    error: 'bg-red-50',
    warning: 'bg-amber-50',
    info: 'bg-blue-50',
  }
  return map[type] || map.info
}

function progressColor(type: ToastItem['type']) {
  const map: Record<string, string> = {
    success: 'bg-emerald-400',
    error: 'bg-red-400',
    warning: 'bg-amber-400',
    info: 'bg-blue-400',
  }
  return map[type] || map.info
}

function dismiss(id: number) {
  removeToast(id)
}

// Auto-dismiss handled in composable via setTimeout
</script>

<style scoped>
.animate-toast-in {
  animation: toastIn 0.35s cubic-bezier(0.21, 1.02, 0.73, 1) forwards;
}

.animate-toast-out {
  animation: toastOut 0.25s ease-in forwards;
}

@keyframes toastIn {
  from {
    opacity: 0;
    transform: translateX(40px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

@keyframes toastOut {
  from {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateX(40px) scale(0.96);
  }
}

.toast-group-enter-active {
  transition: all 0.35s cubic-bezier(0.21, 1.02, 0.73, 1);
}
.toast-group-leave-active {
  transition: all 0.25s ease-in;
}
.toast-group-enter-from {
  opacity: 0;
  transform: translateX(40px) scale(0.96);
}
.toast-group-leave-to {
  opacity: 0;
  transform: translateX(40px) scale(0.96);
}
</style>
