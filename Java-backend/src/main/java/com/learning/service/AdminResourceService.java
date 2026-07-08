package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.learning.common.ErrorCode;
import com.learning.common.PageResult;
import com.learning.entity.ResourceLibrary;
import com.learning.exception.BusinessException;
import com.learning.mapper.ResourceLibraryMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class AdminResourceService {

    private final ResourceLibraryMapper resourceLibraryMapper;
    private final RestTemplate restTemplate;

    public AdminResourceService(ResourceLibraryMapper resourceLibraryMapper) {
        this.resourceLibraryMapper = resourceLibraryMapper;
        // 豆包生图较慢，需要更长超时（2分钟）
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10_000);
        factory.setReadTimeout(120_000);
        this.restTemplate = new RestTemplate(factory);
    }

    @Value("${python.backend.url:http://localhost:8002}")
    private String pythonBackendUrl;

    @Value("${internal.secret:change-this-internal-secret}")
    private String internalSecret;

    // ==================== CRUD ====================

    public PageResult<ResourceLibrary> list(int page, int size, String keyword,
                                             String contentType, Integer status) {
        LambdaQueryWrapper<ResourceLibrary> wrapper = new LambdaQueryWrapper<>();

        if (StringUtils.hasText(keyword)) {
            wrapper.like(ResourceLibrary::getTitle, keyword);
        }
        if (StringUtils.hasText(contentType)) {
            wrapper.eq(ResourceLibrary::getContentType, contentType);
        }
        if (status != null) {
            wrapper.eq(ResourceLibrary::getStatus, status);
        }

        wrapper.orderByDesc(ResourceLibrary::getCreatedAt);

        Page<ResourceLibrary> pageObj = resourceLibraryMapper.selectPage(
                new Page<>(page, size), wrapper);

        return PageResult.of(pageObj.getTotal(), page, size, pageObj.getRecords());
    }

    public ResourceLibrary getById(Long id) {
        ResourceLibrary resource = resourceLibraryMapper.selectById(id);
        if (resource == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND);
        }
        return resource;
    }

    public ResourceLibrary saveDraft(ResourceLibrary resource) {
        // 截断 title 防止超出数据库列宽
        if (resource.getTitle() != null && resource.getTitle().length() > 200) {
            resource.setTitle(resource.getTitle().substring(0, 200));
        }
        resource.setStatus(0); // 待审核
        resource.setCreatedAt(LocalDateTime.now());
        resource.setUpdatedAt(LocalDateTime.now());
        resource.setIsDeleted(0);
        resourceLibraryMapper.insert(resource);
        return resource;
    }

    public ResourceLibrary update(Long id, ResourceLibrary resource) {
        ResourceLibrary existing = getById(id);
        // 只更新允许修改的字段
        if (resource.getTitle() != null) {
            String title = resource.getTitle();
            existing.setTitle(title.length() > 200 ? title.substring(0, 200) : title);
        }
        if (resource.getContent() != null) {
            existing.setContent(resource.getContent());
        }
        if (resource.getImageUrl() != null) {
            existing.setImageUrl(resource.getImageUrl());
        }
        if (resource.getImageCaption() != null) {
            existing.setImageCaption(resource.getImageCaption());
        }
        existing.setUpdatedAt(LocalDateTime.now());
        resourceLibraryMapper.updateById(existing);
        return existing;
    }

    public void delete(Long id) {
        ResourceLibrary resource = getById(id);

        // 如果已入库，先删除 Qdrant 中的向量
        if (resource.getStatus() == 1 && resource.getQdrantDocId() != null) {
            try {
                deleteVectors(resource.getQdrantDocId());
            } catch (Exception e) {
                log.warn("删除 Qdrant 向量失败，继续删除元数据: doc_id={}, error={}",
                        resource.getQdrantDocId(), e.getMessage());
            }
        }

        resourceLibraryMapper.deleteById(id);
    }

    // ==================== 审核 ====================

    @Transactional
    public ResourceLibrary approve(Long id) {
        ResourceLibrary resource = getById(id);
        if (resource.getStatus() != 0) {
            throw new BusinessException(400, "只能审核待审核状态的资源");
        }

        // 分配 doc_id（用资源 id 作为 Qdrant 的 doc_id）
        Long docId = resource.getId();
        resource.setQdrantDocId(docId);

        // 调用 Python 后端入库
        Map<String, Object> result;
        if ("text".equals(resource.getContentType()) || "rich".equals(resource.getContentType())) {
            // text 和 rich 类型都是文本内容，走文本入库
            result = callPythonIngestText(resource.getTitle(), resource.getContent(), docId);
        } else {
            result = callPythonIngestImage(resource.getImageUrl(), resource.getImageCaption(), docId);
        }

        // 更新状态为已入库
        resource.setStatus(1);
        resource.setUpdatedAt(LocalDateTime.now());
        resourceLibraryMapper.updateById(resource);

        log.info("[资源库] 审核通过并入库: id={}, type={}, doc_id={}", id, resource.getContentType(), docId);
        return resource;
    }

    public ResourceLibrary reject(Long id) {
        ResourceLibrary resource = getById(id);
        if (resource.getStatus() != 0) {
            throw new BusinessException(400, "只能拒绝待审核状态的资源");
        }
        resource.setStatus(2);
        resource.setUpdatedAt(LocalDateTime.now());
        resourceLibraryMapper.updateById(resource);
        return resource;
    }

    // ==================== Python 后端调用 ====================

    private Map<String, Object> callPythonIngestText(String title, String content, Long docId) {
        String url = pythonBackendUrl + "/api/ai/admin/resource/ingest/text";
        Map<String, Object> body = new HashMap<>();
        body.put("title", title);
        body.put("content", content);
        body.put("doc_id", docId);
        return postToPython(url, body);
    }

    private Map<String, Object> callPythonIngestImage(String imageUrl, String imageCaption, Long docId) {
        String url = pythonBackendUrl + "/api/ai/admin/resource/ingest/image";
        Map<String, Object> body = new HashMap<>();
        body.put("image_url", imageUrl);
        body.put("image_caption", imageCaption);
        body.put("doc_id", docId);
        return postToPython(url, body);
    }

    private void deleteVectors(Long docId) {
        String url = pythonBackendUrl + "/api/ai/admin/resource/delete-vectors";
        Map<String, Object> body = new HashMap<>();
        body.put("doc_id", docId);
        postToPython(url, body);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> postToPython(String url, Map<String, Object> body) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-Service-Secret", internalSecret);

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        try {
            ResponseEntity<Map> response = restTemplate.exchange(
                    url, HttpMethod.POST, entity, Map.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                return response.getBody();
            }
            throw new BusinessException(500, "Python 后端调用失败: " + response.getStatusCode());
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            log.error("[资源库] 调用 Python 后端失败: url={}, error={}", url, e.getMessage());
            throw new BusinessException(500, "调用 Python 后端失败: " + e.getMessage());
        }
    }
}
