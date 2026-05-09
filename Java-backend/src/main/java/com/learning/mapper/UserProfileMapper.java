package com.learning.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.learning.entity.UserProfile;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserProfileMapper extends BaseMapper<UserProfile> {
}
