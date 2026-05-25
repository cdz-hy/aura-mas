package com.learning.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.UUID;

@Slf4j
@Service
public class FileService {

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    public String uploadFile(MultipartFile file, String directory) {
        try {
            String originalFilename = file.getOriginalFilename();
            String extension = "";
            if (originalFilename != null && originalFilename.contains(".")) {
                extension = originalFilename.substring(originalFilename.lastIndexOf("."));
            }
            String filename = UUID.randomUUID() + extension;

            Path dirPath = Paths.get(uploadDir, directory);
            Files.createDirectories(dirPath);

            Path filePath = dirPath.resolve(filename);
            Files.copy(file.getInputStream(), filePath, StandardCopyOption.REPLACE_EXISTING);

            String relativePath = directory + "/" + filename;
            log.info("File uploaded: {}", relativePath);
            return relativePath;
        } catch (IOException e) {
            log.error("File upload failed", e);
            throw new RuntimeException("文件上传失败: " + e.getMessage());
        }
    }

    public String getPresignedUrl(String objectName) {
        // 本地存储直接返回相对路径，前端可通过下载接口获取
        return "/api/admin/kb/download/" + objectName;
    }

    public InputStream getFile(String objectName) {
        try {
            Path filePath = Paths.get(uploadDir, objectName);
            return Files.newInputStream(filePath);
        } catch (IOException e) {
            log.error("Failed to get file: {}", objectName, e);
            throw new RuntimeException("文件获取失败");
        }
    }

    public void deleteFile(String objectName) {
        try {
            Path filePath = Paths.get(uploadDir, objectName);
            Files.deleteIfExists(filePath);
            log.info("File deleted: {}", objectName);
        } catch (IOException e) {
            log.error("Failed to delete file: {}", objectName, e);
        }
    }
}
