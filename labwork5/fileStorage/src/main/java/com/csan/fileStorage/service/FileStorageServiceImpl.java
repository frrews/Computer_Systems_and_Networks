package com.csan.fileStorage.service;


import com.csan.fileStorage.exception.StorageException;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.util.FileSystemUtils;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetAddress;
import java.nio.file.*;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class FileStorageServiceImpl implements FileStorageService {

    @Value("${storage.root}")
    private String rootPath;

    private Path root;

    @PostConstruct
    public void init() {
        this.root = Paths.get(rootPath);
        try {
            Files.createDirectories(root);
        } catch (IOException e) {
            throw new RuntimeException("Could not initialize storage", e);
        }
    }

    private Path resolvePath(String path) {
        return root.resolve(path.startsWith("/") ? path.substring(1) : path).normalize();
    }

    @Override
    public void store(String path, InputStream inputStream) {
        try {
            Path target = resolvePath(path);
            Files.createDirectories(target.getParent());
            Files.copy(inputStream, target, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException e) {
            throw new StorageException("Failed to store file", HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @Override
    public void copy(String sourcePath, String targetPath) {
        try {
            Path source = resolvePath(sourcePath);
            Path target = resolvePath(targetPath);
            if (!Files.exists(source)) throw new StorageException("Source not found", HttpStatus.NOT_FOUND);

            Files.createDirectories(target.getParent());
            Files.copy(source, target, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException e) {
            throw new StorageException("Failed to copy file", HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @Override
    public Resource load(String path) {
        Path file = resolvePath(path);
        if (Files.exists(file) && !Files.isDirectory(file)) {
            return new FileSystemResource(file);
        }
        throw new StorageException("File not found or is a directory", HttpStatus.NOT_FOUND);
    }

    @Override
    public List<String> listContents(String path) {
        Path dir = resolvePath(path);
        if (!Files.exists(dir)) throw new StorageException("Not found", HttpStatus.NOT_FOUND);

        try {
            return Files.list(dir)
                    .map(p -> Files.isDirectory(p) ? p.getFileName() + "/" : p.getFileName().toString())
                    .collect(Collectors.toList());
        } catch (IOException e) {
            throw new StorageException("Failed to read directory", HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @Override
    public Map<String, Object> getMetadata(String path) {
        try {
            Path file = resolvePath(path);
            if (!Files.exists(file) || Files.isDirectory(file))
                throw new StorageException("File not found", HttpStatus.NOT_FOUND);

            Map<String, Object> meta = new HashMap<>();
            meta.put("size", Files.size(file));
            meta.put("lastModified", Files.getLastModifiedTime(file).toInstant());
            meta.put("server", "Apache Tomcat");
            return meta;
        } catch (IOException e) {
            throw new StorageException("Failed to get metadata", HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @Override
    public void delete(String path) {
        Path p = resolvePath(path);
        try {
            if (!Files.exists(p)) throw new StorageException("Not found", HttpStatus.NOT_FOUND);
            FileSystemUtils.deleteRecursively(p);
        } catch (IOException e) {
            throw new StorageException("Failed to delete", HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @Override
    public boolean exists(String path) {
        return Files.exists(resolvePath(path));
    }
}