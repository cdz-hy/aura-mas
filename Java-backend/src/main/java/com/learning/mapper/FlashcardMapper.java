package com.learning.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.learning.entity.Flashcard;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface FlashcardMapper extends BaseMapper<Flashcard> {
}
