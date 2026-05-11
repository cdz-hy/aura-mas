package com.learning.config;

import com.qiniu.storage.BucketManager;
import com.qiniu.storage.Configuration;
import com.qiniu.storage.Region;
import com.qiniu.storage.UploadManager;
import com.qiniu.util.Auth;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;

@org.springframework.context.annotation.Configuration
public class QiniuConfig {

    @Value("${qiniu.access-key}")
    private String accessKey;

    @Value("${qiniu.secret-key}")
    private String secretKey;

    @Bean
    public Auth qiniuAuth() {
        return Auth.create(accessKey, secretKey);
    }

    @Bean
    public UploadManager qiniuUploadManager() {
        return new UploadManager(new Configuration(Region.autoRegion()));
    }

    @Bean
    public BucketManager qiniuBucketManager() {
        return new BucketManager(qiniuAuth(), new Configuration(Region.autoRegion()));
    }
}
