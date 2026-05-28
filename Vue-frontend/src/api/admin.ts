import request from './request'
import type { User } from '@/types/user'

export interface AdminUserQuery {
  page?: number
  size?: number
  keyword?: string
  role?: string
  status?: number | null
}

export interface AdminPageResult<T> {
  total: number
  page: number
  size: number
  records: T[]
}

export interface CreateUserRequest {
  loginName: string
  password: string
  nickname?: string
  email?: string
  role?: string
  status?: number
}

export interface UpdateUserRequest {
  nickname?: string
  email?: string
  role?: string
  status?: number
  password?: string
}

// 分页查询用户
export function getUsers(params: AdminUserQuery) {
  return request.get<any, any>('/admin/users', { params })
}

// 获取用户详情
export function getUserById(id: number) {
  return request.get<any, any>(`/admin/users/${id}`)
}

// 新增用户
export function createUser(data: CreateUserRequest) {
  return request.post<any, any>('/admin/users', data)
}

// 更新用户
export function updateUser(id: number, data: UpdateUserRequest) {
  return request.put<any, any>(`/admin/users/${id}`, data)
}

// 删除用户
export function deleteUser(id: number) {
  return request.delete(`/admin/users/${id}`)
}

// 切换用户状态
export function toggleUserStatus(id: number) {
  return request.put(`/admin/users/${id}/status`)
}

// 修改用户角色
export function changeUserRole(id: number, role: string) {
  return request.put(`/admin/users/${id}/role`, { role })
}

// 批量切换状态
export function batchToggleStatus(ids: number[], status: number) {
  return request.put('/admin/users/batch/status', { ids, status })
}

// 批量删除
export function batchDeleteUsers(ids: number[]) {
  return request.delete('/admin/users/batch', { data: { ids } })
}

// ========== Token消耗分析 ==========

export interface TokenAnalysisData {
  summary: {
    totalCalls: number
    totalInputTokens: number
    totalOutputTokens: number
    totalTokens: number
  }
  dailyTrend: {
    date: string
    inputTokens: number
    outputTokens: number
    totalTokens: number
    callCount: number
  }[]
  byModel: {
    modelName: string
    callCount: number
    inputTokens: number
    outputTokens: number
    totalTokens: number
  }[]
  byScene: {
    scene: string
    callCount: number
    inputTokens: number
    outputTokens: number
    totalTokens: number
  }[]
  userRanking: {
    userId: number
    userName: string
    callCount: number
    totalTokens: number
  }[]
}

export function getTokenAnalysis(start: string, end: string) {
  return request.get<any, TokenAnalysisData>('/admin/token/analysis', { params: { start, end } })
}

export interface TokenRecord {
  id: number
  userId: number
  userName: string
  modelName: string
  scene: string
  inputTokens: number
  outputTokens: number
  totalTokens: number
  createdAt: string
}

export interface TokenRecordsPage {
  records: TokenRecord[]
  total: number
  page: number
  size: number
}

export function getTokenRecords(start: string, end: string, page: number, size: number, model?: string, scene?: string) {
  return request.get<any, TokenRecordsPage>('/admin/token/records', { params: { start, end, page, size, model, scene } })
}
