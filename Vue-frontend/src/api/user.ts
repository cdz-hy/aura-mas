import request from './request'
import type { StudentProfile } from '@/types/profile'

export function getCurrentProfile() {
  return request.get<any, { data: StudentProfile }>('/user/profile')
}
