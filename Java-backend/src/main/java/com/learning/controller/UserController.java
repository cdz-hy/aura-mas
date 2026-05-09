package com.learning.controller;

import com.learning.common.Result;
import com.learning.entity.User;
import com.learning.entity.UserProfile;
import com.learning.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@Tag(name = "用户管理")
@RestController
@RequestMapping("/api/user")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @Operation(summary = "获取当前用户信息")
    @GetMapping("/me")
    public Result<User> getCurrentUser(Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(userService.getUserById(userId));
    }

    @Operation(summary = "获取用户画像")
    @GetMapping("/profile")
    public Result<UserProfile> getProfile(Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(userService.getCurrentProfile(userId));
    }

    @Operation(summary = "更新用户画像")
    @PutMapping("/profile")
    public Result<Void> updateProfile(Authentication authentication,
                                       @RequestBody UserProfile profile) {
        Long userId = (Long) authentication.getPrincipal();
        userService.updateProfile(userId, profile);
        return Result.success();
    }
}
