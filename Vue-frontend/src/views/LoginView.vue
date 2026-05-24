<template>
  <div class="min-h-screen bg-paper flex items-center justify-center px-4">
    <!-- Decorative background -->
    <div class="fixed inset-0 gradient-mesh pointer-events-none"></div>

    <!-- Floating knowledge nodes (decorative) -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
      <div v-for="i in 6" :key="i"
        class="absolute w-2 h-2 rounded-full bg-navy-200/30 node-pulse"
        :style="{
          left: `${15 + i * 14}%`,
          top: `${20 + (i % 3) * 25}%`,
          animationDelay: `${i * 0.5}s`,
        }"
      ></div>
    </div>

    <div class="relative w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-10 animate-fade-in-up">
        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-navy-600 to-navy-800 flex items-center justify-center shadow-lg">
          <svg class="w-9 h-9 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <h1 class="font-display text-3xl font-bold text-navy-800">智学</h1>
        <p class="mt-2 text-navy-400 text-sm">个性化学习 · 因材施教</p>
      </div>

      <!-- Login form -->
      <div class="card p-8 animate-fade-in-up" style="animation-delay: 0.1s">
        <h2 class="font-display text-xl font-semibold text-navy-800 mb-6">欢迎回来</h2>

        <form @submit.prevent="handleLogin" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">账号</label>
            <input
              v-model="form.loginName"
              type="text"
              class="input-field"
              placeholder="请输入登录账号"
              required
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">密码</label>
            <input
              v-model="form.password"
              type="password"
              class="input-field"
              placeholder="请输入密码"
              required
            />
          </div>

          <div v-if="expiredNotice" class="text-sm text-amber-600 bg-amber-50 px-4 py-2 rounded-lg">
            {{ expiredNotice }}
          </div>

          <div v-if="error" class="text-sm text-red-500 bg-red-50 px-4 py-2 rounded-lg">
            {{ error }}
          </div>

          <button type="submit" class="btn-primary w-full" :disabled="loading">
            <span v-if="loading" class="inline-flex items-center gap-2">
              <svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="4" stroke-linecap="round" class="opacity-75"/></svg>
              登录中...
            </span>
            <span v-else>登 录</span>
          </button>
        </form>

        <div class="mt-6 text-center text-sm text-navy-400">
          还没有账号？
          <router-link to="/register" class="text-navy-600 font-medium hover:text-navy-800 underline underline-offset-2">
            立即注册
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = ref({ loginName: '', password: '' })
const loading = ref(false)
const error = ref('')
const expiredNotice = ref('')

onMounted(() => {
  if (route.query.expired === '1') {
    expiredNotice.value = '登录已过期，请重新登录'
  }
})

async function handleLogin() {
  loading.value = true
  error.value = ''
  expiredNotice.value = ''
  try {
    await authStore.login(form.value)
    router.push(authStore.homeRoute)
  } catch (e: any) {
    error.value = e.message || '登录失败，请检查账号密码'
  } finally {
    loading.value = false
  }
}
</script>
