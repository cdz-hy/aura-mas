package com.learning.controller;

import com.learning.annotation.OperationLog;
import com.learning.common.OperationType;
import com.learning.common.Result;
import com.learning.dto.LoginRequest;
import com.learning.dto.LoginResponse;
import com.learning.dto.RegisterRequest;
import com.learning.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@Tag(name = "认证管理")
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @Operation(summary = "用户登录")
    @OperationLog(type = OperationType.LOGIN, module = "Auth",
            desc = "'用户登录: ' + #request.getLoginName()",
            resourceId = "#result?.data?.user?.id?.toString()")
    @PostMapping("/login")
    public Result<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return Result.success(authService.login(request));
    }

    @Operation(summary = "用户注册")
    @OperationLog(type = OperationType.REGISTER, module = "Auth",
            desc = "'用户注册: ' + #request.getLoginName()",
            resourceId = "#result?.data?.user?.id?.toString()")
    @PostMapping("/register")
    public Result<LoginResponse> register(@Valid @RequestBody RegisterRequest request) {
        return Result.success(authService.register(request));
    }
}
