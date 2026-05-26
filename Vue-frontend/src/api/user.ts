import request from './request'
import type { StudentProfile } from '@/types/profile'
import type { User } from '@/types/user'

export function getCurrentProfile() {
  return request.get<any, { data: StudentProfile }>('/user/profile')
}

export function getCurrentUser() {
  return request.get<any, { data: User }>('/user/me')
}

export function updateUserInfo(data: { nickname?: string; email?: string }) {
  return request.put<any, { data: User }>('/user/info', data)
}

export function uploadAvatar(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<any, { data: { avatarUrl: string } }>('/user/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function clearAvatar() {
  return request.delete('/user/avatar')
}

export function deleteAccount() {
  return request.delete('/user/account')
}

export function updateProfile(data: {
  gender?: string | null
  age?: string | null
  domain?: string | null
  learningBehavior?: string | null
}) {
  return request.put('/user/profile', data)
}
