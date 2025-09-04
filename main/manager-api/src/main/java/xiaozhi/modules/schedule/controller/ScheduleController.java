package xiaozhi.modules.schedule.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import xiaozhi.common.annotation.LogOperation;
import xiaozhi.common.page.PageData;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.schedule.dto.ScheduleDTO;
import xiaozhi.modules.schedule.service.ScheduleService;
import xiaozhi.modules.security.user.SecurityUser;

import jakarta.validation.Valid;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/**
 * 日程管理Controller
 * 
 * @author Xiaozhi ESP32 Server
 * @since 2025-08-24
 */
@Slf4j
@Tag(name = "日程管理")
@AllArgsConstructor
@RestController
@RequestMapping("/schedule")
public class ScheduleController {

    private final ScheduleService scheduleService;

    @GetMapping("/page")
    @Operation(summary = "分页查询日程")
    public Result<PageData<ScheduleDTO>> page(@RequestParam Map<String, Object> params) {
        UserDetail user = SecurityUser.getUser();
        PageData<ScheduleDTO> page = scheduleService.getUserSchedulePage(user.getId(), params);
        return new Result<PageData<ScheduleDTO>>().ok(page);
    }

    @GetMapping("/list")
    @Operation(summary = "获取指定日期范围的日程")
    public Result<List<ScheduleDTO>> getSchedulesByDateRange(
            @RequestParam("startDate") LocalDate startDate,
            @RequestParam("endDate") LocalDate endDate) {
        UserDetail user = SecurityUser.getUser();
        List<ScheduleDTO> schedules = scheduleService.getUserSchedulesByDateRange(user.getId(), startDate, endDate);
        return new Result<List<ScheduleDTO>>().ok(schedules);
    }

    @GetMapping("/{id}")
    @Operation(summary = "获取日程详情")
    public Result<ScheduleDTO> get(@PathVariable("id") Long id) {
        ScheduleDTO schedule = scheduleService.get(id);
        UserDetail user = SecurityUser.getUser();

        // 验证权限
        if (!schedule.getUserId().equals(user.getId())) {
            return new Result<ScheduleDTO>().error("无权限查看此日程");
        }

        return new Result<ScheduleDTO>().ok(schedule);
    }

    @PostMapping
    @Operation(summary = "新增日程")
    @LogOperation("新增日程")
    public Result<String> save(@RequestBody @Valid ScheduleDTO dto) {
        UserDetail user = SecurityUser.getUser();
        dto.setUserId(user.getId());

        scheduleService.save(dto);

        log.info("用户{}新增日程成功，日程ID：{}", user.getId(), dto.getId());
        return new Result<String>().ok("日程添加成功");
    }

    @PutMapping
    @Operation(summary = "修改日程")
    @LogOperation("修改日程")
    public Result<String> update(@RequestBody @Valid ScheduleDTO dto) {
        UserDetail user = SecurityUser.getUser();
        dto.setUserId(user.getId());

        scheduleService.update(dto);

        log.info("用户{}修改日程成功，日程ID：{}", user.getId(), dto.getId());
        return new Result<String>().ok("日程修改成功");
    }

    @PutMapping("/{id}/status")
    @Operation(summary = "更新日程状态")
    @LogOperation("更新日程状态")
    public Result<String> updateStatus(@PathVariable("id") Long id, @RequestParam("status") Integer status) {
        UserDetail user = SecurityUser.getUser();

        scheduleService.updateScheduleStatus(id, user.getId(), status);

        String statusText = status == 1 ? "已完成" : "未完成";
        log.info("用户{}更新日程{}状态为：{}", user.getId(), id, statusText);
        return new Result<String>().ok("状态更新成功");
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除日程")
    @LogOperation("删除日程")
    public Result<String> delete(@PathVariable("id") Long id) {
        UserDetail user = SecurityUser.getUser();

        scheduleService.deleteUserSchedule(id, user.getId());

        log.info("用户{}删除日程{}成功", user.getId(), id);
        return new Result<String>().ok("日程删除成功");
    }

    /**
     * 内部API：获取用户指定日期的日程（xiaozhi-server专用）
     * 使用ServerSecret认证，无需用户登录
     */
    @GetMapping("/internal/user/{userId}/date/{date}")
    @Operation(summary = "内部API：获取用户指定日期的日程")
    public Result<List<ScheduleDTO>> getInternalUserSchedulesByDate(
            @PathVariable("userId") Long userId,
            @PathVariable("date") String date) {
        try {
            LocalDate scheduleDate = LocalDate.parse(date);
            List<ScheduleDTO> schedules = scheduleService.getUserSchedulesByDateRange(userId, scheduleDate,
                    scheduleDate);
            log.info("内部API：获取用户{}在{}的日程，共{}条", userId, date, schedules.size());
            return new Result<List<ScheduleDTO>>().ok(schedules);
        } catch (Exception e) {
            log.error("内部API：获取用户日程失败", e);
            return new Result<List<ScheduleDTO>>().error("获取日程失败");
        }
    }
}
