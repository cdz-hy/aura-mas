<template>
  <div class="min-h-screen bg-paper flex items-center justify-center px-4">
    <div class="fixed inset-0 gradient-mesh pointer-events-none"></div>

    <div class="relative w-full max-w-md">
      <div class="text-center mb-10 animate-fade-in-up">
        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-navy-600 to-navy-800 flex items-center justify-center shadow-lg">
          <svg class="w-9 h-9 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <h1 class="font-display text-3xl font-bold text-navy-800">智学</h1>
        <p class="mt-2 text-navy-400 text-sm">开始你的个性化学习之旅</p>
      </div>

      <div class="card p-8 animate-fade-in-up" style="animation-delay: 0.1s">
        <h2 class="font-display text-xl font-semibold text-navy-800 mb-6">创建账号</h2>

        <form @submit.prevent="handleRegister" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">登录账号</label>
            <input v-model="form.loginName" type="text" class="input-field" placeholder="设置登录账号" required />
          </div>
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">昵称</label>
            <input v-model="form.nickname" type="text" class="input-field" placeholder="你的昵称" required />
          </div>
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">邮箱 <span class="text-red-400">*</span></label>
            <input v-model="form.email" type="email" class="input-field" placeholder="your@email.com" required />
          </div>
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">邮箱验证码 <span class="text-red-400">*</span></label>
            <div class="flex gap-2">
              <input v-model="form.emailCode" type="text" class="input-field flex-1" placeholder="输入验证码" required maxlength="6" />
              <button
                type="button"
                class="btn-secondary whitespace-nowrap px-4"
                :disabled="codeCooldown > 0 || !form.email || sendingCode"
                @click="handleSendCode"
              >
                {{ codeCooldown > 0 ? `${codeCooldown}s` : sendingCode ? '发送中...' : '获取验证码' }}
              </button>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-navy-600 mb-1.5">密码</label>
            <input v-model="form.password" type="password" class="input-field" placeholder="设置密码（至少6位）" required minlength="6" />
          </div>

          <div v-if="error" class="text-sm text-red-500 bg-red-50 px-4 py-2 rounded-lg">{{ error }}</div>
          <div v-if="successMsg" class="text-sm text-emerald-600 bg-emerald-50 px-4 py-2 rounded-lg">{{ successMsg }}</div>

          <button type="submit" class="btn-primary w-full" :disabled="loading">
            {{ loading ? '注册中...' : '注 册' }}
          </button>
        </form>

        <div class="mt-6 text-center text-sm text-navy-400">
          已有账号？
          <router-link to="/login" class="text-navy-600 font-medium hover:text-navy-800 underline underline-offset-2">
            去登录
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { sendVerificationCode } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({ loginName: '', password: '', nickname: '', email: '', emailCode: '' })
const loading = ref(false)
const error = ref('')
const successMsg = ref('')
const sendingCode = ref(false)
const codeCooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

onUnmounted(() => {
  if (cooldownTimer) clearInterval(cooldownTimer)
})

async function handleSendCode() {
  if (!form.value.email) return
  sendingCode.value = true
  error.value = ''
  successMsg.value = ''
  try {
    await sendVerificationCode(form.value.email)
    successMsg.value = '验证码已发送到您的邮箱，请查收'
    // Start cooldown
    codeCooldown.value = 60
    cooldownTimer = setInterval(() => {
      codeCooldown.value--
      if (codeCooldown.value <= 0) {
        if (cooldownTimer) clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    }, 1000)
  } catch (e: any) {
    error.value = e.response?.data?.message || e.message || '发送失败'
  } finally {
    sendingCode.value = false
  }
}

async function handleRegister() {
  loading.value = true
  error.value = ''
  successMsg.value = ''
  try {
    await authStore.register(form.value)
    router.push(authStore.homeRoute)
  } catch (e: any) {
    error.value = e.response?.data?.message || e.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>
