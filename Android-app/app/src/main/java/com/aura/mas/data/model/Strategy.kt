package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName

data class LearningStrategy(
    val id: Long = 0,
    @SerializedName("userId") val userId: Long = 0,
    @SerializedName("strategyType") val strategyType: String = "",
    val title: String = "",
    val description: String = "",
    @SerializedName("strategyData") val strategyData: String = "",
    val status: String = "pending",
    @SerializedName("createdAt") val createdAt: String = "",
    @SerializedName("expiresAt") val expiresAt: String = "",
    @SerializedName("acceptedAt") val acceptedAt: String? = null
)
