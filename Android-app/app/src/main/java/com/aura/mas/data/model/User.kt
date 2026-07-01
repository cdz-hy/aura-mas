package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName

data class User(
    val id: Long = 0,
    @SerializedName("loginName") val loginName: String = "",
    val nickname: String = "",
    val email: String = "",
    val role: String = "student",
    val status: Int = 1,
    @SerializedName("avatarUrl") val avatarUrl: String? = null
)

data class LoginRequest(
    @SerializedName("loginName") val loginName: String,
    val password: String
)

data class RegisterRequest(
    @SerializedName("loginName") val loginName: String,
    val password: String,
    val nickname: String,
    val email: String = ""
)

data class LoginResponse(
    val token: String = "",
    val user: User = User(),
    val menus: List<MenuItem> = emptyList()
)

data class MenuItem(
    val id: Long = 0,
    @SerializedName("parentId") val parentId: Long? = null,
    val name: String = "",
    val path: String = "",
    val icon: String = "",
    val sort: Int = 0,
    val type: String = "menu",
    val children: List<MenuItem>? = null
)

data class ApiResponse<T>(
    @SerializedName("code") private val rawCode: Int = 0,
    val message: String = "",
    val data: T? = null
) {
    val code: Int
        get() = if (rawCode == 200) 0 else rawCode
}
