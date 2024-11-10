package com.app.webnongsan.controller;

import com.app.webnongsan.domain.response.file.ResUploadFileDTO;
import com.app.webnongsan.service.FileService;
import com.app.webnongsan.util.annotation.ApiMessage;
import com.app.webnongsan.util.exception.StorageException;
import lombok.AllArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Arrays;
@RestController
@RequestMapping("api/v2")
public class FileController {
    @Value("${upload-file.base-uri}")
    private String baseURI;

    private final FileService fileService;

    public FileController(FileService fileService) {
        this.fileService = fileService;
    }

    @PostMapping("files")
    @ApiMessage("Upload single file")
    public ResponseEntity<ResUploadFileDTO> upload(@RequestParam(name = "file", required = false) MultipartFile file,
                                                   @RequestParam("folder") String folder ) throws URISyntaxException, IOException, StorageException {
        //Validate empty file
        if (file == null || file.isEmpty()){
            throw new StorageException("File is empty. Please choose a file");
        }

        //Validate extension file
        String fileName = file.getOriginalFilename();
        List<String> allowedExtensions = Arrays.asList("jpg", "jpeg", "png");
        boolean isValid = allowedExtensions.stream().anyMatch(item -> {
            assert fileName != null;
            return fileName.toLowerCase().endsWith(item);
        });
        if (!isValid){
            throw new StorageException("File not allowed! Please use file " + allowedExtensions.toString());
        }
        //create folder if not exist
        this.fileService.createDirectory(baseURI + folder);
        //save file
        String uploadFile = this.fileService.store(file, folder);
        ResUploadFileDTO rs = new ResUploadFileDTO(uploadFile, Instant.now());
        return ResponseEntity.ok(rs);
    }
}
