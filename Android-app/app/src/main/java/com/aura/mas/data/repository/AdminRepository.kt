package com.aura.mas.data.repository

import com.aura.mas.data.api.ApiService
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AdminRepository @Inject constructor(private val api: ApiService) {
    suspend fun getStats() = api.getAdminStats()
    suspend fun getUsers(page: Int = 1, size: Int = 20, keyword: String? = null) =
        api.getAdminUsers(page, size, keyword)
    suspend fun toggleUserStatus(userId: Long, status: Int) =
        api.toggleUserStatus(userId, mapOf("status" to status))
    suspend fun getLogs(page: Int = 1, size: Int = 20) = api.getLogs(page, size)
}
