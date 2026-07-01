import request from './request'

/**
 * 增量更新用户学习画像
 * @param userId 用户 ID
 * @param updates 增量更新数据，如 { active_vs_reflective: 0.1 }
 */
export function updateProfileBehavior(
  userId: number,
  updates: Record<string, number>
) {
  return request.put('/internal/profile/incremental', {
    userId,
    updates,
    updateReason: 'profile_bubble_survey'
  })
}
