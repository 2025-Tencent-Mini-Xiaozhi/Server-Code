package xiaozhi.modules.schedule.service;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.CrudService;
import xiaozhi.modules.schedule.dto.ScheduleDTO;
import xiaozhi.modules.schedule.entity.ScheduleEntity;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/**
 * 日程管理Service接口
 * 
 * @author Xiaozhi ESP32 Server
 * @since 2025-08-24
 */
public interface ScheduleService extends CrudService<ScheduleEntity, ScheduleDTO> {
    
    /**
     * 获取用户日程列表（分页）
     */
    PageData<ScheduleDTO> getUserSchedulePage(Long userId, Map<String, Object> params);
    
    /**
     * 获取用户指定日期范围的日程
     */
    List<ScheduleDTO> getUserSchedulesByDateRange(Long userId, LocalDate startDate, LocalDate endDate);
    
    /**
     * 更新日程状态
     */
    void updateScheduleStatus(Long scheduleId, Long userId, Integer status);
    
    /**
     * 删除用户日程
     */
    void deleteUserSchedule(Long scheduleId, Long userId);
}
