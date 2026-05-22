import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginRequest, RegisterRequest } from '@/types/user'
import type { MenuItem } from '@/types/menu'
import { login as loginApi, register as registerApi } from '@/api/auth'
import { usePermissionStore } from '@/stores/permission'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const homeRoute = computed(() => user.value?.role === 'admin' ? '/admin' : '/dashboard')

  async function login(data: LoginRequest) {
    const res = await loginApi(data)
    const { token: t, user: u, menus: m } = res.data as { token: string; user: User; menus: MenuItem[] }
    if (!t) throw new Error('登录响应格式错误')
    token.value = t
    user.value = u
    localStorage.setItem('token', t)
    localStorage.setItem('user', JSON.stringify(u))
    if (m?.length) {
      const permissionStore = usePermissionStore()
      permissionStore.generateRoutes(m)
    }
  }

  async function register(data: RegisterRequest) {
    const res = await registerApi(data)
    const { token: t, user: u, menus: m } = res.data as { token: string; user: User; menus: MenuItem[] }
    if (!t) throw new Error('注册响应格式错误')
    token.value = t
    user.value = u
    localStorage.setItem('token', t)
    localStorage.setItem('user', JSON.stringify(u))
    if (m?.length) {
      const permissionStore = usePermissionStore()
      permissionStore.generateRoutes(m)
    }
  }

  function logout() {
    const permissionStore = usePermissionStore()
    permissionStore.resetRoutes()
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

  return { token, user, isLoggedIn, isAdmin, homeRoute, login, register, logout, restoreSession }
})
