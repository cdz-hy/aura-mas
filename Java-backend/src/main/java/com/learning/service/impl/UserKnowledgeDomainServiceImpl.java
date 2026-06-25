package com.learning.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.learning.entity.UserKnowledgeDomain;
import com.learning.mapper.UserKnowledgeDomainMapper;
import com.learning.service.UserKnowledgeDomainService;
import org.springframework.stereotype.Service;

@Service
public class UserKnowledgeDomainServiceImpl extends ServiceImpl<UserKnowledgeDomainMapper, UserKnowledgeDomain> implements UserKnowledgeDomainService {
}
