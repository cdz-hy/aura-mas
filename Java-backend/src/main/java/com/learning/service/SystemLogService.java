package com.learning.service;

import com.learning.entity.SystemLog;
import com.learning.mapper.SystemLogMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Slf4j
@Service
@RequiredArgsConstructor
public class SystemLogService {

    private final SystemLogMapper systemLogMapper;

    @Async
    public void log(Long userId, String operationType, String operationDesc,
                    String module, String resourceId, String userIp,
                    int status, String errorMsg) {
        try {
            SystemLog sysLog = new SystemLog();
            sysLog.setUserId(userId);
            sysLog.setOperationType(operationType);
            sysLog.setOperationDesc(operationDesc);
            sysLog.setModule(module);
            sysLog.setResourceId(resourceId);
            sysLog.setUserIp(userIp);
            sysLog.setStatus(status);
            sysLog.setErrorMsg(errorMsg);
            sysLog.setCreatedAt(LocalDateTime.now());
            systemLogMapper.insert(sysLog);
        } catch (Exception e) {
            log.error("写入系统日志失败: type={}", operationType, e);
        }
    }
}
