package xiaozhi.modules.schedule.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.common.entity.BaseEntity;

import java.time.LocalDate;
import java.util.Date;

/**
 * 用户日程实体类
 * 
 * @author Xiaozhi ESP32 Server
 * @since 2025-08-24
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("sys_schedule")
@Schema(description = "用户日程信息")
public class ScheduleEntity extends BaseEntity {
    
    /**
     * 用户ID
     */
    @Schema(description = "用户ID")
    private Long userId;
    
    /**
     * 日程内容
     */
    @Schema(description = "日程内容")
    private String content;
    
    /**
     * 日程日期
     */
    @Schema(description = "日程日期")
    private LocalDate scheduleDate;
    
    /**
     * 状态：0-未完成(pending)，1-已完成(completed)
     */
    @Schema(description = "状态：0-未完成，1-已完成")
    private Integer status;
    
    /**
     * 更新者
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Long updater;
    
    /**
     * 更新时间
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Date updateDate;
}
