package com.learning.util;

import com.learning.common.ErrorCode;
import com.learning.exception.BusinessException;
import org.springframework.security.core.Authentication;

/**
 * 认证工具类 - 统一处理 Authentication 空值检查
 */
public class AuthUtils {

    /**
     * 获取当前登录用户 ID，未登录时抛出业务异常
     */
    public static Long getCurrentUserId(Authentication authentication) {
        if (authentication == null || authentication.getPrincipal() == null) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }
        return (Long) authentication.getPrincipal();
    }
}
