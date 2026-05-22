<template>
  <div class="flex flex-col items-center justify-center h-full min-h-[60vh]">
    <div class="text-center animate-fade-in-up">
      <!-- 404 icon -->
      <div class="w-24 h-24 mx-auto mb-6 rounded-2xl bg-navy-50 flex items-center justify-center">
        <svg class="w-12 h-12 text-navy-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M16 16s-1.5-2-4-2-4 2-4 2" />
          <line x1="9" y1="9" x2="9.01" y2="9" stroke-width="2.5" />
          <line x1="15" y1="9" x2="15.01" y2="9" stroke-width="2.5" />
        </svg>
      </div>
      <h1 class="text-4xl font-display font-bold text-navy-400 mb-2">404</h1>
      <p class="text-navy-400 mb-8">页面不存在或已被移除</p>
      <button @click="goHome" class="btn-primary">
        返回首页
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function goHome() {
  router.push(authStore.homeRoute)
}
</script>
