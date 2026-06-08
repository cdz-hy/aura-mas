package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.common.ErrorCode;
import com.learning.dto.LoginRequest;
import com.learning.dto.LoginResponse;
import com.learning.dto.MenuNode;
import com.learning.dto.RegisterRequest;
import com.learning.entity.User;
import com.learning.exception.BusinessException;
import com.learning.mapper.UserMapper;
import com.learning.security.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;
    private final MenuService menuService;

    @Transactional
    public LoginResponse register(RegisterRequest request) {
        User existing = userMapper.selectOne(
                new LambdaQueryWrapper<User>().eq(User::getLoginName, request.getLoginName()));
        if (existing != null) {
            throw new BusinessException(ErrorCode.USER_ALREADY_EXISTS);
        }

        User user = new User();
        user.setLoginName(request.getLoginName());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setNickname(request.getNickname() != null ? request.getNickname() : request.getLoginName());
        user.setEmail(request.getEmail());
        user.setRole("student");
        user.setStatus(1);
        user.setCreatedAt(LocalDateTime.now());
        userMapper.insert(user);

        String token = jwtTokenProvider.generateToken(user.getId(), user.getLoginName(), user.getRole());
        List<MenuNode> menus = menuService.getMenuTreeByRole(user.getRole());

        return LoginResponse.builder()
                .token(token)
                .user(buildUserDTO(user))
                .menus(menus)
                .build();
    }

    public LoginResponse login(LoginRequest request) {
        User user = userMapper.selectOne(
                new LambdaQueryWrapper<User>().eq(User::getLoginName, request.getLoginName()));

        if (user == null) {
            throw new BusinessException(ErrorCode.USER_NOT_FOUND);
        }

        if (user.getStatus() != 1) {
            throw new BusinessException(ErrorCode.ACCOUNT_DISABLED);
        }

        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new BusinessException(ErrorCode.PASSWORD_ERROR);
        }

        user.setLastLoginTime(LocalDateTime.now());
        userMapper.updateById(user);

        String token = jwtTokenProvider.generateToken(user.getId(), user.getLoginName(), user.getRole());
        List<MenuNode> menus = menuService.getMenuTreeByRole(user.getRole());

        return LoginResponse.builder()
                .token(token)
                .user(buildUserDTO(user))
                .menus(menus)
                .build();
    }

    private LoginResponse.UserDTO buildUserDTO(User user) {
        return LoginResponse.UserDTO.builder()
                .id(user.getId())
                .loginName(user.getLoginName())
                .nickname(user.getNickname())
                .email(user.getEmail())
                .avatarUrl(user.getAvatarUrl())
                .role(user.getRole())
                .build();
    }
}
