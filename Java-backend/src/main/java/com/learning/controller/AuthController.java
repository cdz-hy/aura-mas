package com.learning.controller;

import com.learning.annotation.OperationLog;
import com.learning.common.OperationType;
import com.learning.common.Result;
import com.learning.dto.LoginRequest;
import com.learning.dto.LoginResponse;
import com.learning.dto.RegisterRequest;
import com.learning.service.AuthService;
import com.learning.service.EmailService;
import com.learning.service.VerificationService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@Tag(name = "认证管理")
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;
    private final VerificationService verificationService;
    private final EmailService emailService;

    @Operation(summary = "用户登录")
    @OperationLog(type = OperationType.LOGIN, module = "Auth",
            desc = "'用户登录: ' + #request.getLoginName()",
            resourceId = "#result?.data?.user?.id?.toString()")
    @PostMapping("/login")
    public Result<LoginResponse> login(@Valid @RequestBody LoginRequest request,
                                       jakarta.servlet.http.HttpServletRequest httpRequest) {
        String clientIp = getClientIp(httpRequest);
        return Result.success(authService.login(request, clientIp));
    }

    @Operation(summary = "发送邮箱验证码")
    @PostMapping("/send-code")
    public Result<Void> sendCode(@Valid @RequestBody SendCodeRequest request,
                                 jakarta.servlet.http.HttpServletRequest httpRequest) {
        String clientIp = getClientIp(httpRequest);
        String error = verificationService.generateCode(request.getEmail(), clientIp);
        if (error != null) {
            return Result.error(429, error);
        }
        // 获取刚生成的验证码并发送邮件
        String code = verificationService.getLastGeneratedCode(request.getEmail());
        if (code == null) {
            return Result.error(500, "验证码生成失败");
        }
        try {
            emailService.sendVerificationCode(request.getEmail(), code);
        } catch (Exception e) {
            return Result.error(500, "邮件发送失败，请稍后重试");
        }
        return Result.success();
    }

    @Operation(summary = "用户注册（需要邮箱验证码）")
    @OperationLog(type = OperationType.REGISTER, module = "Auth",
            desc = "'用户注册: ' + #request.getLoginName()",
            resourceId = "#result?.data?.user?.id?.toString()")
    @PostMapping("/register")
    public Result<LoginResponse> register(@Valid @RequestBody RegisterRequest request) {
        // 验证邮箱验证码
        String verifyError = verificationService.verifyCode(request.getEmail(), request.getEmailCode());
        if (verifyError != null) {
            return Result.error(400, verifyError);
        }
        return Result.success(authService.register(request));
    }

    private String getClientIp(jakarta.servlet.http.HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip != null && !ip.isBlank() && !"unknown".equalsIgnoreCase(ip)) {
            return ip.split(",")[0].trim();
        }
        ip = request.getHeader("X-Real-IP");
        if (ip != null && !ip.isBlank() && !"unknown".equalsIgnoreCase(ip)) {
            return ip;
        }
        return request.getRemoteAddr();
    }

    @Data
    public static class SendCodeRequest {
        @NotBlank(message = "邮箱不能为空")
        @Email(message = "邮箱格式不正确")
        private String email;
    }
}
