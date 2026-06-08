package com.learning.service;

import com.qiniu.http.Response;
import com.qiniu.storage.BucketManager;
import com.qiniu.storage.UploadManager;
import com.qiniu.util.Auth;
import com.qiniu.util.StringMap;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.UUID;

@Slf4j
@Service
public class QiniuService {

    private final Auth qiniuAuth;
    private final UploadManager qiniuUploadManager;
    private final BucketManager qiniuBucketManager;
    private final String bucketName;
    private final String domain;

    public QiniuService(Auth qiniuAuth,
                        UploadManager qiniuUploadManager,
                        BucketManager qiniuBucketManager,
                        @Value("${qiniu.bucket-name}") String bucketName,
                        @Value("${qiniu.domain}") String domain) {
        this.qiniuAuth = qiniuAuth;
        this.qiniuUploadManager = qiniuUploadManager;
        this.qiniuBucketManager = qiniuBucketManager;
        this.bucketName = bucketName;
        this.domain = domain;
    }

    public String uploadFile(MultipartFile file, String directory) {
        try {
            String originalFilename = file.getOriginalFilename();
            String extension = "";
            if (originalFilename != null && originalFilename.contains(".")) {
                extension = originalFilename.substring(originalFilename.lastIndexOf("."));
            }
            String key = directory + "/" + UUID.randomUUID() + extension;

            String token = qiniuAuth.uploadToken(bucketName, key, 3600, new StringMap().put("returnBody",
                    "{\"key\":\"$(key)\",\"hash\":\"$(etag)\",\"size\":\"$(fsize)\",\"mimeType\":\"$(mimeType)\"}"));

            Response response = qiniuUploadManager.put(file.getInputStream(), key, token, null, file.getContentType());
            if (response.isOK()) {
                log.info("Qiniu upload success: {}", key);
                return getAccessUrl(key);
            } else {
                log.error("Qiniu upload failed: {}", response.error);
                throw new RuntimeException("七牛云上传失败: " + response.error);
            }
        } catch (Exception e) {
            log.error("Qiniu upload error", e);
            throw new RuntimeException("文件上传失败: " + e.getMessage());
        }
    }

    public String getAccessUrl(String key) {
        String base = domain.endsWith("/") ? domain.substring(0, domain.length() - 1) : domain;
        return base + "/" + key;
    }

    /**
     * 从完整 URL 中提取 Qiniu key 并删除文件
     */
    public void deleteByUrl(String url) {
        if (url == null || url.isEmpty()) return;
        String base = domain.endsWith("/") ? domain : domain + "/";
        if (!url.startsWith(base)) return;
        String key = url.substring(base.length());
        try {
            qiniuBucketManager.delete(bucketName, key);
            log.info("Qiniu delete success: {}", key);
        } catch (Exception e) {
            log.warn("Qiniu delete failed for key {}: {}", key, e.getMessage());
        }
    }
}
