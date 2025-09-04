package xiaozhi.modules.schedule.dao;

import org.apache.ibatis.annotations.Mapper;
import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.schedule.entity.ScheduleEntity;

/**
 * 日程管理DAO
 * 
 * @author Xiaozhi ESP32 Server
 * @since 2025-08-24
 */
@Mapper
public interface ScheduleDao extends BaseDao<ScheduleEntity> {
}
