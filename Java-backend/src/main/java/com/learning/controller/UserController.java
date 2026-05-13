package com.learning.controller;

import com.learning.common.Result;
import com.learning.entity.User;
import com.learning.entity.UserProfile;
import com.learning.service.QiniuService;
import com.learning.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashMap;
import java.util.Map;

@Tag(name = "用户管理")
@RestController
@RequestMapping("/api/user")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;
    private final QiniuService qiniuService;

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

    @Operation(summary = "更新个人信息")
    @PutMapping("/info")
    public Result<User> updateUserInfo(Authentication authentication,
                                        @RequestBody Map<String, Object> updates) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(userService.updateUserInfo(userId, updates));
    }

    @Operation(summary = "上传头像")
    @PostMapping("/avatar")
    public Result<Map<String, String>> uploadAvatar(Authentication authentication,
                                                     @RequestParam("file") MultipartFile file) {
        Long userId = (Long) authentication.getPrincipal();

        // 后端限制头像大小为 1MB
        if (file.getSize() > 1024 * 1024) {
            return Result.error(400, "头像大小不能超过 1MB");
        }
        // 校验文件类型
        String contentType = file.getContentType();
        if (contentType == null || !contentType.startsWith("image/")) {
            return Result.error(400, "请上传图片文件");
        }

        // 删除旧头像
        User currentUser = userService.getUserById(userId);
        if (currentUser.getAvatarUrl() != null) {
            qiniuService.deleteByUrl(currentUser.getAvatarUrl());
        }

        String avatarUrl = qiniuService.uploadFile(file, "avatars");
        userService.updateAvatar(userId, avatarUrl);
        Map<String, String> result = new HashMap<>();
        result.put("avatarUrl", avatarUrl);
        return Result.success(result);
    }

    @Operation(summary = "清空头像")
    @DeleteMapping("/avatar")
    public Result<Void> clearAvatar(Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        String oldUrl = userService.clearAvatar(userId);
        if (oldUrl != null) {
            qiniuService.deleteByUrl(oldUrl);
        }
        return Result.success();
    }
}
