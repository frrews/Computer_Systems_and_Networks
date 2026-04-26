package com.csan.fileStorage.service;

import org.springframework.core.io.Resource;
import java.io.InputStream;
import java.util.List;
import java.util.Map;

public interface FileStorageService {
    void store(String path, InputStream inputStream);
    void copy(String sourcePath, String targetPath);
    Resource load(String path);
    List<String> listContents(String path);
    Map<String, Object> getMetadata(String path);
    void delete(String path);
    boolean exists(String path);
}