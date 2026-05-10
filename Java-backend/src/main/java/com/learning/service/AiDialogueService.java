package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.entity.AiDialogue;
import com.learning.entity.LearningPlan;
import com.learning.mapper.AiDialogueMapper;
import com.learning.mapper.LearningPlanMapper;
import com.learning.mapper.LearningResourceMapper;
import com.learning.mapper.UserLearningProgressMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AiDialogueService {

    private final AiDialogueMapper dialogueMapper;
    private final LearningPlanMapper planMapper;
    private final LearningResourceMapper resourceMapper;
    private final UserLearningProgressMapper progressMapper;

    @Transactional
    public AiDialogue createDialogue(Long userId, String sessionId, Long planId,
                                     String conversationText, String dialogueType, String intentType) {
        AiDialogue dialogue = new AiDialogue();
        dialogue.setUserId(userId);
        dialogue.setSessionId(sessionId);
        dialogue.setPlanId(planId);
        dialogue.setConversationText(conversationText);
        dialogue.setDialogueType(dialogueType);
        dialogue.setIntentType(intentType);
        dialogue.setDialogueTime(LocalDateTime.now());
        dialogueMapper.insert(dialogue);
        return dialogue;
    }

    public List<AiDialogue> getHistory(Long userId, Long planId, String intentType, int limit) {
        LambdaQueryWrapper<AiDialogue> wrapper = new LambdaQueryWrapper<AiDialogue>()
                .eq(AiDialogue::getUserId, userId)
                .eq(planId != null, AiDialogue::getPlanId, planId)
                .eq(intentType != null, AiDialogue::getIntentType, intentType)
                .orderByDesc(AiDialogue::getId)
                .last("LIMIT " + limit);
        return dialogueMapper.selectList(wrapper);
    }

    public List<AiDialogue> getHistoryBySession(String sessionId, Long planId, int limit) {
        LambdaQueryWrapper<AiDialogue> wrapper = new LambdaQueryWrapper<AiDialogue>()
                .eq(AiDialogue::getSessionId, sessionId)
                .eq(planId != null, AiDialogue::getPlanId, planId)
                .orderByAsc(AiDialogue::getId)
                .last("LIMIT " + limit);
        return dialogueMapper.selectList(wrapper);
    }

    public List<AiDialogue> getHistoryByPlan(Long userId, Long planId, int limit) {
        LambdaQueryWrapper<AiDialogue> wrapper = new LambdaQueryWrapper<AiDialogue>()
                .eq(AiDialogue::getUserId, userId)
                .eq(AiDialogue::getPlanId, planId)
                .orderByAsc(AiDialogue::getId)
                .last("LIMIT " + limit);
        return dialogueMapper.selectList(wrapper);
    }

    public List<AiDialogue> getHistoryBySession(String sessionId, int limit) {
        LambdaQueryWrapper<AiDialogue> wrapper = new LambdaQueryWrapper<AiDialogue>()
                .eq(AiDialogue::getSessionId, sessionId)
                .orderByAsc(AiDialogue::getId)
                .last("LIMIT " + limit);
        return dialogueMapper.selectList(wrapper);
    }

    public List<Map<String, Object>> getSessionList(Long userId, String intentType, Long planId) {
        // Get all dialogues for this user+intent+plan, grouped by session
        LambdaQueryWrapper<AiDialogue> wrapper = new LambdaQueryWrapper<AiDialogue>()
                .eq(AiDialogue::getUserId, userId)
                .eq(intentType != null, AiDialogue::getIntentType, intentType)
                .eq(planId != null, AiDialogue::getPlanId, planId)
                .orderByDesc(AiDialogue::getId);
        List<AiDialogue> all = dialogueMapper.selectList(wrapper);

        // Group by sessionId, compute metadata
        Map<String, List<AiDialogue>> grouped = all.stream()
                .collect(Collectors.groupingBy(AiDialogue::getSessionId,
                        LinkedHashMap::new, Collectors.toList()));

        List<Map<String, Object>> sessions = new ArrayList<>();
        for (Map.Entry<String, List<AiDialogue>> entry : grouped.entrySet()) {
            List<AiDialogue> msgs = entry.getValue();
            // First user message as title
            String title = msgs.stream()
                    .filter(d -> "USER".equals(d.getDialogueType()))
                    .map(AiDialogue::getConversationText)
                    .findFirst()
                    .orElse("新对话");
            if (title.length() > 50) title = title.substring(0, 50) + "...";

            Map<String, Object> session = new LinkedHashMap<>();
            session.put("sessionId", entry.getKey());
            session.put("intentType", intentType);
            session.put("planId", planId);
            session.put("title", title);
            session.put("messageCount", msgs.size());
            session.put("createdAt", msgs.get(msgs.size() - 1).getDialogueTime());
            session.put("lastMessageAt", msgs.get(0).getDialogueTime());
            sessions.add(session);
        }
        return sessions;
    }

    @Transactional
    public void updateResourceId(Long dialogueId, Long resourceId) {
        AiDialogue dialogue = dialogueMapper.selectById(dialogueId);
        if (dialogue != null) {
            dialogue.setResourceId(resourceId);
            dialogueMapper.updateById(dialogue);
        }
    }

    @Transactional
    public void linkSessionToPlan(String sessionId, Long planId) {
        LambdaQueryWrapper<AiDialogue> wrapper = new LambdaQueryWrapper<AiDialogue>()
                .eq(AiDialogue::getSessionId, sessionId)
                .isNull(AiDialogue::getPlanId);
        List<AiDialogue> dialogues = dialogueMapper.selectList(wrapper);
        for (AiDialogue d : dialogues) {
            d.setPlanId(planId);
            dialogueMapper.updateById(d);
        }
    }

    @Transactional
    public void deleteBySession(String sessionId) {
        // Get all dialogues in this session to find associated plan
        LambdaQueryWrapper<AiDialogue> wrapper = new LambdaQueryWrapper<AiDialogue>()
                .eq(AiDialogue::getSessionId, sessionId);
        List<AiDialogue> dialogues = dialogueMapper.selectList(wrapper);

        if (dialogues.isEmpty()) return;

        // Soft-delete all dialogues in this session
        LocalDateTime now = LocalDateTime.now();
        for (AiDialogue d : dialogues) {
            d.setIsDeleted(1);
            d.setDeletedAt(now);
            dialogueMapper.updateById(d);
        }

        // If intent_type is "profile", also delete associated plan + resources
        String intentType = dialogues.get(0).getIntentType();
        if ("profile".equals(intentType)) {
            Long planId = dialogues.stream()
                    .map(AiDialogue::getPlanId)
                    .filter(Objects::nonNull)
                    .findFirst()
                    .orElse(null);
            if (planId != null) {
                cascadeDeletePlan(planId);
            }
        }
    }

    private void cascadeDeletePlan(Long planId) {
        // Soft-delete plan
        LearningPlan plan = planMapper.selectById(planId);
        if (plan != null) {
            plan.setIsDeleted(1);
            plan.setDeletedAt(LocalDateTime.now());
            planMapper.updateById(plan);
        }
        // Resources are cascade-deleted via is_deleted on learning_resource table
        // (MyBatis-Plus @TableLogic handles this if configured)
    }

    public String getSessionTitle(String sessionId) {
        LambdaQueryWrapper<AiDialogue> wrapper = new LambdaQueryWrapper<AiDialogue>()
                .eq(AiDialogue::getSessionId, sessionId)
                .eq(AiDialogue::getDialogueType, "USER")
                .orderByAsc(AiDialogue::getId)
                .last("LIMIT 1");
        AiDialogue first = dialogueMapper.selectOne(wrapper);
        if (first == null) return "新对话";
        String title = first.getConversationText();
        return title.length() > 50 ? title.substring(0, 50) + "..." : title;
    }
}
