package com.aura.mas.data.repository

import com.aura.mas.data.api.ApiService
import com.aura.mas.data.local.dao.PlanDao
import com.aura.mas.data.local.dao.ResourceDao
import com.aura.mas.data.local.entity.CachedPlan
import com.aura.mas.data.local.entity.CachedResource
import com.aura.mas.data.model.*
import com.google.gson.Gson
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.CancellationException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PlanRepository @Inject constructor(
    private val api: ApiService,
    private val planDao: PlanDao,
    private val resourceDao: ResourceDao
) {
    fun getPlans(page: Int = 1, size: Int = 20): Flow<ApiResponse<PaginatedResponse<LearningPlan>>> = flow {
        try {
            val response = api.getPlans(page, size)
            if (response.isSuccess && response.data != null) {
                val cached = response.data.records.map { it.toCached() }
                if (page == 1) planDao.deleteAll()
                planDao.insertAll(cached)
            }
            emit(response)
        } catch (e: Exception) {
            if (e is CancellationException) throw e
            val cachedPlans = planDao.getAllPlansSync()
            if (cachedPlans.isNotEmpty()) {
                val paginated = PaginatedResponse(
                    records = cachedPlans.map { it.toDomain() },
                    total = cachedPlans.size.toLong(),
                    page = 1,
                    size = cachedPlans.size,
                    pages = 1
                )
                emit(ApiResponse(data = paginated, message = "离线模式：显示缓存数据"))
            } else {
                emit(ApiResponse(message = e.message ?: "Network error"))
            }
        }
    }

    suspend fun getPlan(planId: Long): ApiResponse<LearningPlan> {
        return try {
            val response = api.getPlan(planId)
            if (response.isSuccess && response.data != null) {
                planDao.insert(response.data.toCached())
            }
            response
        } catch (e: Exception) {
            val cached = planDao.getPlanById(planId)
            if (cached != null) {
                ApiResponse(data = cached.toDomain())
            } else {
                ApiResponse(message = e.message ?: "Unknown error")
            }
        }
    }

    suspend fun createPlan(request: PlanCreateRequest): ApiResponse<LearningPlan> {
        return api.createPlan(request)
    }

    suspend fun deletePlan(planId: Long): ApiResponse<Unit> {
        val result = api.deletePlan(planId)
        if (result.isSuccess) {
            planDao.getPlanById(planId)?.let { planDao.delete(it) }
        }
        return result
    }

    fun getCachedPlans(): Flow<List<CachedPlan>> = planDao.getAllPlans()

    /** Returns cached plan as domain object immediately. */
    suspend fun getCachedPlanDomain(planId: Long): LearningPlan? =
        planDao.getPlanById(planId)?.toDomain()


    fun getResources(planId: Long): Flow<ApiResponse<List<LearningResource>>> = flow {
        try {
            val response = api.getResourcesByPlan(planId)
            if (response.isSuccess && response.data != null) {
                val cached = response.data.map { it.toCachedResource() }
                resourceDao.deleteByPlan(planId)
                resourceDao.insertAll(cached)
            }
            emit(response)
        } catch (e: Exception) {
            if (e is CancellationException) throw e
            val cached = resourceDao.getResourcesByPlanSync(planId)
            if (cached.isNotEmpty()) {
                emit(ApiResponse(data = cached.map { it.toDomain() }, message = "离线模式：显示缓存数据"))
            } else {
                emit(ApiResponse(message = e.message ?: "Network error"))
            }
        }
    }

    fun getCachedResources(planId: Long): Flow<List<CachedResource>> =
        resourceDao.getResourcesByPlan(planId)

    /** Returns cached resources as domain objects immediately (for Cache-First display). */
    suspend fun getCachedResourcesDomain(planId: Long): List<LearningResource> =
        resourceDao.getResourcesByPlanSync(planId).map { it.toDomain() }

    suspend fun dispatchTask(planId: Long, moduleOrder: Int, resourceType: String): ApiResponse<ResourceGenerationTask> {
        return api.dispatchTask(
            mapOf(
                "planId" to planId,
                "moduleOrder" to moduleOrder,
                "resourceType" to resourceType
            )
        )
    }

    suspend fun getProgress(planId: Long): ApiResponse<List<ResourceProgress>> {
        return try {
            api.getProgress(planId)
        } catch (e: Exception) {
            ApiResponse(data = emptyList(), message = e.message ?: "Failed to load progress")
        }
    }

    suspend fun markComplete(planId: Long, resourceId: Long): ApiResponse<Unit> {
        return api.markComplete(planId, resourceId)
    }

    private fun LearningPlan.toCached() = CachedPlan(
        id = id, userId = userId, title = title,
        learningGoal = learningGoal, status = status,
        createdAt = createdAt, updatedAt = updatedAt
    )

    private fun CachedPlan.toDomain() = LearningPlan(
        id = id, userId = userId, title = title,
        learningGoal = learningGoal, status = status,
        createdAt = createdAt, updatedAt = updatedAt
    )

    private fun LearningResource.toCachedResource() = CachedResource(
        id = id, planId = planId, moduleType = moduleType,
        moduleOrder = moduleOrder, moduleName = getModuleName(),
        resourceTitle = getResourceTitle(), resourceType = getResourceType(),
        // Store the complete moduleData JSON so offline restore is lossless
        moduleDataJson = try { Gson().toJson(moduleData) } catch (_: Exception) { null },
        status = status
    )

    private fun CachedResource.toDomain() = LearningResource(
        id = id, planId = planId, moduleType = moduleType,
        moduleOrder = moduleOrder, status = status,
        // Pass the raw JSON string directly – LearningResource.getParsedModuleData() handles String type
        moduleData = moduleDataJson ?: ""
    )
}
