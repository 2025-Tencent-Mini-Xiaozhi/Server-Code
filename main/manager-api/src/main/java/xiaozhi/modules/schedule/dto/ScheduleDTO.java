package xiaozhi.modules.schedule.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.LocalDate;

/**
 * 日程DTO
 * 
 * @author Xiaozhi ESP32 Server
 * @since 2025-08-24
 */
@Data
@Schema(description = "日程信息")
public class ScheduleDTO {
    
    @Schema(description = "日程ID")
    private Long id;
    
    @Schema(description = "用户ID")
    private Long userId;
    
    @NotBlank(message = "日程内容不能为空")
    @Schema(description = "日程内容")
    private String content;
    
    @NotNull(message = "日程日期不能为空")
    @Schema(description = "日程日期")
    private LocalDate scheduleDate;
    
    @Schema(description = "状态：0-未完成，1-已完成")
    private Integer status;
}
