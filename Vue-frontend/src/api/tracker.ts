/**
 * 学习追踪 API
 */
import request from './request'

export interface LearningStrategy {
  id: number
  userId: number
  strategyType: string
  title: string
  description: string
  strategyData: string
  status: 'pending' | 'accepted' | 'rejected'
  createdAt: string
  expiresAt: string
  acceptedAt?: string
}

/**
 * 获取待处理策略数量
 */
export function getPendingStrategyCount() {
  return request.get<any, { data: number }>('/tracker/strategies/count')
}

/**
 * 获取待处理策略列表
 */
export function getPendingStrategies() {
  return request.get<any, { data: LearningStrategy[] }>('/tracker/strategies/pending')
}

/**
 * 获取用户策略列表
 */
export function getUserStrategies(status?: string, limit = 20) {
  return request.get<any, { data: LearningStrategy[] }>('/tracker/strategies', {
    params: { status, limit }
  })
}

/**
 * 接受策略
 */
export function acceptStrategy(strategyId: number) {
  return request.post<any, { data: boolean }>(`/tracker/strategies/${strategyId}/accept`)
}

/**
 * 拒绝策略
 */
export function rejectStrategy(strategyId: number) {
  return request.post<any, { data: boolean }>(`/tracker/strategies/${strategyId}/reject`)
}
