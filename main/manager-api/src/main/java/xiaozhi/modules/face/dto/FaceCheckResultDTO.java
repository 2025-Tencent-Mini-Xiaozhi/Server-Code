package xiaozhi.modules.face.dto;

import lombok.Data;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 人脸检查结果DTO
 */
@Data
@Schema(description = "人脸检查结果")
public class FaceCheckResultDTO {

    @Schema(description = "是否成功")
    private Boolean success;

    @Schema(description = "人脸是否已存在")
    private Boolean exists;

    @Schema(description = "是否检测到人脸")
    private Boolean faceDetected;

    @Schema(description = "消息")
    private String message;

    @Schema(description = "检测到的人脸总数")
    private Integer totalFacesDetected;

    @Schema(description = "已存在的用户信息")
    private ExistingUserDTO existingUser;

    /**
     * 已存在用户信息的内部类
     */
    @Data
    @Schema(description = "已存在用户信息")
    public static class ExistingUserDTO {
        @Schema(description = "用户ID")
        private Long userId;

        @Schema(description = "用户名")
        private String username;

        @Schema(description = "真实姓名")
        private String realName;

        @Schema(description = "相似度")
        private Double similarity;
    }
}
