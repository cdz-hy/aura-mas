package com.aura.mas.data.api

import com.aura.mas.data.repository.AuthStore
import com.aura.mas.util.Constants
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Named

class AuthInterceptor @Inject constructor(
    @Named("token_datastore") private val tokenStore: kotlinx.coroutines.flow.MutableStateFlow<String?>,
    private val authStore: AuthStore
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val token = tokenStore.value
        val request = if (!token.isNullOrBlank()) {
            chain.request().newBuilder()
                .addHeader("Authorization", "Bearer $token")
                .build()
        } else {
            chain.request()
        }
        val response = chain.proceed(request)
        if (response.code == 401) {
            runBlocking {
                authStore.clearSession(expired = true)
            }
        }
        return response
    }
}
