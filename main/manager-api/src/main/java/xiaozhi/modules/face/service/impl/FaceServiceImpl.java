package xiaozhi.modules.face.service.impl;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.ResourceAccessException;
import xiaozhi.modules.face.dto.FaceRegisterDTO;
import xiaozhi.modules.face.dto.FaceRegisterResultDTO;
import xiaozhi.modules.face.dto.FaceCheckDTO;
import xiaozhi.modules.face.dto.FaceCheckResultDTO;
import xiaozhi.modules.face.service.FaceService;

import java.util.HashMap;
import java.util.Map;

/**
 * 人脸识别服务实现类
 */
@Slf4j
@Service
public class FaceServiceImpl implements FaceService {

    @Value("${xiaozhi.server.host:xiaozhi-esp32-server}")
    private String xiaozhiServerHost;

    @Value("${xiaozhi.server.port:8003}")
    private String xiaozhiServerPort;

    @Autowired
    private RestTemplate restTemplate;

    private String getXiaozhiServerUrl() {
        return String.format("http://%s:%s", xiaozhiServerHost, xiaozhiServerPort);
    }

    @Override
    public FaceCheckResultDTO checkFace(String imageName) {
        try {
            String url = getXiaozhiServerUrl() + "/face/check";

            log.info("调用xiaozhi-server人脸检查API: {}", url);
            log.info("检查图片: {}", imageName);

            // 构建请求体
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("image_name", imageName);

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestBody, headers);

            // 发送请求
            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);

            log.info("xiaozhi-server响应状态码: {}", response.getStatusCode());
            log.info("xiaozhi-server响应体: {}", response.getBody());

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                Map<String, Object> responseBody = response.getBody();
                Integer code = (Integer) responseBody.get("code");

                if (code != null && code == 0) {
                    // 成功
                    Map<String, Object> data = (Map<String, Object>) responseBody.get("data");
                    if (data != null) {
                        FaceCheckResultDTO result = new FaceCheckResultDTO();
                        result.setSuccess((Boolean) data.get("success"));
                        result.setExists((Boolean) data.get("exists"));
                        result.setFaceDetected((Boolean) data.get("face_detected"));
                        result.setMessage((String) data.get("message"));
                        result.setTotalFacesDetected((Integer) data.get("total_faces_detected"));

                        // 处理已存在用户信息
                        Map<String, Object> existingUserData = (Map<String, Object>) data.get("existing_user");
                        if (existingUserData != null) {
                            FaceCheckResultDTO.ExistingUserDTO existingUser = new FaceCheckResultDTO.ExistingUserDTO();
                            existingUser.setUserId(((Number) existingUserData.get("user_id")).longValue());
                            existingUser.setUsername((String) existingUserData.get("username"));
                            existingUser.setRealName((String) existingUserData.get("real_name"));
                            existingUser.setSimilarity((Double) existingUserData.get("similarity"));
                            result.setExistingUser(existingUser);
                        }

                        return result;
                    }
                } else {
                    // xiaozhi-server返回错误
                    String message = (String) responseBody.get("msg");
                    FaceCheckResultDTO result = new FaceCheckResultDTO();
                    result.setSuccess(false);
                    result.setExists(false);
                    result.setFaceDetected(false);
                    result.setMessage(message != null ? message : "人脸检查失败");
                    return result;
                }
            }

            // 默认失败响应
            FaceCheckResultDTO result = new FaceCheckResultDTO();
            result.setSuccess(false);
            result.setExists(false);
            result.setFaceDetected(false);
            result.setMessage("调用xiaozhi-server人脸检查API失败");
            return result;

        } catch (ResourceAccessException e) {
            log.error("无法连接到xiaozhi-server: {}", e.getMessage());
            FaceCheckResultDTO result = new FaceCheckResultDTO();
            result.setSuccess(false);
            result.setExists(false);
            result.setFaceDetected(false);
            result.setMessage("无法连接到人脸识别服务");
            return result;
        } catch (Exception e) {
            log.error("调用xiaozhi-server人脸检查API异常", e);
            FaceCheckResultDTO result = new FaceCheckResultDTO();
            result.setSuccess(false);
            result.setExists(false);
            result.setFaceDetected(false);
            result.setMessage("人脸检查服务异常: " + e.getMessage());
            return result;
        }
    }

    @Override
    public FaceRegisterResultDTO registerFace(FaceRegisterDTO faceRegisterDTO) {
        try {
            String url = getXiaozhiServerUrl() + "/face/register";

            log.info("调用xiaozhi-server人脸注册API: {}", url);
            log.info("注册参数: userId={}, realName={}, imageName={}",
                    faceRegisterDTO.getUserId(),
                    faceRegisterDTO.getRealName(),
                    faceRegisterDTO.getImageName());

            // 构建请求体
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("user_id", faceRegisterDTO.getUserId());
            requestBody.put("real_name", faceRegisterDTO.getRealName());
            requestBody.put("image_name", faceRegisterDTO.getImageName());

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestBody, headers);

            // 发送请求
            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);

            log.info("xiaozhi-server响应状态码: {}", response.getStatusCode());
            log.info("xiaozhi-server响应体: {}", response.getBody());

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                Map<String, Object> responseBody = response.getBody();
                Integer code = (Integer) responseBody.get("code");

                if (code != null && code == 0) {
                    // 成功
                    Map<String, Object> data = (Map<String, Object>) responseBody.get("data");
                    if (data != null) {
                        FaceRegisterResultDTO result = new FaceRegisterResultDTO();
                        result.setSuccess((Boolean) data.get("success"));
                        result.setMessage((String) data.get("message"));
                        result.setUserId(((Number) data.get("user_id")).longValue());
                        result.setRealName((String) data.get("real_name"));
                        result.setFaceImagePath((String) data.get("face_image_path"));
                        result.setTotalFacesDetected((Integer) data.get("total_faces_detected"));
                        result.setSelectedLargestFace((Boolean) data.get("selected_largest_face"));
                        return result;
                    }
                } else {
                    // xiaozhi-server返回错误
                    String message = (String) responseBody.get("msg");
                    FaceRegisterResultDTO result = new FaceRegisterResultDTO();
                    result.setSuccess(false);
                    result.setMessage(message != null ? message : "人脸注册失败");
                    return result;
                }
            }

            // 默认失败响应
            FaceRegisterResultDTO result = new FaceRegisterResultDTO();
            result.setSuccess(false);
            result.setMessage("调用xiaozhi-server人脸注册API失败");
            return result;

        } catch (ResourceAccessException e) {
            log.error("无法连接到xiaozhi-server: {}", e.getMessage());
            FaceRegisterResultDTO result = new FaceRegisterResultDTO();
            result.setSuccess(false);
            result.setMessage("无法连接到人脸识别服务");
            return result;
        } catch (Exception e) {
            log.error("调用xiaozhi-server人脸注册API异常", e);
            FaceRegisterResultDTO result = new FaceRegisterResultDTO();
            result.setSuccess(false);
            result.setMessage("人脸注册服务异常: " + e.getMessage());
            return result;
        }
    }

    @Override
    public boolean isXiaozhiServerAvailable() {
        try {
            String url = getXiaozhiServerUrl() + "/face/images";
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            return response.getStatusCode() == HttpStatus.OK;
        } catch (Exception e) {
            log.warn("xiaozhi-server不可用: {}", e.getMessage());
            return false;
        }
    }
}
