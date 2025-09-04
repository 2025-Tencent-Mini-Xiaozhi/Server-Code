package xiaozhi.modules.face.dto;

import lombok.Data;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 人脸注册请求DTO
 */
@Data
@Schema(description = "人脸注册请求")
public class FaceRegisterDTO {

    @Schema(description = "用户ID")
    private Long userId;

    @Schema(description = "用户真实姓名")
    private String realName;

    @Schema(description = "人脸图片文件名")
    private String imageName;
}
