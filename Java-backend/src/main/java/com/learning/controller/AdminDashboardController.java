package com.learning.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.common.PageResult;
import com.learning.common.Result;
import com.learning.entity.KnowledgeBase;
import com.learning.entity.LearningPlan;
import com.learning.entity.User;
import com.learning.mapper.AiTokenUsageMapper;
import com.learning.mapper.KnowledgeBaseMapper;
import com.learning.mapper.LearningPlanMapper;
import com.learning.mapper.UserMapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Tag(name = "管理员-仪表盘")
@RestController
@RequestMapping("/api/admin/dashboard")
@RequiredArgsConstructor
public class AdminDashboardController {

    private final UserMapper userMapper;
    private final LearningPlanMapper planMapper;
    private final KnowledgeBaseMapper kbMapper;
    private final AiTokenUsageMapper tokenMapper;
    private final JdbcTemplate jdbcTemplate;

    @Operation(summary = "获取管理员仪表盘统计数据")
    @GetMapping("/stats")
    public Result<Map<String, Object>> getStats() {
        Map<String, Object> data = new HashMap<>();

        // 用户统计
        long totalUsers = userMapper.selectCount(
                new LambdaQueryWrapper<User>().eq(User::getIsDeleted, 0));
        long activeUsers = userMapper.selectCount(
                new LambdaQueryWrapper<User>().eq(User::getStatus, 1).eq(User::getIsDeleted, 0));

        // 学习计划统计
        long totalPlans = planMapper.selectCount(
                new LambdaQueryWrapper<LearningPlan>().eq(LearningPlan::getIsDeleted, 0));
        long activePlans = planMapper.selectCount(
                new LambdaQueryWrapper<LearningPlan>()
                        .eq(LearningPlan::getStatus, 3).eq(LearningPlan::getIsDeleted, 0));

        // 知识库统计
        long totalKBDocs = kbMapper.selectCount(
                new LambdaQueryWrapper<KnowledgeBase>().eq(KnowledgeBase::getIsDeleted, 0));

        // 今日 AI 调用统计
        String todayStart = LocalDate.now().atStartOfDay().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        String todayEnd = LocalDate.now().plusDays(1).atStartOfDay().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        Map<String, Object> todaySummary = tokenMapper.selectSummary(todayStart, todayEnd);
        long todayAICalls = todaySummary != null && todaySummary.get("totalCalls") != null
                ? ((Number) todaySummary.get("totalCalls")).longValue() : 0;
        long todayTokens = todaySummary != null && todaySummary.get("totalTokens") != null
                ? ((Number) todaySummary.get("totalTokens")).longValue() : 0;

        data.put("totalUsers", totalUsers);
        data.put("activeUsers", activeUsers);
        data.put("totalPlans", totalPlans);
        data.put("activePlans", activePlans);
        data.put("totalKBDocs", totalKBDocs);
        data.put("todayAICalls", todayAICalls);
        data.put("todayTokens", todayTokens);

        return Result.success(data);
    }

    @Operation(summary = "获取最近系统日志")
    @GetMapping("/logs")
    public Result<List<Map<String, Object>>> getRecentLogs() {
        String sql = """
                SELECT sl.id, sl.user_id, sl.operation_type, sl.operation_desc,
                       sl.module, sl.status, sl.user_ip, sl.created_at,
                       u.login_name
                FROM system_log sl
                LEFT JOIN `user` u ON u.id = sl.user_id
                ORDER BY sl.id DESC
                LIMIT 15
                """;

        List<Map<String, Object>> result = jdbcTemplate.queryForList(sql);
        return Result.success(result);
    }

    @Operation(summary = "分页查询系统日志")
    @GetMapping("/logs/page")
    public Result<PageResult<Map<String, Object>>> getLogsPage(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String module,
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String startDate,
            @RequestParam(required = false) String endDate) {

        StringBuilder where = new StringBuilder(" WHERE 1=1");
        List<Object> params = new ArrayList<>();

        if (StringUtils.hasText(module)) {
            where.append(" AND sl.module = ?");
            params.add(module);
        }
        if (status != null) {
            where.append(" AND sl.status = ?");
            params.add(status);
        }
        if (StringUtils.hasText(keyword)) {
            where.append(" AND (sl.operation_desc LIKE ? OR sl.operation_type LIKE ? OR u.login_name LIKE ?)");
            String kw = "%" + keyword + "%";
            params.add(kw);
            params.add(kw);
            params.add(kw);
        }
        if (StringUtils.hasText(startDate)) {
            where.append(" AND sl.created_at >= ?");
            params.add(startDate);
        }
        if (StringUtils.hasText(endDate)) {
            where.append(" AND sl.created_at <= ?");
            params.add(endDate);
        }

        // Count
        String countSql = "SELECT COUNT(*) FROM system_log sl LEFT JOIN `user` u ON u.id = sl.user_id" + where;
        Long total = jdbcTemplate.queryForObject(countSql, Long.class, params.toArray());
        if (total == null) total = 0L;

        // Data
        int offset = (page - 1) * size;
        String dataSql = """
                SELECT sl.id, sl.user_id, sl.operation_type, sl.operation_desc,
                       sl.module, sl.status, sl.user_ip, sl.error_msg, sl.created_at,
                       u.login_name
                FROM system_log sl
                LEFT JOIN `user` u ON u.id = sl.user_id
                """ + where + " ORDER BY sl.id DESC LIMIT ? OFFSET ?";
        List<Object> dataParams = new ArrayList<>(params);
        dataParams.add(size);
        dataParams.add(offset);
        List<Map<String, Object>> records = jdbcTemplate.queryForList(dataSql, dataParams.toArray());

        return Result.success(PageResult.of(total, page, size, records));
    }

    @Operation(summary = "获取日志统计概览")
    @GetMapping("/logs/stats")
    public Result<Map<String, Object>> getLogStats() {
        Map<String, Object> stats = new HashMap<>();

        // 总数
        Long total = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM system_log", Long.class);
        stats.put("total", total != null ? total : 0);

        // 今日新增
        String today = LocalDate.now().atStartOfDay().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        Long todayCount = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM system_log WHERE created_at >= ?", Long.class, today);
        stats.put("todayCount", todayCount != null ? todayCount : 0);

        // 失败数
        Long failCount = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM system_log WHERE status = 0", Long.class);
        stats.put("failCount", failCount != null ? failCount : 0);

        // 模块分布
        List<Map<String, Object>> moduleDist = jdbcTemplate.queryForList(
                "SELECT module, COUNT(*) AS count FROM system_log WHERE module IS NOT NULL GROUP BY module ORDER BY count DESC");
        stats.put("moduleDistribution", moduleDist);

        return Result.success(stats);
    }
}
