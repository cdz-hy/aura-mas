package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.learning.common.ErrorCode;
import com.learning.entity.User;
import com.learning.entity.UserProfile;
import com.learning.exception.BusinessException;
import com.learning.mapper.UserMapper;
import com.learning.mapper.UserProfileMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;

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

    public User updateUserInfo(Long userId, Map<String, Object> updates) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException(ErrorCode.USER_NOT_FOUND);
        }
        if (updates.containsKey("nickname") && updates.get("nickname") != null) {
            user.setNickname((String) updates.get("nickname"));
        }
        if (updates.containsKey("email") && updates.get("email") != null) {
            user.setEmail((String) updates.get("email"));
        }
        userMapper.updateById(user);
        user.setPassword(null);
        return user;
    }

    public void updateAvatar(Long userId, String avatarUrl) {
        User user = new User();
        user.setId(userId);
        user.setAvatarUrl(avatarUrl);
        userMapper.updateById(user);
    }

    public String clearAvatar(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException(ErrorCode.USER_NOT_FOUND);
        }
        String oldUrl = user.getAvatarUrl();
        // MyBatis-Plus updateById 默认忽略 null 字段，必须用 LambdaUpdateWrapper 显式置空
        userMapper.update(null, new LambdaUpdateWrapper<User>()
                .eq(User::getId, userId)
                .set(User::getAvatarUrl, null));
        return oldUrl;
    }

    public void updateProfile(Long userId, UserProfile profile) {
        UserProfile existing = getCurrentProfile(userId);
        if (existing != null) {
            existing.setIsCurrent(0);
            userProfileMapper.updateById(existing);

            // 从旧版本继承未被本次更新的字段（age/gender/domain 由前端管理，Python 只更新 learningBehavior）
            if (profile.getAge() == null) profile.setAge(existing.getAge());
            if (profile.getGender() == null) profile.setGender(existing.getGender());
            if (profile.getDomain() == null) profile.setDomain(existing.getDomain());
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
