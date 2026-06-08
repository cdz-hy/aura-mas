package com.learning.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * 任务状态 SSE 推送服务
 * Vue 通过订阅 SSE 端点接收任务完成通知，替代轮询
 */
@Slf4j
@Service
public class TaskSseService {

    /** userId -> 该用户的所有活跃 SSE Emitter */
    private final ConcurrentHashMap<Long, CopyOnWriteArrayList<SseEmitter>> emitters = new ConcurrentHashMap<>();

    /**
     * 为指定用户创建 SSE 订阅
     */
    public SseEmitter subscribe(Long userId) {
        // 0L = 无超时，由客户端断开时主动清理
        SseEmitter emitter = new SseEmitter(0L);

        emitters.computeIfAbsent(userId, k -> new CopyOnWriteArrayList<>()).add(emitter);

        emitter.onCompletion(() -> removeEmitter(userId, emitter));
        emitter.onTimeout(() -> removeEmitter(userId, emitter));
        emitter.onError(e -> removeEmitter(userId, emitter));

        // 发送初始连接确认事件
        try {
            emitter.send(SseEmitter.event()
                    .name("connected")
                    .data("{\"type\":\"connected\",\"message\":\"SSE 连接已建立\"}"));
        } catch (IOException e) {
            removeEmitter(userId, emitter);
        }

        log.debug("SSE 订阅: userId={}, 当前连接数={}", userId, emitters.get(userId).size());
        return emitter;
    }

    /**
     * 向指定用户的所有 SSE 连接推送任务状态更新
     */
    public void sendTaskUpdate(Long userId, Long taskId, Integer status, String moduleData) {
        CopyOnWriteArrayList<SseEmitter> userEmitters = emitters.get(userId);
        if (userEmitters == null || userEmitters.isEmpty()) {
            return;
        }

        String eventData = String.format(
                "{\"type\":\"task_update\",\"taskId\":%d,\"status\":%d,\"moduleData\":%s}",
                taskId, status,
                moduleData != null ? "\"" + moduleData.replace("\"", "\\\"") + "\"" : "null"
        );

        for (SseEmitter emitter : userEmitters) {
            try {
                emitter.send(SseEmitter.event()
                        .name("task_update")
                        .data(eventData));
            } catch (IOException e) {
                removeEmitter(userId, emitter);
            }
        }

        log.debug("SSE 推送: userId={}, taskId={}, status={}, 接收者={}",
                userId, taskId, status, userEmitters.size());
    }

    /**
     * 向指定用户推送任务完成事件（简化版本，仅通知状态变化）
     */
    public void sendTaskStatus(Long userId, Long taskId, Integer status) {
        CopyOnWriteArrayList<SseEmitter> userEmitters = emitters.get(userId);
        if (userEmitters == null || userEmitters.isEmpty()) {
            return;
        }

        String eventData = String.format(
                "{\"type\":\"task_status\",\"taskId\":%d,\"status\":%d}",
                taskId, status
        );

        for (SseEmitter emitter : userEmitters) {
            try {
                emitter.send(SseEmitter.event()
                        .name("task_status")
                        .data(eventData));
            } catch (IOException e) {
                removeEmitter(userId, emitter);
            }
        }
    }

    private void removeEmitter(Long userId, SseEmitter emitter) {
        CopyOnWriteArrayList<SseEmitter> userEmitters = emitters.get(userId);
        if (userEmitters != null) {
            userEmitters.remove(emitter);
            if (userEmitters.isEmpty()) {
                emitters.remove(userId);
            }
        }
    }
}
