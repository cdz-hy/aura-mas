import request from './request'
import type { LoginRequest, RegisterRequest, LoginResponse } from '@/types/user'

export function login(data: LoginRequest) {
  return request.post<any, { data: LoginResponse }>('/auth/login', data)
}

export function register(data: RegisterRequest) {
  return request.post<any, { data: LoginResponse }>('/auth/register', data)
}

export function sendVerificationCode(email: string) {
  return request.post<any, { data: null }>('/auth/send-code', { email })
}

export function refreshToken() {
  return request.post<any, { data: { token: string } }>('/auth/refresh')
}

export function issueTicket() {
  return request.post<any, { data: { ticket: string } }>('/ticket/issue')
}
