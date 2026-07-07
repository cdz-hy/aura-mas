package com.aura.mas.di

import com.aura.mas.data.api.ApiService
import com.aura.mas.data.api.AuthInterceptor
import com.aura.mas.data.api.PythonApiService
import com.aura.mas.data.repository.ServerConfig
import com.aura.mas.util.Constants
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Named
import javax.inject.Singleton

import com.aura.mas.data.model.ProfileDimensions
import com.google.gson.JsonDeserializationContext
import com.google.gson.JsonDeserializer
import com.google.gson.JsonElement
import java.lang.reflect.Type

class ProfileDimensionsDeserializer : JsonDeserializer<ProfileDimensions> {
    private val delegateGson = Gson()

    override fun deserialize(json: JsonElement, typeOfT: Type, context: JsonDeserializationContext): ProfileDimensions {
        return if (json.isJsonPrimitive && json.asJsonPrimitive.isString) {
            val str = json.asString
            delegateGson.fromJson(str, ProfileDimensions::class.java)
        } else {
            delegateGson.fromJson(json, ProfileDimensions::class.java)
        }
    }
}

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideGson(): Gson = GsonBuilder()
        .setLenient()
        .registerTypeAdapter(ProfileDimensions::class.java, ProfileDimensionsDeserializer())
        .create()

    @Provides
    @Singleton
    fun provideOkHttpClient(authInterceptor: AuthInterceptor, serverConfig: ServerConfig): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
        // Interceptor that rewrites URLs from default to custom server address
        val serverRewrite = okhttp3.Interceptor { chain ->
            val request = chain.request()
            val currentJavaUrl = serverConfig.javaUrl.value
            val currentPythonUrl = serverConfig.pythonUrl.value
            val url = request.url.toString()
            val newUrl = when {
                url.startsWith(Constants.JAVA_BASE_URL) && currentJavaUrl != Constants.JAVA_BASE_URL ->
                    url.replaceFirst(Constants.JAVA_BASE_URL, currentJavaUrl)
                url.startsWith(Constants.PYTHON_BASE_URL) && currentPythonUrl != Constants.PYTHON_BASE_URL ->
                    url.replaceFirst(Constants.PYTHON_BASE_URL, currentPythonUrl)
                else -> null
            }
            if (newUrl != null) {
                chain.proceed(request.newBuilder().url(newUrl).build())
            } else {
                chain.proceed(request)
            }
        }
        return OkHttpClient.Builder()
            .addInterceptor(serverRewrite)
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .connectTimeout(3, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .build()
    }

    @Provides
    @Singleton
    @Named("java")
    fun provideJavaRetrofit(client: OkHttpClient, gson: Gson): Retrofit {
        return Retrofit.Builder()
            .baseUrl(Constants.JAVA_BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
    }

    @Provides
    @Singleton
    @Named("python")
    fun providePythonRetrofit(client: OkHttpClient, gson: Gson): Retrofit {
        return Retrofit.Builder()
            .baseUrl(Constants.PYTHON_BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
    }

    @Provides
    @Singleton
    fun provideApiService(@Named("java") retrofit: Retrofit): ApiService {
        return retrofit.create(ApiService::class.java)
    }

    @Provides
    @Singleton
    fun providePythonApiService(@Named("python") retrofit: Retrofit): PythonApiService {
        return retrofit.create(PythonApiService::class.java)
    }
}
