package com.aura.mas.util

import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import okhttp3.*
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import java.io.IOException
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

data class SseEvent(
    val type: String,
    val data: String,
    val rawJson: JsonObject? = null
)

@Singleton
class SseClient @Inject constructor(
    private val gson: Gson,
    private val serverConfig: com.aura.mas.data.repository.ServerConfig
) {
    // Interceptor that rewrites URLs from default to custom server address
    private val serverRewrite = Interceptor { chain ->
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

    private val client = OkHttpClient.Builder()
        .addInterceptor(serverRewrite)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(5, TimeUnit.MINUTES)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val factory = EventSources.createFactory(client)

    fun connect(url: String): Flow<SseEvent> = callbackFlow {
        val request = Request.Builder()
            .url(url)
            .header("Accept", "text/event-stream")
            .header("Cache-Control", "no-cache")
            .build()

        val listener = object : EventSourceListener() {
            override fun onEvent(eventSource: EventSource, id: String?, type: String?, data: String) {
                // Python backend sends: data: {"type": "stream_text", "content": "..."}
                // The SSE event type is inside the JSON 'type' field, not the SSE 'event' field
                try {
                    val json = gson.fromJson(data, JsonObject::class.java)
                    val eventType = json?.get("type")?.asString ?: type ?: "message"
                    trySend(SseEvent(eventType, data, json))
                } catch (e: Exception) {
                    // If JSON parsing fails, use the raw SSE event type
                    trySend(SseEvent(type ?: "message", data))
                }
            }

            override fun onClosed(eventSource: EventSource) {
                close()
            }

            override fun onFailure(eventSource: EventSource, t: Throwable?, response: Response?) {
                close(t ?: IOException("SSE connection failed: ${response?.code}"))
            }

            override fun onOpen(eventSource: EventSource, response: Response) {
                // Connection opened
            }
        }

        val eventSource = factory.newEventSource(request, listener)

        awaitClose {
            eventSource.cancel()
        }
    }

    fun parseEventData(data: String): JsonObject? {
        return try {
            gson.fromJson(data, JsonObject::class.java)
        } catch (e: Exception) {
            null
        }
    }
}
