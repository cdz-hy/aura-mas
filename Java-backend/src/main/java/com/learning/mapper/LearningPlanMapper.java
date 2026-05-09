package com.learning.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.learning.entity.LearningPlan;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface LearningPlanMapper extends BaseMapper<LearningPlan> {
}
