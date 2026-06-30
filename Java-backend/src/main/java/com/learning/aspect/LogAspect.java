package com.learning.aspect;

import com.learning.annotation.OperationLog;
import com.learning.dto.LoginResponse;
import com.learning.service.SystemLogService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.expression.EvaluationContext;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.lang.reflect.Method;
import java.lang.reflect.Parameter;

@Slf4j
@Aspect
@Component
@RequiredArgsConstructor
public class LogAspect {

    private final SystemLogService systemLogService;
    private final ExpressionParser parser = new SpelExpressionParser();

    @Around("@annotation(operationLog)")
    public Object around(ProceedingJoinPoint joinPoint, OperationLog operationLog) throws Throwable {
        Long userId = getCurrentUserId();
        String userIp = getClientIp();

        Object result = null;
        int status = 1;
        String errorMsg = null;

        try {
            result = joinPoint.proceed();
            return result;
        } catch (Throwable ex) {
            status = 0;
            errorMsg = truncate(ex.getMessage(), 500);
            throw ex;
        } finally {
            // 登录/注册时 SecurityContext 无用户，从返回结果中提取
            if (userId == null) {
                userId = extractUserIdFromResult(result);
            }

            String desc = evaluateSpel(operationLog.desc(), joinPoint, result);
            String resourceId = evaluateSpel(operationLog.resourceId(), joinPoint, result);

            systemLogService.log(
                    userId,
                    operationLog.type(),
                    desc,
                    operationLog.module(),
                    resourceId,
                    userIp,
                    status,
                    errorMsg
            );
        }
    }

    private Long extractUserIdFromResult(Object result) {
        try {
            if (result instanceof com.learning.common.Result<?> r && r.getData() instanceof LoginResponse lr) {
                return lr.getUser().getId();
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    private String evaluateSpel(String expression, ProceedingJoinPoint joinPoint, Object result) {
        if (expression == null || expression.isEmpty()) {
            return null;
        }
        try {
            EvaluationContext context = new StandardEvaluationContext();
            MethodSignature signature = (MethodSignature) joinPoint.getSignature();
            Method method = signature.getMethod();
            Parameter[] parameters = method.getParameters();
            Object[] args = joinPoint.getArgs();

            for (int i = 0; i < parameters.length; i++) {
                ((StandardEvaluationContext) context).setVariable(parameters[i].getName(), args[i]);
            }
            if (result != null) {
                ((StandardEvaluationContext) context).setVariable("result", result);
            }

            Object value = parser.parseExpression(expression).getValue(context);
            return value != null ? truncate(value.toString(), 200) : null;
        } catch (Exception e) {
            log.warn("SpEL表达式解析失败: {}", expression, e);
            return null;
        }
    }

    private Long getCurrentUserId() {
        try {
            Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
            if (authentication != null && authentication.getPrincipal() instanceof Long) {
                return (Long) authentication.getPrincipal();
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    private String getClientIp() {
        try {
            ServletRequestAttributes attrs = (ServletRequestAttributes)
                    RequestContextHolder.getRequestAttributes();
            if (attrs == null) {
                return null;
            }
            HttpServletRequest request = attrs.getRequest();
            String ip = request.getHeader("X-Forwarded-For");
            if (ip != null && !ip.isEmpty()) {
                ip = ip.split(",")[0].trim();
            }
            if (ip == null || ip.isEmpty()) {
                ip = request.getHeader("X-Real-IP");
            }
            if (ip == null || ip.isEmpty()) {
                ip = request.getRemoteAddr();
            }
            return ip;
        } catch (Exception ignored) {
            return null;
        }
    }

    private String truncate(String str, int maxLen) {
        if (str == null) return null;
        return str.length() > maxLen ? str.substring(0, maxLen) : str;
    }
}
