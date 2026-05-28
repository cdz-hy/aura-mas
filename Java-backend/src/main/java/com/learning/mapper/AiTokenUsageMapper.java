package com.learning.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.learning.entity.AiTokenUsage;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

@Mapper
public interface AiTokenUsageMapper extends BaseMapper<AiTokenUsage> {

    Map<String, Object> selectSummary(@Param("start") String start, @Param("end") String end);

    List<Map<String, Object>> selectDailyTrend(@Param("start") String start, @Param("end") String end);

    List<Map<String, Object>> selectByModel(@Param("start") String start, @Param("end") String end);

    List<Map<String, Object>> selectByScene(@Param("start") String start, @Param("end") String end);

    List<Map<String, Object>> selectUserRanking(@Param("start") String start, @Param("end") String end, @Param("limit") int limit);

    List<Map<String, Object>> selectRecords(@Param("start") String start, @Param("end") String end, @Param("model") String model, @Param("scene") String scene, @Param("offset") int offset, @Param("size") int size);

    Long selectRecordsCount(@Param("start") String start, @Param("end") String end, @Param("model") String model, @Param("scene") String scene);
}
