package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName

data class AdminStats(
    @SerializedName("userCount") val userCount: Int = 0,
    @SerializedName("planCount") val planCount: Int = 0,
    @SerializedName("kbDocCount") val kbDocCount: Int = 0,
    @SerializedName("todayAiCalls") val todayAiCalls: Int = 0
)

data class SystemLog(
    val id: Long = 0,
    @SerializedName("userId") val userId: Long = 0,
    @SerializedName("operationType") val operationType: String = "",
    @SerializedName("operationDesc") val operationDesc: String = "",
    val module: String = "",
    val status: Int = 1,
    @SerializedName("userIp") val userIp: String = "",
    @SerializedName("errorMsg") val errorMsg: String? = null,
    val createdAt: String = ""
)
