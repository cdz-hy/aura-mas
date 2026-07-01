package com.learning.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.learning.annotation.OperationLog;
import com.learning.common.ErrorCode;
import com.learning.common.OperationType;
import com.learning.common.PageResult;
import com.learning.common.Result;
import com.learning.entity.User;
import com.learning.exception.BusinessException;
import com.learning.mapper.UserMapper;
import com.learning.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Tag(name = "管理员-用户管理")
@RestController
@RequestMapping("/api/admin/users")
@RequiredArgsConstructor
public class AdminUserController {

    private final UserMapper userMapper;
    private final UserService userService;
    private final PasswordEncoder passwordEncoder;

    @Operation(summary = "分页查询用户列表")
    @GetMapping
    public Result<PageResult<User>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String role,
            @RequestParam(required = false) Integer status) {

        LambdaQueryWrapper<User> wrapper = new LambdaQueryWrapper<>();

        if (StringUtils.hasText(keyword)) {
            wrapper.and(w -> w
                    .like(User::getLoginName, keyword)
                    .or().like(User::getNickname, keyword)
                    .or().like(User::getEmail, keyword));
        }
        if (StringUtils.hasText(role)) {
            wrapper.eq(User::getRole, role);
        }
        if (status != null) {
            wrapper.eq(User::getStatus, status);
        }

        wrapper.orderByDesc(User::getCreatedAt);

        Page<User> pageObj = userMapper.selectPage(new Page<>(page, size), wrapper);
        List<User> records = pageObj.getRecords().stream().peek(u -> u.setPassword(null)).toList();

        return Result.success(PageResult.of(pageObj.getTotal(), page, size, records));
    }

    @Operation(summary = "获取用户详情")
    @GetMapping("/{id}")
    public Result<User> getById(@PathVariable Long id) {
        User user = userService.getUserById(id);
        return Result.success(user);
    }

    @Operation(summary = "新增用户")
    @OperationLog(type = OperationType.ADMIN_CREATE_USER, module = "UserAdmin",
            desc = "'管理员创建用户: ' + #body.get('loginName')",
            resourceId = "#result?.data?.id?.toString()")
    @PostMapping
    public Result<User> create(@RequestBody Map<String, Object> body) {
        String loginName = (String) body.get("loginName");
        String password = (String) body.get("password");
        String nickname = (String) body.get("nickname");
        String email = (String) body.get("email");
        String role = (String) body.getOrDefault("role", "student");
        Integer status = (Integer) body.getOrDefault("status", 1);

        if (!StringUtils.hasText(loginName) || !StringUtils.hasText(password)) {
            throw new BusinessException(ErrorCode.BAD_REQUEST.getCode(), "登录名和密码不能为空");
        }

        if (userService.getUserByLoginName(loginName) != null) {
            throw new BusinessException(ErrorCode.USER_ALREADY_EXISTS);
        }

        User user = new User();
        user.setLoginName(loginName);
        user.setPassword(passwordEncoder.encode(password));
        user.setNickname(StringUtils.hasText(nickname) ? nickname : loginName);
        user.setEmail(email);
        user.setRole(role);
        user.setStatus(status);
        user.setCreatedAt(LocalDateTime.now());

        userMapper.insert(user);
        user.setPassword(null);
        return Result.success(user);
    }

    @Operation(summary = "更新用户信息")
    @OperationLog(type = OperationType.ADMIN_UPDATE_USER, module = "UserAdmin",
            desc = "'管理员更新用户ID: ' + #id",
            resourceId = "#id?.toString()")
    @PutMapping("/{id}")
    public Result<User> update(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        User user = userMapper.selectById(id);
        if (user == null) {
            throw new BusinessException(ErrorCode.USER_NOT_FOUND);
        }

        if (body.containsKey("nickname")) {
            user.setNickname((String) body.get("nickname"));
        }
        if (body.containsKey("email")) {
            user.setEmail((String) body.get("email"));
        }
        if (body.containsKey("role")) {
            user.setRole((String) body.get("role"));
        }
        if (body.containsKey("status")) {
            user.setStatus((Integer) body.get("status"));
        }
        if (body.containsKey("password") && StringUtils.hasText((String) body.get("password"))) {
            user.setPassword(passwordEncoder.encode((String) body.get("password")));
        }

        userMapper.updateById(user);
        user.setPassword(null);
        return Result.success(user);
    }

    @Operation(summary = "删除用户")
    @OperationLog(type = OperationType.ADMIN_DELETE_USER, module = "UserAdmin",
            desc = "'管理员删除用户ID: ' + #id",
            resourceId = "#id?.toString()")
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        userService.deleteAccount(id);
        return Result.success();
    }

    @Operation(summary = "切换用户状态（启用/禁用）")
    @OperationLog(type = OperationType.ADMIN_TOGGLE_STATUS, module = "UserAdmin",
            desc = "'管理员切换用户状态ID: ' + #id",
            resourceId = "#id?.toString()")
    @PutMapping("/{id}/status")
    public Result<Void> toggleStatus(@PathVariable Long id) {
        User user = userMapper.selectById(id);
        if (user == null) {
            throw new BusinessException(ErrorCode.USER_NOT_FOUND);
        }
        user.setStatus(user.getStatus() == 1 ? 0 : 1);
        userMapper.updateById(user);
        return Result.success();
    }

    @Operation(summary = "修改用户角色")
    @OperationLog(type = OperationType.ADMIN_CHANGE_ROLE, module = "UserAdmin",
            desc = "'管理员修改用户角色ID: ' + #id + ' -> ' + #body.get('role')",
            resourceId = "#id?.toString()")
    @PutMapping("/{id}/role")
    public Result<Void> changeRole(@PathVariable Long id, @RequestBody Map<String, String> body) {
        User user = userMapper.selectById(id);
        if (user == null) {
            throw new BusinessException(ErrorCode.USER_NOT_FOUND);
        }
        String newRole = body.get("role");
        if (!"admin".equals(newRole) && !"student".equals(newRole)) {
            throw new BusinessException(ErrorCode.BAD_REQUEST.getCode(), "角色只能是 admin 或 student");
        }
        user.setRole(newRole);
        userMapper.updateById(user);
        return Result.success();
    }

    @Operation(summary = "批量切换状态")
    @OperationLog(type = OperationType.ADMIN_BATCH_TOGGLE_STATUS, module = "UserAdmin",
            desc = "'管理员批量切换状态: ' + #body.get('ids')")
    @PutMapping("/batch/status")
    public Result<Void> batchToggleStatus(@RequestBody Map<String, Object> body) {
        @SuppressWarnings("unchecked")
        List<Integer> ids = (List<Integer>) body.get("ids");
        Integer status = (Integer) body.get("status");

        if (ids == null || ids.isEmpty() || status == null) {
            throw new BusinessException(ErrorCode.BAD_REQUEST.getCode(), "参数不完整");
        }

        for (Integer id : ids) {
            User user = userMapper.selectById(id.longValue());
            if (user != null) {
                user.setStatus(status);
                userMapper.updateById(user);
            }
        }
        return Result.success();
    }

    @Operation(summary = "批量删除")
    @OperationLog(type = OperationType.ADMIN_BATCH_DELETE_USER, module = "UserAdmin",
            desc = "'管理员批量删除用户: ' + #body.get('ids')")
    @DeleteMapping("/batch")
    public Result<Void> batchDelete(@RequestBody Map<String, Object> body) {
        @SuppressWarnings("unchecked")
        List<Integer> ids = (List<Integer>) body.get("ids");

        if (ids == null || ids.isEmpty()) {
            throw new BusinessException(ErrorCode.BAD_REQUEST.getCode(), "请选择要删除的用户");
        }

        for (Integer id : ids) {
            userService.deleteAccount(id.longValue());
        }
        return Result.success();
    }
}
