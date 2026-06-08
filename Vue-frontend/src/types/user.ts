import type { MenuItem } from './menu'

export interface User {
  id: number
  loginName: string
  nickname: string
  email: string
  avatarUrl: string
  role: 'student' | 'admin'
  status: number
  lastLoginTime: string
  createdAt: string
}

export interface LoginRequest {
  loginName: string
  password: string
}

export interface RegisterRequest {
  loginName: string
  password: string
  nickname: string
  email: string
}

export interface LoginResponse {
  token: string
  user: User
  menus: MenuItem[]
}
