package xiaozhi.modules.face.dto;

import lombok.Data;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 人脸检查请求DTO
 */
@Data
@Schema(description = "人脸检查请求")
public class FaceCheckDTO {

    @Schema(description = "人脸图片文件名")
    private String imageName;
}
