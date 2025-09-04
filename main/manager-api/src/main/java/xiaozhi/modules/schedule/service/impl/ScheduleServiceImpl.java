package xiaozhi.modules.schedule.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.CrudServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.modules.schedule.dao.ScheduleDao;
import xiaozhi.modules.schedule.dto.ScheduleDTO;
import xiaozhi.modules.schedule.entity.ScheduleEntity;
import xiaozhi.modules.schedule.service.ScheduleService;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/**
 * 日程管理Service实现类
 * 
 * @author Xiaozhi ESP32 Server
 * @since 2025-08-24
 */
@Slf4j
@Service
@AllArgsConstructor
public class ScheduleServiceImpl extends CrudServiceImpl<ScheduleDao, ScheduleEntity, ScheduleDTO> 
        implements ScheduleService {

    private final ScheduleDao scheduleDao;

    @Override
    public QueryWrapper<ScheduleEntity> getWrapper(Map<String, Object> params) {
        Long userId = (Long) params.get("userId");
        String content = (String) params.get("content");
        LocalDate startDate = (LocalDate) params.get("startDate");
        LocalDate endDate = (LocalDate) params.get("endDate");
        Integer status = (Integer) params.get("status");

        QueryWrapper<ScheduleEntity> wrapper = new QueryWrapper<>();
        wrapper.eq(userId != null, "user_id", userId)
               .like(content != null && !content.isEmpty(), "content", content)
               .ge(startDate != null, "schedule_date", startDate)
               .le(endDate != null, "schedule_date", endDate)
               .eq(status != null, "status", status)
               .orderByDesc("schedule_date", "create_date");

        return wrapper;
    }

    @Override
    public PageData<ScheduleDTO> getUserSchedulePage(Long userId, Map<String, Object> params) {
        log.info("获取用户{}的日程列表，参数：{}", userId, params);
        
        params.put("userId", userId);
        
        IPage<ScheduleEntity> page = scheduleDao.selectPage(
                getPage(params, "schedule_date", false),
                getWrapper(params));

        return getPageData(page, ScheduleDTO.class);
    }

    @Override
    public List<ScheduleDTO> getUserSchedulesByDateRange(Long userId, LocalDate startDate, LocalDate endDate) {
        log.info("获取用户{}在{}到{}的日程", userId, startDate, endDate);
        
        QueryWrapper<ScheduleEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("user_id", userId)
               .ge("schedule_date", startDate)
               .le("schedule_date", endDate)
               .orderByAsc("schedule_date");

        List<ScheduleEntity> schedules = scheduleDao.selectList(wrapper);
        return ConvertUtils.sourceToTarget(schedules, ScheduleDTO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateScheduleStatus(Long scheduleId, Long userId, Integer status) {
        log.info("更新日程状态：scheduleId={}, userId={}, status={}", scheduleId, userId, status);
        
        ScheduleEntity entity = scheduleDao.selectById(scheduleId);
        if (entity == null) {
            throw new RenException(ErrorCode.FORBIDDEN, "日程不存在");
        }
        
        if (!entity.getUserId().equals(userId)) {
            throw new RenException(ErrorCode.FORBIDDEN, "无权限操作此日程");
        }
        
        entity.setStatus(status);
        scheduleDao.updateById(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteUserSchedule(Long scheduleId, Long userId) {
        log.info("删除用户日程：scheduleId={}, userId={}", scheduleId, userId);
        
        ScheduleEntity entity = scheduleDao.selectById(scheduleId);
        if (entity == null) {
            throw new RenException(ErrorCode.FORBIDDEN, "日程不存在");
        }
        
        if (!entity.getUserId().equals(userId)) {
            throw new RenException(ErrorCode.FORBIDDEN, "无权限删除此日程");
        }
        
        scheduleDao.deleteById(scheduleId);
    }

    @Override
    public void save(ScheduleDTO dto) {
        log.info("创建日程：{}", dto);
        
        ScheduleEntity entity = ConvertUtils.sourceToTarget(dto, ScheduleEntity.class);
        
        // 新建日程默认状态为未完成
        if (entity.getStatus() == null) {
            entity.setStatus(0);
        }
        
        scheduleDao.insert(entity);
        dto.setId(entity.getId());
    }

    @Override
    public void update(ScheduleDTO dto) {
        log.info("更新日程：{}", dto);
        
        ScheduleEntity entity = scheduleDao.selectById(dto.getId());
        if (entity == null) {
            throw new RenException(ErrorCode.FORBIDDEN, "日程不存在");
        }
        
        if (!entity.getUserId().equals(dto.getUserId())) {
            throw new RenException(ErrorCode.FORBIDDEN, "无权限操作此日程");
        }
        
        entity.setContent(dto.getContent());
        entity.setScheduleDate(dto.getScheduleDate());
        if (dto.getStatus() != null) {
            entity.setStatus(dto.getStatus());
        }
        
        scheduleDao.updateById(entity);
    }
}
