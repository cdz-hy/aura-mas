package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.common.ErrorCode;
import com.learning.entity.User;
import com.learning.entity.UserProfile;
import com.learning.exception.BusinessException;
import com.learning.mapper.UserMapper;
import com.learning.mapper.UserProfileMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserMapper userMapper;
    private final UserProfileMapper userProfileMapper;

    public User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException(ErrorCode.USER_NOT_FOUND);
        }
        user.setPassword(null);
        return user;
    }

    public User getUserByLoginName(String loginName) {
        return userMapper.selectOne(
                new LambdaQueryWrapper<User>().eq(User::getLoginName, loginName));
    }

    public void updateLastLoginTime(Long userId) {
        User user = new User();
        user.setId(userId);
        user.setLastLoginTime(LocalDateTime.now());
        userMapper.updateById(user);
    }

    public UserProfile getCurrentProfile(Long userId) {
        return userProfileMapper.selectOne(
                new LambdaQueryWrapper<UserProfile>()
                        .eq(UserProfile::getUserId, userId)
                        .eq(UserProfile::getIsCurrent, 1));
    }

    public void updateProfile(Long userId, UserProfile profile) {
        UserProfile existing = getCurrentProfile(userId);
        if (existing != null) {
            existing.setIsCurrent(0);
            userProfileMapper.updateById(existing);
        }

        UserProfile latest = userProfileMapper.selectOne(
                new LambdaQueryWrapper<UserProfile>()
                        .eq(UserProfile::getUserId, userId)
                        .orderByDesc(UserProfile::getVersion)
                        .last("LIMIT 1"));

        int maxVersion = (latest != null && latest.getVersion() != null) ? latest.getVersion() : 0;

        profile.setId(null);
        profile.setUserId(userId);
        profile.setVersion(maxVersion + 1);
        profile.setIsCurrent(1);
        profile.setCreatedAt(LocalDateTime.now());
        userProfileMapper.insert(profile);
    }
}
