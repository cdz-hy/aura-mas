package com.learning.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.learning.entity.KnowledgeNode;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface KnowledgeNodeMapper extends BaseMapper<KnowledgeNode> {
}
