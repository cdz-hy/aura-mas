package com.learning.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.learning.entity.UserLearningProgress;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserLearningProgressMapper extends BaseMapper<UserLearningProgress> {
}
