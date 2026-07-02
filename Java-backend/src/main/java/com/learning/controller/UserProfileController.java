package com.learning.controller;

import com.learning.common.Result;
import com.learning.entity.UserProfile;
import com.learning.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Tag(name = "用户画像")
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class UserProfileController {

    private final UserService userService;

    @Operation(summary = "获取当前用户画像")
    @GetMapping("/user/profile/current")
    public Result<UserProfile> getCurrentProfile(Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        return Result.success(userService.getCurrentProfile(userId));
    }

    @Operation(summary = "内部接口：按userId获取画像")
    @GetMapping("/internal/profile/current")
    public Result<UserProfile> getCurrentProfileInternal(@RequestParam Long userId) {
        return Result.success(userService.getCurrentProfile(userId));
    }

    @Operation(summary = "内部接口：更新用户画像")
    @PutMapping("/internal/profile")
    public Result<Void> updateProfileInternal(@RequestBody Map<String, Object> body) {
        Long userId = Long.valueOf(body.get("userId").toString());
        String learningBehavior = (String) body.get("learningBehavior");
        String updateReason = (String) body.get("updateReason");

        UserProfile profile = new UserProfile();
        profile.setLearningBehavior(learningBehavior);
        profile.setUpdateReason(updateReason != null ? updateReason : "ai_update");

        userService.updateProfile(userId, profile);
        return Result.success();
    }

    @Operation(summary = "内部接口：增量更新用户学习画像")
    @PutMapping("/internal/profile/incremental")
    public Result<Void> updateProfileIncremental(@RequestBody Map<String, Object> body) {
        Long userId = Long.valueOf(body.get("userId").toString());
        @SuppressWarnings("unchecked")
        Map<String, Object> updates = (Map<String, Object>) body.get("updates");
        String updateReason = (String) body.get("updateReason");

        userService.updateProfileIncremental(userId, updates, updateReason != null ? updateReason : "profile_bubble_survey");
        return Result.success();
    }

    @Operation(summary = "当前用户增量更新学习画像（JWT 认证）")
    @PutMapping("/profile/incremental")
    public Result<Void> updateMyProfileIncremental(Authentication authentication,
                                                     @RequestBody Map<String, Object> body) {
        Long userId = (Long) authentication.getPrincipal();
        @SuppressWarnings("unchecked")
        Map<String, Object> updates = (Map<String, Object>) body.get("updates");
        String updateReason = (String) body.get("updateReason");

        userService.updateProfileIncremental(userId, updates, updateReason != null ? updateReason : "profile_bubble_survey");
        return Result.success();
    }
}
