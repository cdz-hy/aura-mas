package com.learning.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.learning.entity.ResourceLibrary;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface ResourceLibraryMapper extends BaseMapper<ResourceLibrary> {
}
