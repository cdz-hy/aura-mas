package com.learning.service;

import com.learning.mapper.AiTokenUsageMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class AiTokenUsageService {

    private final AiTokenUsageMapper tokenUsageMapper;

    /**
     * 获取总览统计
     */
    public Map<String, Object> getSummary(String start, String end) {
        return tokenUsageMapper.selectSummary(start, end);
    }

    /**
     * 获取每日趋势（含调用次数）
     */
    public List<Map<String, Object>> getDailyTrend(String start, String end) {
        return tokenUsageMapper.selectDailyTrend(start, end);
    }

    /**
     * 按模型分组统计
     */
    public List<Map<String, Object>> getByModel(String start, String end) {
        return tokenUsageMapper.selectByModel(start, end);
    }

    /**
     * 按场景分组统计
     */
    public List<Map<String, Object>> getByScene(String start, String end) {
        return tokenUsageMapper.selectByScene(start, end);
    }

    /**
     * 用户消耗排行
     */
    public List<Map<String, Object>> getUserRanking(String start, String end, int limit) {
        return tokenUsageMapper.selectUserRanking(start, end, limit);
    }

    /**
     * 获取全部分析数据（一次性返回）
     */
    public Map<String, Object> getFullAnalysis(String start, String end) {
        Map<String, Object> result = new HashMap<>();
        result.put("summary", getSummary(start, end));
        result.put("dailyTrend", getDailyTrend(start, end));
        result.put("byModel", getByModel(start, end));
        result.put("byScene", getByScene(start, end));
        result.put("userRanking", getUserRanking(start, end, 10));
        return result;
    }

    /**
     * 分页查询原始记录
     */
    public Map<String, Object> getRecords(String start, String end, String model, String scene, int page, int size) {
        int offset = (page - 1) * size;
        List<Map<String, Object>> records = tokenUsageMapper.selectRecords(start, end, model, scene, offset, size);
        Long total = tokenUsageMapper.selectRecordsCount(start, end, model, scene);
        Map<String, Object> result = new HashMap<>();
        result.put("records", records);
        result.put("total", total != null ? total : 0);
        result.put("page", page);
        result.put("size", size);
        return result;
    }
}
