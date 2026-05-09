import axios, { type AxiosInstance, type InternalAxiosRequestConfig, type AxiosResponse } from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const JAVA_BASE = '/api'

const request: AxiosInstance = axios.create({
  baseURL: JAVA_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

request.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const authStore = useAuthStore()
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config
})

request.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data
    // Java Result wrapper: code=200 means success
    if (res.code !== undefined && res.code !== 200 && res.code !== 0) {
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    // Return { data: ... } so callers can use res.data.xxx
    return { data: res.data ?? res } as any
  },
  (error) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default request

// Python SSE base URL (direct connection, bypassing Java proxy)
export const PYTHON_AI_BASE = 'http://localhost:8002'
