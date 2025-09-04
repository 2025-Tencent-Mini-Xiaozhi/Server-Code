package xiaozhi.modules.face.dto;

import lombok.Data;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 人脸注册结果DTO
 */
@Data
@Schema(description = "人脸注册结果")
public class FaceRegisterResultDTO {

    @Schema(description = "是否成功")
    private Boolean success;

    @Schema(description = "消息")
    private String message;

    @Schema(description = "用户ID")
    private Long userId;

    @Schema(description = "用户真实姓名")
    private String realName;

    @Schema(description = "人脸图片路径")
    private String faceImagePath;

    @Schema(description = "检测到的人脸总数")
    private Integer totalFacesDetected;

    @Schema(description = "是否选择了最大的人脸")
    private Boolean selectedLargestFace;
}
