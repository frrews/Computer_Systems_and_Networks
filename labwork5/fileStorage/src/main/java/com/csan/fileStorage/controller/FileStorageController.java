package com.csan.fileStorage.controller;

import com.csan.fileStorage.service.FileStorageService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.core.io.Resource;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Map;


@RestController
public class FileStorageController {

    private final FileStorageService    storageService;

    public FileStorageController(FileStorageService storageService) {
        this.storageService = storageService;
    }

    @PutMapping("/**")
    public ResponseEntity<?> uploadOrCopy(
            HttpServletRequest request,
            @RequestHeader(value = "X-Copy-From", required = false) String copyFrom) throws IOException {

        String path = request.getRequestURI();
        boolean existed = storageService.exists(path);

        if (copyFrom != null) {
            storageService.copy(copyFrom, path);
            return ResponseEntity
                    .status(existed ? HttpStatus.OK : HttpStatus.CREATED)
                    .body(existed ? "Overwritten" : "Copied");
        }

        storageService.store(path, request.getInputStream());
        return ResponseEntity
                .status(existed ? HttpStatus.OK : HttpStatus.CREATED)
                .body(existed ? "Overwritten" : "Uploaded");
    }

    @GetMapping("/**")
    public ResponseEntity<?> get(HttpServletRequest request) {
        String path = request.getRequestURI();

        try {
            Resource resource = storageService.load(path);
            Path filePath = resource.getFile().toPath();
            String contentType = Files.probeContentType(filePath);

            if (contentType == null) {
                contentType = "application/octet-stream";
            }

            return ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType(contentType))
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + resource.getFilename() + "\"")
                    .body(resource);
        } catch (Exception e) {
            return ResponseEntity.ok(storageService.listContents(path));
        }
    }

    @RequestMapping(value = "/**", method = RequestMethod.HEAD)
    public ResponseEntity<?> head(HttpServletRequest request) {
        Map<String, Object> meta = storageService.getMetadata(request.getRequestURI());
        return ResponseEntity.ok()
                .contentLength((Long) meta.get("size"))
                .lastModified((Instant) meta.get("lastModified"))
                .header("Server", (String) meta.get("server"))
                .build();
    }

    @DeleteMapping("/**")
    public ResponseEntity<?> delete(HttpServletRequest request) {
        storageService.delete(request.getRequestURI());
        return ResponseEntity.ok("Deleted");
    }
}