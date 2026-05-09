import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginRequest, RegisterRequest } from '@/types/user'
import { login as loginApi, register as registerApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(data: LoginRequest) {
    const res = await loginApi(data)
    const { token: t, user: u } = res.data as any
    if (!t) throw new Error('登录响应格式错误')
    token.value = t
    user.value = u
    localStorage.setItem('token', t)
    if (u) localStorage.setItem('user', JSON.stringify(u))
  }

  async function register(data: RegisterRequest) {
    const res = await registerApi(data)
    const { token: t, user: u } = res.data as any
    if (!t) throw new Error('注册响应格式错误')
    token.value = t
    user.value = u
    localStorage.setItem('token', t)
    if (u) localStorage.setItem('user', JSON.stringify(u))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  function restoreSession() {
    const savedUser = localStorage.getItem('user')
    if (savedUser && token.value) {
      try {
        user.value = JSON.parse(savedUser)
      } catch {
        logout()
      }
    }
  }

  restoreSession()

  return { token, user, isLoggedIn, isAdmin, login, register, logout, restoreSession }
})
