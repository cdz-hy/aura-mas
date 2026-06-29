package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.learning.common.ErrorCode;
import com.learning.entity.User;
import com.learning.entity.UserProfile;
import com.learning.exception.BusinessException;
import com.learning.mapper.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserMapper userMapper;
    private final UserProfileMapper userProfileMapper;
    private final LearningPlanMapper planMapper;
    private final LearningResourceMapper resourceMapper;
    private final ResourceGenerationTaskMapper taskMapper;
    private final NoteMapper noteMapper;
    private final NoteResourceRelMapper noteResourceRelMapper;
    private final AiDialogueMapper dialogueMapper;
    private final AiFeedbackMapper feedbackMapper;
    private final AiTokenUsageMapper tokenUsageMapper;
    private final QuizRecordMapper quizRecordMapper;
    private final LearningDurationMapper learningDurationMapper;
    private final UserLearningProgressMapper progressMapper;
    private final SystemLogMapper systemLogMapper;
    private final KnowledgeBaseMapper knowledgeBaseMapper;

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

    @Transactional
    public void deleteAccount(Long userId) {
        // Get all plan IDs owned by this user
        List<Long> planIds = planMapper.selectList(
                new LambdaQueryWrapper<com.learning.entity.LearningPlan>()
                        .eq(com.learning.entity.LearningPlan::getUserId, userId)
                        .select(com.learning.entity.LearningPlan::getId))
                .stream().map(com.learning.entity.LearningPlan::getId).toList();

        // Delete resources and tasks associated with user's plans
        if (!planIds.isEmpty()) {
            resourceMapper.delete(new LambdaQueryWrapper<com.learning.entity.LearningResource>()
                    .in(com.learning.entity.LearningResource::getPlanId, planIds));
            taskMapper.delete(new LambdaQueryWrapper<com.learning.entity.ResourceGenerationTask>()
                    .in(com.learning.entity.ResourceGenerationTask::getPlanId, planIds));
        }

        // Delete note-resource relations for user's notes
        List<Long> noteIds = noteMapper.selectList(
                new LambdaQueryWrapper<com.learning.entity.Note>()
                        .eq(com.learning.entity.Note::getUserId, userId)
                        .select(com.learning.entity.Note::getId))
                .stream().map(com.learning.entity.Note::getId).toList();
        if (!noteIds.isEmpty()) {
            noteResourceRelMapper.delete(new LambdaQueryWrapper<com.learning.entity.NoteResourceRel>()
                    .in(com.learning.entity.NoteResourceRel::getNoteId, noteIds));
        }

        // Delete user-owned data
        noteMapper.delete(new LambdaQueryWrapper<com.learning.entity.Note>()
                .eq(com.learning.entity.Note::getUserId, userId));
        dialogueMapper.delete(new LambdaQueryWrapper<com.learning.entity.AiDialogue>()
                .eq(com.learning.entity.AiDialogue::getUserId, userId));
        feedbackMapper.delete(new LambdaQueryWrapper<com.learning.entity.AiFeedback>()
                .eq(com.learning.entity.AiFeedback::getUserId, userId));
        tokenUsageMapper.delete(new LambdaQueryWrapper<com.learning.entity.AiTokenUsage>()
                .eq(com.learning.entity.AiTokenUsage::getUserId, userId));
        quizRecordMapper.delete(new LambdaQueryWrapper<com.learning.entity.QuizRecord>()
                .eq(com.learning.entity.QuizRecord::getUserId, userId));
        learningDurationMapper.delete(new LambdaQueryWrapper<com.learning.entity.LearningDuration>()
                .eq(com.learning.entity.LearningDuration::getUserId, userId));
        progressMapper.delete(new LambdaQueryWrapper<com.learning.entity.UserLearningProgress>()
                .eq(com.learning.entity.UserLearningProgress::getUserId, userId));
        systemLogMapper.delete(new LambdaQueryWrapper<com.learning.entity.SystemLog>()
                .eq(com.learning.entity.SystemLog::getUserId, userId));
        userProfileMapper.delete(new LambdaQueryWrapper<UserProfile>()
                .eq(UserProfile::getUserId, userId));
        knowledgeBaseMapper.delete(new LambdaQueryWrapper<com.learning.entity.KnowledgeBase>()
                .eq(com.learning.entity.KnowledgeBase::getUploadUserId, userId));

        // Delete plans
        planMapper.delete(new LambdaQueryWrapper<com.learning.entity.LearningPlan>()
                .eq(com.learning.entity.LearningPlan::getUserId, userId));

        // Finally soft-delete the user (set is_deleted + deletedAt in one shot)
        userMapper.update(null, new LambdaUpdateWrapper<User>()
                .eq(User::getId, userId)
                .set(User::getIsDeleted, 1)
                .set(User::getDeletedAt, LocalDateTime.now()));
    }

    @Transactional
    public void updateProfile(Long userId, UserProfile profile) {
        UserProfile existing = getCurrentProfile(userId);
        if (existing != null) {
            existing.setIsCurrent(0);
            userProfileMapper.updateById(existing);

            // 从旧版本继承未被本次更新的字段（age/gender/domain 由前端管理，Python 只更新 learningBehavior）
            if (profile.getAge() == null) profile.setAge(existing.getAge());
            if (profile.getGender() == null) profile.setGender(existing.getGender());
            if (profile.getDomain() == null) profile.setDomain(existing.getDomain());

            // learningBehavior JSON 字段级合并（只增不删）
            if (profile.getLearningBehavior() != null && existing.getLearningBehavior() != null) {
                profile.setLearningBehavior(
                        mergeLearningBehavior(existing.getLearningBehavior(), profile.getLearningBehavior()));
            }
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

    /**
     * 直接替换 learningBehavior（前端手动编辑用，不做 merge）
     */
    @Transactional
    public void replaceLearningBehavior(Long userId, String newBehaviorJson) {
        UserProfile existing = getCurrentProfile(userId);
        if (existing == null) return;

        existing.setIsCurrent(0);
        userProfileMapper.updateById(existing);

        UserProfile latest = userProfileMapper.selectOne(
                new LambdaQueryWrapper<UserProfile>()
                        .eq(UserProfile::getUserId, userId)
                        .orderByDesc(UserProfile::getVersion)
                        .last("LIMIT 1"));
        int maxVersion = (latest != null && latest.getVersion() != null) ? latest.getVersion() : 0;

        UserProfile newProfile = new UserProfile();
        newProfile.setId(null);
        newProfile.setUserId(userId);
        newProfile.setVersion(maxVersion + 1);
        newProfile.setIsCurrent(1);
        newProfile.setAge(existing.getAge());
        newProfile.setGender(existing.getGender());
        newProfile.setDomain(existing.getDomain());
        newProfile.setLearningBehavior(newBehaviorJson);
        newProfile.setUpdateReason("用户手动编辑");
        newProfile.setCreatedAt(LocalDateTime.now());
        userProfileMapper.insert(newProfile);
    }

    private static final Set<String> LIST_FIELDS = new HashSet<>(
            java.util.Arrays.asList("knowledge_base", "weak_areas", "interest_tags", "preferred_resource_types", "preferred_quiz_types"));

    /**
     * 合并 learningBehavior JSON：列表字段只增不删，标量字段新值覆盖旧值
     */
    private String mergeLearningBehavior(String oldJson, String newJson) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            ObjectNode oldNode = mapper.readValue(oldJson, ObjectNode.class);
            JsonNode newNode = mapper.readValue(newJson, JsonNode.class);

            Iterator<String> fields = newNode.fieldNames();
            while (fields.hasNext()) {
                String key = fields.next();
                JsonNode newValue = newNode.get(key);
                if (newValue.isNull()) continue;

                if (LIST_FIELDS.contains(key) && newValue.isArray()) {
                    // 列表字段：合并，只增不删
                    ArrayNode oldArray = oldNode.has(key) && oldNode.get(key).isArray()
                            ? (ArrayNode) oldNode.get(key) : mapper.createArrayNode();
                    Set<String> existing = new HashSet<>();
                    for (JsonNode item : oldArray) existing.add(item.asText());
                    for (JsonNode item : newValue) {
                        String text = item.asText();
                        if (!existing.contains(text)) {
                            oldArray.add(text);
                            existing.add(text);
                        }
                    }
                    oldNode.set(key, oldArray);
                } else {
                    // 标量字段：直接覆盖
                    oldNode.set(key, newValue);
                }
            }
            return mapper.writeValueAsString(oldNode);
        } catch (Exception e) {
            // JSON 解析失败时返回新值（保守策略）
            return newJson;
        }
    }
}
