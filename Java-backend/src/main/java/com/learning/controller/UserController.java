package com.learning.controller;

import com.learning.annotation.OperationLog;
import com.learning.common.OperationType;
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
    @OperationLog(type = OperationType.USER_UPDATE_PROFILE, module = "User", desc = "更新学习画像")
    @PutMapping("/profile")
    public Result<Void> updateProfile(Authentication authentication,
                                       @RequestBody UserProfile profile) {
        Long userId = (Long) authentication.getPrincipal();
        userService.updateProfile(userId, profile);
        return Result.success();
    }

    @Operation(summary = "直接替换学习行为数据（前端手动编辑用）")
    @OperationLog(type = OperationType.USER_UPDATE_BEHAVIOR, module = "User", desc = "替换学习行为数据")
    @PutMapping("/profile/behavior")
    public Result<Void> replaceLearningBehavior(Authentication authentication,
                                                 @RequestBody Map<String, String> body) {
        Long userId = (Long) authentication.getPrincipal();
        String learningBehavior = body.get("learningBehavior");
        if (learningBehavior == null || learningBehavior.isBlank()) {
            return Result.error(400, "learningBehavior 不能为空");
        }
        userService.replaceLearningBehavior(userId, learningBehavior);
        return Result.success();
    }

    @Operation(summary = "更新个人信息")
    @OperationLog(type = OperationType.USER_UPDATE_INFO, module = "User", desc = "更新个人信息")
    @PutMapping("/info")
    public Result<User> updateUserInfo(Authentication authentication,
                                        @RequestBody Map<String, Object> updates) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(userService.updateUserInfo(userId, updates));
    }

    @Operation(summary = "上传头像")
    @OperationLog(type = OperationType.USER_UPLOAD_AVATAR, module = "User", desc = "上传头像")
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

    @Operation(summary = "注销账号")
    @OperationLog(type = OperationType.USER_DELETE_ACCOUNT, module = "User", desc = "用户注销账号")
    @DeleteMapping("/account")
    public Result<Void> deleteAccount(Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        userService.deleteAccount(userId);
        return Result.success();
    }

    @Operation(summary = "清空头像")
    @OperationLog(type = OperationType.USER_CLEAR_AVATAR, module = "User", desc = "清除头像")
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
