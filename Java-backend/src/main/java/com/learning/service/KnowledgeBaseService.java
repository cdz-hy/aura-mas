package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.learning.common.PageResult;
import com.learning.entity.KnowledgeBase;
import com.learning.mapper.KnowledgeBaseMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class KnowledgeBaseService {

    private final KnowledgeBaseMapper knowledgeBaseMapper;

    @Transactional
    public KnowledgeBase createKnowledgeBase(KnowledgeBase kb) {
        kb.setUploadTime(LocalDateTime.now());
        kb.setParseStatus(0);
        knowledgeBaseMapper.insert(kb);
        return kb;
    }

    public KnowledgeBase getById(Long id) {
        return knowledgeBaseMapper.selectById(id);
    }

    public PageResult<KnowledgeBase> getList(int page, int size) {
        Page<KnowledgeBase> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<KnowledgeBase> wrapper = new LambdaQueryWrapper<KnowledgeBase>()
                .orderByDesc(KnowledgeBase::getUploadTime);

        Page<KnowledgeBase> result = knowledgeBaseMapper.selectPage(pageParam, wrapper);
        return PageResult.of(result.getTotal(), page, size, result.getRecords());
    }

    @Transactional
    public void updateParseStatus(Long id, Integer status, Integer chunkCount) {
        KnowledgeBase kb = knowledgeBaseMapper.selectById(id);
        if (kb != null) {
            kb.setParseStatus(status);
            if (chunkCount != null) {
                kb.setChunkCount(chunkCount);
            }
            knowledgeBaseMapper.updateById(kb);
        }
    }

    @Transactional
    public void updateStatus(Long id, Integer status, Integer chunkCount, String mineruTaskId, String collectionName) {
        KnowledgeBase kb = knowledgeBaseMapper.selectById(id);
        if (kb != null) {
            if (status != null) kb.setParseStatus(status);
            if (chunkCount != null) kb.setChunkCount(chunkCount);
            if (mineruTaskId != null) kb.setMineruTaskId(mineruTaskId);
            if (collectionName != null) kb.setCollectionName(collectionName);
            knowledgeBaseMapper.updateById(kb);
        }
    }

    public List<KnowledgeBase> getIndexedDocuments() {
        LambdaQueryWrapper<KnowledgeBase> wrapper = new LambdaQueryWrapper<KnowledgeBase>()
                .eq(KnowledgeBase::getParseStatus, 2)
                .orderByDesc(KnowledgeBase::getUploadTime);
        return knowledgeBaseMapper.selectList(wrapper);
    }

    @Transactional
    public void deleteById(Long id) {
        knowledgeBaseMapper.deleteById(id);
    }
}
