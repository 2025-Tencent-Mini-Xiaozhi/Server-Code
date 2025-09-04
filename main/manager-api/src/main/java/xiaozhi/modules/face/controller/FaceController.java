package xiaozhi.modules.face.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import xiaozhi.common.annotation.LogOperation;
import xiaozhi.common.utils.Result;

import java.io.File;
import java.util.*;
import java.util.regex.Pattern;

/**
 * 人脸模块管理Controller
 * 
 * @author Xiaozhi ESP32 Server
 * @since 2025-08-25
 */
@Slf4j
@Tag(name = "人脸模块管理")
@RestController
@RequestMapping("/face")
public class FaceController {

    private static final String UPLOADS_DIR = "/root/xiaozhi-esp32-server/main/xiaozhi-server/uploads/";
    private static final Pattern IMAGE_PATTERN = Pattern.compile(".*\\.(jpg|jpeg|png|gif|bmp)$",
            Pattern.CASE_INSENSITIVE);

    @GetMapping("/images")
    @Operation(summary = "获取人脸图片列表")
    @LogOperation("获取人脸图片列表")
    public Result<List<Map<String, Object>>> getImageList(@RequestParam(required = false) String deviceId) {
        try {
            File uploadsDir = new File(UPLOADS_DIR);
            if (!uploadsDir.exists() || !uploadsDir.isDirectory()) {
                return new Result<List<Map<String, Object>>>().ok(new ArrayList<>());
            }

            File[] files = uploadsDir.listFiles();
            if (files == null) {
                return new Result<List<Map<String, Object>>>().ok(new ArrayList<>());
            }

            List<Map<String, Object>> imageList = new ArrayList<>();

            for (File file : files) {
                if (file.isFile() && IMAGE_PATTERN.matcher(file.getName()).matches()) {
                    // 如果指定了设备码，则进行过滤
                    if (deviceId != null && !deviceId.trim().isEmpty()) {
                        if (!file.getName().contains(deviceId)) {
                            continue;
                        }
                    }

                    Map<String, Object> imageInfo = new HashMap<>();
                    imageInfo.put("name", file.getName());
                    imageInfo.put("size", file.length());
                    imageInfo.put("timestamp", file.lastModified() / 1000); // 转换为秒

                    imageList.add(imageInfo);
                }
            }

            // 按时间戳倒序排列（最新的在前）
            imageList.sort((a, b) -> {
                Long timestampA = (Long) a.get("timestamp");
                Long timestampB = (Long) b.get("timestamp");
                return timestampB.compareTo(timestampA);
            });

            return new Result<List<Map<String, Object>>>().ok(imageList);
        } catch (Exception e) {
            log.error("获取图片列表失败", e);
            return new Result<List<Map<String, Object>>>().error("获取图片列表失败：" + e.getMessage());
        }
    }

    @GetMapping("/images/{filename:.+}")
    @Operation(summary = "获取人脸图片文件")
    @LogOperation("获取人脸图片文件")
    public ResponseEntity<Resource> getImage(@PathVariable String filename) {
        try {
            // 使用绝对路径查找图片文件
            String filePath = "/root/xiaozhi-esp32-server/main/xiaozhi-server/uploads/" + filename;
            File file = new File(filePath);

            // 检查文件是否存在
            if (!file.exists()) {
                return ResponseEntity.notFound().build();
            }

            // 创建资源
            FileSystemResource resource = new FileSystemResource(file);

            // 设置响应头
            HttpHeaders headers = new HttpHeaders();
            headers.add(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + filename + "\"");

            // 确定内容类型
            MediaType mediaType;
            if (filename.toLowerCase().endsWith(".jpg") || filename.toLowerCase().endsWith(".jpeg")) {
                mediaType = MediaType.IMAGE_JPEG;
            } else if (filename.toLowerCase().endsWith(".png")) {
                mediaType = MediaType.IMAGE_PNG;
            } else {
                mediaType = MediaType.APPLICATION_OCTET_STREAM;
            }

            return ResponseEntity.ok()
                    .headers(headers)
                    .contentLength(file.length())
                    .contentType(mediaType)
                    .body(resource);
        } catch (Exception e) {
            log.error("获取图片文件失败: {}", filename, e);
            return ResponseEntity.status(500).build();
        }
    }
}